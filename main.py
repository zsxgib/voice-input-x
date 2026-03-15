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
from core.logger import logger
from gui.window import VoiceGUI
from gui.tray import SystemTray


def main():
    """主函数"""
    # 热键配置 - 格式: "修饰键+触发键"，多个修饰键用 + 分隔
    # 可选修饰键: alt, ctrl, shift
    # 示例: alt+d, alt+v, ctrl+shift+v, alt+shift+d
    # Alt+D 在浏览器中会聚焦到地址栏，推荐使用 Alt+Shift+D
    # 从配置读取热键
    HOTKEY_MODIFIER = config.hotkey.modifier
    HOTKEY_KEY = config.hotkey.key

    logger.info("=" * 50)
    logger.info("       语音输入法")
    logger.info("=" * 50)
    logger.info(f"热键: {HOTKEY_MODIFIER}+{HOTKEY_KEY}")
    logger.info(f"最大时长: {config.recorder.max_duration} 秒")
    logger.info(f"模型: {config.asr.model}")
    logger.info("=" * 50)
    logger.info(f"按 {HOTKEY_MODIFIER.upper()}+{HOTKEY_KEY.upper()} 开始录音")
    logger.info("按 回车 停止并注入")
    logger.info("按 Ctrl+C 退出")
    logger.info("=" * 50)

    # 创建应用实例
    app = VoiceApp()
    app.init()

    # 创建系统托盘
    tray = SystemTray(app, VoiceGUI)
    tray.create()
    tray.run()
    logger.info("系统托盘已创建")

    # 预热模型
    threading.Thread(target=app.warmup, daemon=True).start()

    # GUI
    gui = None

    # 状态
    state = {
        "pending_hotkey": False,
        "pending_enter": False,
        "pending_escape": False,
    }

    # 回调函数
    def on_enter_pressed():
        """全局回车键回调"""
        state["pending_enter"] = True

    def on_escape_pressed():
        """全局 ESC 键回调"""
        state["pending_escape"] = True

    def close_window():
        logger.info("close_window 被调用")
        if gui:
            # 最小化到托盘，而不是真正销毁
            gui.hide()
            logger.info("窗口已隐藏到托盘")

    def start_recording():
        nonlocal gui
        if app.state != AppState.IDLE:
            return
        app.save_original_window()
        logger.info(f"原始窗口: {app.original_window}")

        # 创建 GUI
        gui = VoiceGUI()
        gui.create_window()
        gui.update_status("录音中... 请说话", "red")
        gui.show_text("正在倾听...")

        # 设置实时识别回调
        def on_realtime_text(text):
            if gui:
                gui.show_text_thread_safe(text)

        app.set_realtime_callback(on_realtime_text)

        # 将 gui 传给托盘
        tray.set_gui(gui)

        # 立即更新显示窗口
        gui.update()

        # 开始录音
        app.start_recording()

    # 热键回调
    def on_hotkey():
        state["pending_hotkey"] = True

    # 热键管理
    hotkey = HotkeyManager(trigger_key=HOTKEY_KEY, modifier_key=HOTKEY_MODIFIER)
    hotkey.set_callback(on_hotkey)
    hotkey.set_enter_callback(on_enter_pressed)
    hotkey.set_escape_callback(on_escape_pressed)
    hotkey.start()
    logger.info(f"{HOTKEY_MODIFIER.upper()}+{HOTKEY_KEY.upper()} 热键已注册")
    logger.info("ESC 取消已注册")

    logger.info("\n等待输入...")
    logger.info("按 Ctrl+C 退出")

    # 主循环
    try:
        while app.running:
            # 检查 Alt+D 热键
            if state["pending_hotkey"]:
                state["pending_hotkey"] = False
                start_recording()

            # 检查 ESC 键 - 取消录音
            if state["pending_escape"]:
                state["pending_escape"] = False
                if app.state == AppState.RECORDING:
                    logger.info("ESC 取消录音")
                    app.stop_recording()
                    if gui:
                        gui.update_status("已取消", "gray")
                        close_window()
                    app.reset()

            # 检查回车键
            if state["pending_enter"]:
                state["pending_enter"] = False
                if app.state == AppState.RECORDING:
                    logger.info("停止录音，开始识别...")
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
                    app.reset()

            # 检查识别错误
            if app.state == AppState.ERROR and gui:
                gui.update_status(f"识别失败: {app.last_error}", "red")
                app.reset()

            # 运行 GUI
            if gui:
                gui.update()

            time.sleep(0.05)
    except KeyboardInterrupt:
        logger.info("\n退出")
        hotkey.stop()
        tray.stop()
        app.running = False
        sys.exit(0)


if __name__ == "__main__":
    main()
