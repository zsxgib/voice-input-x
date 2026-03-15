# 应用核心模块

import threading
import subprocess
import tempfile
import time

from .state import AppState
from .recorder import Recorder
from .recognizer import Recognizer
from .injector import inject_text
from .config import config


class VoiceApp:
    """语音输入应用核心"""

    def __init__(self):
        self.state = AppState.IDLE
        self.recorder = None
        self.recognizer = Recognizer(config.asr.model, config.asr.language)
        self.original_window = None
        self.inject_done = False
        self.last_result = None
        self.last_error = None
        self.recognition_done = False

    def log(self, msg: str):
        """日志"""
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] {msg}", flush=True)

    def init(self):
        """初始化"""
        self.log("初始化组件...")

    def warmup(self):
        """预热模型"""
        self.recognizer.load_model()
        self.log("模型预热完成!")

    def save_original_window(self):
        """保存原始窗口"""
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True
            )
            self.original_window = result.stdout.strip()
        except:
            self.original_window = None

    def start_recording(self):
        """开始录音"""
        if self.state != AppState.IDLE:
            return

        self.save_original_window()
        self.recorder = Recorder(
            max_duration=config.recorder.max_duration,
            device=config.recorder.device
        )
        self.recorder.start()
        self.state = AppState.RECORDING

    def stop_recording(self) -> str:
        """停止录音，返回音频路径"""
        if self.state != AppState.RECORDING:
            return None

        self.recorder.stop()
        audio_path = tempfile.mktemp(suffix=".wav")
        self.recorder.save(audio_path)
        return audio_path

    def recognize(self, audio_path: str):
        """识别并处理结果"""
        import time as time_module
        t0 = time_module.time()

        try:
            # ASR 识别
            self.log("ASR 开始...")
            text = self.recognizer.recognize(audio_path)
            t1 = time_module.time()
            self.log(f"ASR 完成 ({t1-t0:.1f}s): {text}")

            # LLM 整理
            if config.llm.enabled:
                from .recognizer import llm_refine
                self.log("LLM 开始...")
                text = llm_refine(text)
                t2 = time_module.time()
                self.log(f"LLM 完成 ({t2-t1:.1f}s): {text}")

            self.last_result = text
            self.state = AppState.DONE
            self.recognition_done = True
            self.log(f"总时间: {time_module.time()-t0:.1f}s")

        except Exception as e:
            self.log(f"识别错误: {e}")
            self.last_error = str(e)
            self.state = AppState.ERROR
            self.recognition_done = True

    def inject(self, text: str):
        """注入文字"""
        if self.inject_done or not text:
            return
        self.inject_done = True

        # 激活原始窗口
        if self.original_window:
            try:
                subprocess.run(
                    ["xdotool", "windowactivate", "--sync", self.original_window],
                    capture_output=True,
                    timeout=2
                )
                self.log(f"激活原始窗口: {self.original_window}")
                time.sleep(0.2)
            except:
                pass

        # 注入
        inject_text(text, self.original_window)
        self.log("注入完成")

    def reset(self):
        """重置状态"""
        self.state = AppState.IDLE
        self.inject_done = False
        self.recorder = None
