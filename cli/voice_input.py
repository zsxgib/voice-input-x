#!/usr/bin/env python3
"""
语音输入法 - CLI 入口
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import config
from core.app import VoiceApp


def main():
    """主函数"""
    print("=" * 50)
    print("       语音输入法 (CLI)")
    print("=" * 50)
    print(f"模型: {config.asr.model}")
    print("=" * 50)

    # 创建应用
    app = VoiceApp()
    app.init()
    app.warmup()

    # 开始录音
    print("\n按回车开始录音...")
    input()

    print("录音中... 按回车停止")
    app.start_recording()

    input()

    # 停止录音
    print("停止录音...")
    audio_path = app.stop_recording()

    if audio_path:
        # 识别
        app.recognize(audio_path)
        text = app.last_result
        print(f"\n识别结果:\n{text}\n")

        # 注入
        confirm = input("确认注入？(y/n): ").strip().lower()
        if confirm == 'y':
            app.inject(text)

    print("\n完成")


if __name__ == "__main__":
    main()
