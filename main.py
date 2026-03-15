#!/usr/bin/env python3
"""
语音输入法 - 主程序

用法: python main.py
按 Alt+D 开始录音，按回车停止并注入
"""

import sys
import os
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pyannote")

import threading
import time

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import config
from core.state import AppState
from core.app import VoiceApp
from core.hotkey import HotkeyManager
from gui.window import VoiceGUI


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
    log(f"热键: {config.hotkey.trigger}")
    log(f"最大时长: {config.recorder.max_duration} 秒")
    log(f"模型: {config.asr.model}")
    log("=" * 50)
    log("按 Alt+D 开始录音")
    log("按 回车 停止并注入")
    log("按 Ctrl+C 退出")
    log("=" * 50)

    # 创建应用实例
    app = VoiceApp()
    app.init()

    # 预热模型
    threading.Thread(target=app.warmup, daemon=True).start()

    # GUI
    gui = None

    # 状态
    state = {
        "pending_hotkey": False,
        "pending_enter": False,
    }

    # 回调函数
    def on_enter_pressed():
        """全局回车键回调"""
        state["pending_enter"] = True

    def close_window():
        log("close_window 被调用")
        app.reset()
        if gui:
            gui.destroy()
            log("窗口已关闭")

    def start_recording():
        nonlocal gui
        if app.state != AppState.IDLE:
            return
        app.save_original_window()
        log(f"原始窗口: {app.original_window}")

        # 创建 GUI
        gui = VoiceGUI()
        gui.create_window()
        gui.update_status("录音中... 请说话", "red")
        gui.show_text("录音中...")

        # 立即更新显示窗口
        gui.update()

        # 开始录音
        app.start_recording()

    # 热键回调
    def on_hotkey():
        state["pending_hotkey"] = True

    # 热键管理
    hotkey = HotkeyManager(trigger_key='d', modifier_key='alt')
    hotkey.set_callback(on_hotkey)
    hotkey.set_enter_callback(on_enter_pressed)
    hotkey.start()
    log("Alt+D 热键已注册")

    log("\n等待输入...")
    log("按 Ctrl+C 退出")

    # 主循环
    try:
        while True:
            # 检查 Alt+D 热键
            if state["pending_hotkey"]:
                state["pending_hotkey"] = False
                start_recording()

            # 检查回车键
            if state["pending_enter"]:
                state["pending_enter"] = False
                if app.state == AppState.RECORDING:
                    log("停止录音，开始识别...")
                    if gui:
                        gui.update_status("识别中...", "orange")
                    audio_path = app.stop_recording()
                    if audio_path:
                        def do_recognize():
                            app.recognize(audio_path)
                        threading.Thread(target=do_recognize, daemon=True).start()

            # 检查识别完成
            if app.state == AppState.DONE:
                text = app.last_result
                if text and gui:
                    gui.update_status("识别成功！即将注入...", "green")
                    gui.show_text(text)
                    time.sleep(0.5)
                    close_window()
                    app.inject(text)

            # 检查识别错误
            if app.state == AppState.ERROR and gui:
                gui.update_status(f"识别失败: {app.last_error}", "red")
                app.reset()

            # 运行 GUI
            if gui:
                gui.update()

            time.sleep(0.05)
    except KeyboardInterrupt:
        log("\n退出")
        hotkey.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
