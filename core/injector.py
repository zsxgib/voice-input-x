# 文字注入模块

import subprocess
import pyperclip
import time

from .logger import logger


def get_window_info(window_id=None):
    """获取窗口信息"""
    try:
        # 如果没有指定窗口ID，获取当前活动窗口
        if window_id is None:
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True
            )
            window_id = result.stdout.strip()

        if not window_id:
            logger.warning("window_id 为空")
            return None, "", "", ""

        # 获取窗口名
        name_result = subprocess.run(
            ["xdotool", "getwindowname", window_id],
            capture_output=True, text=True
        )
        window_name = name_result.stdout.strip().lower()
        if name_result.returncode != 0:
            logger.warning(f"getwindowname 失败: {name_result.stderr}")

        # 获取窗口类名
        window_class = ""
        class_result = subprocess.run(
            ["xdotool", "getwindowclassname", window_id],
            capture_output=True, text=True
        )
        if class_result.returncode != 0:
            # 尝试使用 xprop
            try:
                prop_result = subprocess.run(
                    ["xprop", "-id", window_id, "WM_CLASS"],
                    capture_output=True, text=True, timeout=3
                )
                if prop_result.returncode == 0 and "WM_CLASS" in prop_result.stdout:
                    # 格式: WM_CLASS = STRING = "code", "Code"
                    parts = prop_result.stdout.split('=')
                    if len(parts) > 1:
                        window_class = parts[-1].strip().strip('"').split(',')[0].strip().lower()
            except:
                pass
        else:
            window_class = class_result.stdout.strip().lower()
        if not window_class:
            logger.warning("无法获取窗口类名")

        # 获取窗口的进程名
        pid = ""
        pid_result = subprocess.run(
            ["xdotool", "getwindowpid", window_id],
            capture_output=True, text=True
        )
        if pid_result.returncode != 0:
            # 尝试使用 xprop
            try:
                prop_result = subprocess.run(
                    ["xprop", "-id", window_id, "_NET_WM_PID"],
                    capture_output=True, text=True, timeout=3
                )
                if prop_result.returncode == 0 and "_NET_WM_PID" in prop_result.stdout:
                    parts = prop_result.stdout.split('=')
                    if len(parts) > 1:
                        pid = parts[-1].strip()
            except:
                pass
        else:
            pid = pid_result.stdout.strip()

        process_name = ""
        if pid:
            try:
                proc_result = subprocess.run(
                    ["ps", "-p", pid, "-o", "comm="],
                    capture_output=True, text=True
                )
                process_name = proc_result.stdout.strip().lower()
            except Exception as e:
                logger.warning(f"获取进程名失败: {e}")

        return window_id, window_name, window_class, process_name
    except Exception as e:
        logger.error(f"get_window_info 异常: {e}")
        return None, "", "", ""


def is_terminal_window(window_name, window_class, process_name):
    """判断是否是终端窗口"""
    # 检查进程名
    terminal_processes = ['gnome-terminal', 'konsole', 'xterm', 'urxvt',
                        'alacritty', 'kitty', 'wezterm', 'termite', 'st',
                        'bash', 'zsh', 'fish', 'sh', 'x-terminal-emul',
                        'tmux', 'screen']

    for proc in terminal_processes:
        if proc in process_name:
            return True

    # 检查窗口类名
    terminal_classes = ['terminal', 'gnome-terminal', 'konsole', 'xterm', 'urxvt',
                       'alacritty', 'kitty', 'wezterm', 'termite', 'st',
                       'gnome-console', 'pop', 'x-terminal-emul']

    for cls in terminal_classes:
        if cls in window_class:
            return True

    # 检查窗口名
    terminal_names = ['terminal', '命令行', '终端', 'console']
    for name in terminal_names:
        if name in window_name:
            return True

    return False


def try_inject(text, keys):
    """尝试使用指定按键注入"""
    try:
        subprocess.run(
            ["xdotool", "key", "--clearmodifiers"] + keys,
            capture_output=True,
            timeout=5
        )
        return True
    except:
        return False


