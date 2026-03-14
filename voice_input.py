#!/usr/bin/env python3
"""
语音输入法 - 主程序

用法: python voice_input.py
按 Alt+D 开始录音并注入
"""

import sys
import os
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pyannote")

import threading
import time
import tempfile
import tkinter as tk
from tkinter import scrolledtext
import subprocess
from pynput import keyboard

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from recorder import Recorder
from recognizer import Recognizer, llm_refine
from injector import inject_text


def log(msg):
    """带刷新的日志"""
    from datetime import datetime
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def main():
    """主函数"""
    log("=" * 50)
    log("       语音输入法")
    log("=" * 50)
    log(f"热键: {config.HOTKEY}")
    log(f"最大时长: {config.MAX_DURATION} 秒")
    log(f"模型: {config.WHISPER_MODEL}")
    log("=" * 50)
    log("按 Alt+D 开始录音")
    log("按 Ctrl+C 退出")
    log("=" * 50)

    # 全局状态
    state = {
        "recording": False,
        "recognizing": False,
        "window_active": False,
        "inject_done": False,  # 防止重复注入
        "recognizer": None,
        "alt_pressed": False,
        "d_pressed": False,
        "pending_hotkey": False,
        "original_window": None,  # 原始窗口 ID
        "recognition_done": False,
        "recognized_text": "",
        "recognition_error": "",
    }

    # 预热模型
    recognizer = Recognizer(config.WHISPER_MODEL, config.LANGUAGE)

    def warmup():
        recognizer.load_model()
        log("模型预热完成!")

    threading.Thread(target=warmup, daemon=True).start()

    # tkinter 变量
    root = None
    status_label = None
    text_area = None
    current_recorder = None

    def create_window():
        """创建窗口"""
        nonlocal root, status_label, text_area

        root = tk.Tk()
        root.title("语音输入")
        root.geometry("400x200")
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.95)

        # 定位在光标附近
        try:
            result = subprocess.run(
                ["xdotool", "getmouselocation"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                x = int(parts[0].split(':')[1]) + 20
                y = int(parts[1].split(':')[1]) + 20

                screen_w = root.winfo_screenwidth()
                screen_h = root.winfo_screenheight()

                if x + 400 > screen_w:
                    x = screen_w - 420
                if y + 200 > screen_h:
                    y = screen_h - 220

                root.geometry(f"400x200+{x}+{y}")
        except:
            pass

        # 状态标签
        status_label = tk.Label(
            root,
            text="按 Enter 结束录音并注入...",
            font=("Arial", 12),
            fg="blue"
        )
        status_label.pack(pady=10)

        # 文本区域
        text_area = scrolledtext.ScrolledText(
            root,
            width=50,
            height=6,
            font=("Arial", 11)
        )
        text_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        text_area.insert("1.0", "请说话，按 Enter 结束录音...")

        root.focus_force()
        state["window_active"] = True

    def on_enter():
        """处理 Enter 键"""
        global current_recorder

        if state["recognizing"]:
            return

        if state["recording"]:
            # 停止录音
            state["recording"] = False

            if not current_recorder:
                log("错误: recorder 未初始化")
                status_label.config(text="录音失败: recorder 未初始化", fg="red")
                return

            log("停止录音，开始识别...")
            status_label.config(text="识别中...", fg="orange")

            # 停止并保存
            current_recorder.stop()
            audio_path = tempfile.mktemp(suffix=".wav")
            result = current_recorder.save(audio_path)

            if not result:
                log("错误: 录音保存失败")
                status_label.config(text="录音保存失败", fg="red")
                return

            # 在后台线程识别和整理
            def do_recognition():
                import time as time_module
                t0 = time_module.time()

                try:
                    # ASR 识别
                    log("ASR 开始...")
                    text = recognizer.recognize(audio_path)
                    t1 = time_module.time()
                    log(f"ASR 完成 ({t1-t0:.1f}s): {text}")

                    # LLM 整理
                    log("LLM 开始...")
                    text = llm_refine(text)
                    t2 = time_module.time()
                    log(f"LLM 完成 ({t2-t1:.1f}s): {text}")
                    log(f"总识别时间: {t2-t0:.1f}s")

                    # 把结果存入 state，让主循环处理 GUI 更新
                    state["recognized_text"] = text
                    state["recognition_done"] = True
                    log(f"识别完成，结果已存入，等待主循环处理")

                except Exception as e:
                    log(f"识别错误: {e}")
                    state["recognition_error"] = str(e)

            threading.Thread(target=do_recognition, daemon=True).start()

    def on_recognized(text):
        """识别完成"""
        state["recognizing"] = False

        if not text:
            status_label.config(text="未识别到文字，请重试", fg="red")
            return

        # 显示结果
        text_area.delete("1.0", tk.END)
        text_area.insert("1.0", text)
        status_label.config(text="识别成功！即将注入...", fg="green")

        # 延迟关闭窗口并注入（让用户看到结果后再关闭）
        # 直接调用，因为主循环会处理
        import time
        time.sleep(0.5)
        do_inject(text)

    def do_inject(text):
        """关闭窗口并注入"""
        # 防止重复调用
        if state.get("inject_done"):
            return
        state["inject_done"] = True

        import time as time_module
        t0 = time_module.time()

        # 先关闭窗口
        close_window()
        time.sleep(0.3)

        # 激活原始窗口
        original_window = state.get("original_window")
        if original_window:
            try:
                subprocess.run(
                    ["xdotool", "windowactivate", "--sync", original_window],
                    capture_output=True,
                    timeout=2
                )
                log(f"激活原始窗口: {original_window}")
                time.sleep(0.2)
            except Exception as e:
                log(f"激活窗口失败: {e}")

        # 注入文字（传入原始窗口ID用于判断类型）
        original_window = state.get("original_window")
        inject_text(text, original_window)

        log(f"注入完成 ({time_module.time()-t0:.1f}s)")

    def on_error(msg):
        """识别错误"""
        state["recognizing"] = False
        status_label.config(text=f"识别失败: {msg}", fg="red")

    def on_escape():
        """取消"""
        global current_recorder
        if state["recording"] and current_recorder:
            current_recorder.stop()
        close_window()

    def close_window():
        """关闭窗口"""
        log("close_window 被调用")
        state["window_active"] = False
        state["recording"] = False
        state["recognizing"] = False
        state["inject_done"] = False
        try:
            if root:
                try:
                    exists = root.winfo_exists()
                    log(f"尝试关闭窗口，root exists: {exists}")
                except:
                    log("无法检查窗口状态")
            root.destroy()
            log("窗口已关闭")
        except Exception as e:
            log(f"关闭窗口失败: {e}")

    def start_recording():
        """开始录音"""
        global current_recorder

        if state["window_active"]:
            return

        # 保存原始窗口
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True
            )
            state["original_window"] = result.stdout.strip()
            log(f"原始窗口: {state['original_window']}")
        except:
            state["original_window"] = None

        # 创建窗口
        create_window()

        # 绑定快捷键（创建窗口后绑定）
        # 绑定主键盘和数字键盘的 Enter 键
        root.bind("<Return>", lambda e: on_enter())
        root.bind("<KP_Enter>", lambda e: on_enter())
        root.bind("<Escape>", lambda e: on_escape())

        # 开始录音
        state["recording"] = True
        status_label.config(text="录音中... 请说话", fg="red")
        text_area.delete("1.0", tk.END)
        text_area.insert("1.0", "录音中...")

        current_recorder = Recorder(max_duration=config.MAX_DURATION, device=config.AUDIO_DEVICE)
        current_recorder.start()

    # pynput 监听
    def on_press(key):
        try:
            if hasattr(key, 'char') and key.char == 'd':
                if state.get('alt_pressed') and not state.get('d_pressed'):
                    state['d_pressed'] = True
                    if not state["window_active"]:
                        state["pending_hotkey"] = True
        except:
            pass

    def on_release(key):
        try:
            if key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                state['alt_pressed'] = False
            if hasattr(key, 'char') and key.char == 'd':
                state['d_pressed'] = False
        except:
            pass

    def on_press_alt(key):
        try:
            if key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                state['alt_pressed'] = True
        except:
            pass

    def combined_on_press(key):
        on_press(key)
        on_press_alt(key)

    listener = keyboard.Listener(on_press=combined_on_press, on_release=on_release)
    listener.start()
    log("Alt+D 热键已注册")

    log("\n等待输入...")
    log("按 Ctrl+C 退出")

    # 主循环
    try:
        while True:
            # 检查热键
            if state["pending_hotkey"]:
                state["pending_hotkey"] = False
                start_recording()

            # 检查识别是否完成
            if state.get("recognition_done"):
                state["recognition_done"] = False
                text = state.pop("recognized_text", "")
                if text:
                    # 显示结果
                    try:
                        status_label.config(text="识别成功！", fg="green")
                        text_area.delete("1.0", tk.END)
                        text_area.insert("1.0", text)
                    except:
                        pass
                    # 延迟注入
                    time.sleep(0.5)
                    do_inject(text)

            # 检查识别错误
            if state.get("recognition_error"):
                error = state.pop("recognition_error", "")
                try:
                    status_label.config(text=f"识别失败: {error}", fg="red")
                except:
                    pass

            # 运行 GUI
            if state["window_active"] and root:
                try:
                    root.update()
                except:
                    state["window_active"] = False

            time.sleep(0.05)
    except KeyboardInterrupt:
        log("\n退出")
        sys.exit(0)


if __name__ == "__main__":
    main()
