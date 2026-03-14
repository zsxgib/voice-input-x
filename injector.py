# 文字注入模块

import subprocess
import pyperclip
import time


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

        # 获取窗口名
        name_result = subprocess.run(
            ["xdotool", "getwindowname", window_id],
            capture_output=True, text=True
        )
        window_name = name_result.stdout.strip().lower()

        # 获取窗口类名
        class_result = subprocess.run(
            ["xdotool", "getwindowclassname", window_id],
            capture_output=True, text=True
        )
        window_class = class_result.stdout.strip().lower()

        # 获取窗口的进程名
        pid_result = subprocess.run(
            ["xdotool", "getwindowpid", window_id],
            capture_output=True, text=True
        )
        pid = pid_result.stdout.strip()

        process_name = ""
        if pid:
            try:
                proc_result = subprocess.run(
                    ["ps", "-p", pid, "-o", "comm="],
                    capture_output=True, text=True
                )
                process_name = proc_result.stdout.strip().lower()
            except:
                pass

        return window_id, window_name, window_class, process_name
    except:
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
        print(f"已复制到剪贴板: {text[:20]}...")
    except Exception as e:
        print(f"复制失败: {e}")
        return False

    time.sleep(0.2)

    # 获取窗口信息
    win_id, window_name, window_class, process_name = get_window_info(window_id)
    print(f"窗口: class={window_class}, proc={process_name}, name={window_name[:30]}")

    # 判断是否为终端
    is_terminal = is_terminal_window(window_name, window_class, process_name)

    # 对于 VS Code，尝试两种方式（终端可能在面板中）
    if 'code' in process_name or 'vscode' in process_name:
        print("检测到 VS Code，尝试 Ctrl+Shift+V...")
        if try_inject(text, ["ctrl+shift+v"]):
            print("文字已注入 (Ctrl+Shift+V)")
            return True
        print("Ctrl+Shift+V 失败，尝试 Ctrl+V...")
        if try_inject(text, ["ctrl+v"]):
            print("文字已注入 (Ctrl+V)")
            return True
    elif is_terminal:
        # 终端使用 Ctrl+Shift+V
        print("检测到终端，使用 Ctrl+Shift+V")
        if try_inject(text, ["ctrl+shift+v"]):
            print("文字已注入 (Ctrl+Shift+V)")
            return True
    else:
        # 普通应用使用 Ctrl+V
        print("检测到普通应用，使用 Ctrl+V")
        if try_inject(text, ["ctrl+v"]):
            print("文字已注入 (Ctrl+V)")
            return True

    # 备用方式：xdotool type
    print("尝试 xdotool type...")
    try:
        subprocess.run(
            ["xdotool", "type", "--", text],
            capture_output=True,
            timeout=10
        )
        print("文字已注入 (xdotool type)")
        return True
    except Exception as e:
        print(f"xdotool type 失败: {e}")
        return False


def inject_text(text, original_window=None):
    """注入文字，original_window 是原始窗口ID"""
    return inject_text_at_cursor(text, original_window)