def inject_text_at_cursor(text, window_id=None):
    """
    将文字注入到指定窗口
    自动尝试多种注入方式
    """
    if not text:
        return False

    # 复制到剪贴板
    try:
        pyperclip.copy(text)
        logger.info(f"已复制到剪贴板: {text[:20]}...")
    except Exception as e:
        logger.error(f"复制失败: {e}")
        return False

    time.sleep(0.2)

    # 激活原始窗口
    if window_id:
        try:
            subprocess.run(
                ["xdotool", "windowactivate", "--sync", window_id],
                capture_output=True,
                timeout=5
            )
            time.sleep(0.2)

            # 对于 VS Code，尝试查找并激活终端子窗口
            class_check = subprocess.run(
                ["xdotool", "getwindowclassname", window_id],
                capture_output=True, text=True
            ).stdout.strip().lower()
            if 'code' in class_check or 'vscode' in class_check:
                # 尝试查找终端子窗口
                try:
                    result = subprocess.run(
                        ["xdotool", "search", "--name", "terminal", "--onlyvisible", window_id],
                        capture_output=True, text=True, timeout=5
                    )
                    terminal_ids = result.stdout.strip().split('\n')
                    if terminal_ids and terminal_ids[0]:
                        subprocess.run(
                            ["xdotool", "windowactivate", "--sync", terminal_ids[0]],
                            capture_output=True, timeout=5
                        )
                        time.sleep(0.1)
                        logger.info(f"已激活终端子窗口: {terminal_ids[0]}")
                except Exception as e:
                    logger.warning(f"查找终端子窗口失败: {e}")

        except Exception as e:
            logger.warning(f"激活窗口失败: {e}")

    # 使用传入的 window_id 获取窗口信息
    win_id, window_name, window_class, process_name = get_window_info(window_id)
    logger.info(f"窗口: class={window_class}, proc={process_name}, name={window_name[:50]}")
    logger.info(f"窗口ID: {win_id}")

    # 判断是否为终端
    is_terminal = is_terminal_window(window_name, window_class, process_name)

    # 检查是否是 VS Code 终端
    is_vscode_terminal = ('code' in process_name or 'vscode' in process_name) and ('terminal' in window_name.lower() or 'term' in window_class.lower())
    if is_vscode_terminal:
        logger.info("检测到 VS Code 集成终端")
        is_terminal = True

    # 检查是否是 VS Code 调试终端或集成终端
    is_vscode_terminal = ('code' in process_name or 'vscode' in process_name) and (
        'debug' in window_name.lower() or 'repl' in window_name.lower() or
        'terminal' in window_name.lower() or 'term' in window_class.lower()
    )

    # 对于 VS Code 终端（调试或集成终端），优先使用 xdotool type
    if is_vscode_terminal:
        logger.info("检测到 VS Code 终端，使用 xdotool type...")
        try:
            if win_id:
                subprocess.run(
                    ["xdotool", "type", "--window", win_id, "--", text],
                    capture_output=True,
                    timeout=10
                )
            else:
                subprocess.run(
                    ["xdotool", "type", "--", text],
                    capture_output=True,
                    timeout=10
                )
            logger.info("文字已注入 (xdotool type)")
            return True
        except Exception as e:
            logger.warning(f"xdotool type 失败: {e}")
    # 对于普通 VS Code，尝试两种方式
    elif 'code' in process_name or 'vscode' in process_name:
        logger.info("检测到 VS Code，尝试 Ctrl+Shift+V...")
        if try_inject(text, ["ctrl+shift+v"]):
            logger.info("文字已注入 (Ctrl+Shift+V)")
            return True
        logger.info("Ctrl+Shift+V 失败，尝试 Ctrl+V...")
        if try_inject(text, ["ctrl+v"]):
            logger.info("文字已注入 (Ctrl+V)")
            return True
    elif is_terminal:
        # 终端使用 Ctrl+Shift+V
        logger.info("检测到终端，使用 Ctrl+Shift+V")
        if try_inject(text, ["ctrl+shift+v"]):
            logger.info("文字已注入 (Ctrl+Shift+V)")
            return True
    else:
        # 普通应用使用 Ctrl+V
        logger.info("检测到普通应用，使用 Ctrl+V")
        if try_inject(text, ["ctrl+v"]):
            logger.info("文字已注入 (Ctrl+V)")
            return True

    # 备用方式：xdotool type
    logger.info("尝试 xdotool type...")
    try:
        if win_id:
            subprocess.run(
                ["xdotool", "type", "--window", win_id, "--", text],
                capture_output=True,
                timeout=10
            )
        else:
            subprocess.run(
                ["xdotool", "type", "--", text],
                capture_output=True,
                timeout=10
            )
        logger.info("文字已注入 (xdotool type)")
        return True
    except Exception as e:
        logger.error(f"xdotool type 失败: {e}")
        return False


def inject_text(text, original_window=None):
    """注入文字，original_window 是原始窗口ID"""
    return inject_text_at_cursor(text, original_window)
