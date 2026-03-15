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
from .logger import logger


class VoiceApp:
    """语音输入应用核心"""

    def __init__(self):
        self.state = AppState.IDLE
        self.running = True  # 用于控制程序退出
        self.recorder = None
        self.recognizer = Recognizer(config.asr.model, config.asr.language)
        self.original_window = None
        self.original_window_name = None
        self.original_window_class = None
        self.original_window_pid = None
        self.inject_done = False
        self.last_result = None
        self.last_error = None
        self.recognition_done = False

        # 实时识别相关
        self._realtime_thread = None
        self._realtime_running = False
        self._realtime_callback = None  # GUI 回调：实时更新文字
        self._last_realtime_text = ""  # 上一次识别的文字，避免重复显示
        self._realtime_recognizing = False  # 是否正在识别中
        self._realtime_recognizer = None  # 实时识别用的小模型

    def log(self, msg: str):
        """日志"""
        logger.info(msg)

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
            if not self.original_window:
                self.log(f"警告: getactivewindow 返回空结果")

            # 同时保存窗口名称、类名和 PID，用于失效时查找
            if self.original_window:
                name_result = subprocess.run(
                    ["xdotool", "getwindowname", self.original_window],
                    capture_output=True, text=True
                )
                if name_result.returncode == 0:
                    self.original_window_name = name_result.stdout.strip()

                # 获取窗口类名
                class_result = subprocess.run(
                    ["xdotool", "getwindowclassname", self.original_window],
                    capture_output=True, text=True
                )
                if class_result.returncode == 0:
                    self.original_window_class = class_result.stdout.strip()

                # 获取窗口 PID（最可靠的方式）
                pid_result = subprocess.run(
                    ["xdotool", "getwindowpid", self.original_window],
                    capture_output=True, text=True
                )
                if pid_result.returncode == 0:
                    self.original_window_pid = pid_result.stdout.strip()

                self.log(f"保存窗口: ID={self.original_window}, PID={self.original_window_pid}, 类名={self.original_window_class}")
        except:
            self.original_window = None
            self.original_window_name = None
            self.original_window_class = None
            self.original_window_pid = None

    def set_realtime_callback(self, callback):
        """设置实时识别回调，用于更新 GUI"""
        self._realtime_callback = callback

    def start_recording(self):
        """开始录音"""
        if self.state != AppState.IDLE:
            return

        # 窗口已在 main.py 中保存，这里不再重复保存
        self.recorder = Recorder(
            max_duration=config.recorder.max_duration,
            device=config.recorder.device
        )
        self.recorder.start()
        self.state = AppState.RECORDING

        # 启动实时识别线程
        self._realtime_running = True
        self._last_realtime_text = ""
        self._realtime_thread = threading.Thread(target=self._realtime_recognize, daemon=True)
        self._realtime_thread.start()

    def _realtime_recognize(self):
        """实时识别线程：每隔几秒识别一次已录制的音频（非阻塞）"""
        import os

        # 等待主线程的模型加载完成
        import time
        for _ in range(50):  # 最多等 5 秒
            if self.recognizer.model is not None:
                break
            time.sleep(0.1)

        # 复用主线程已加载的 large-v3 模型
        model = self.recognizer.model
        if model is None:
            self.log("警告: 模型未加载，跳过实时识别")
            return
        self.log("复用 large-v3 模型进行实时识别")

        interval = 0.05  # 每 0.05 秒检查一次

        while self._realtime_running and self.state == AppState.RECORDING:
            time.sleep(interval)

            if not self._realtime_running or self.state != AppState.RECORDING:
                break

            # 如果正在识别中，跳过这次
            if self._realtime_recognizing:
                continue

            # 获取临时文件
            temp_file = self.recorder.get_temp_file() if self.recorder else None
            if not temp_file or not os.path.exists(temp_file):
                continue

            # 检查录音是否已开始足够时间（至少 1 秒后开始识别）
            if self.recorder and self.recorder.start_time:
                elapsed = time.time() - self.recorder.start_time
                if elapsed < 1.0:  # 至少录音 1 秒后才开始识别
                    continue

            # 检查文件是否有足够内容（至少 20KB，约 1.2 秒音频）
            try:
                if os.path.getsize(temp_file) < 20000:
                    continue
            except:
                continue

            # 标记为正在识别
            self._realtime_recognizing = True

            try:
                # 用 large-v3 模型实时识别
                segments, info = model.transcribe(temp_file, language=self.recognizer.language, beam_size=1)
                text = " ".join([seg.text for seg in segments])

                if text and text.strip() and text != self._last_realtime_text:
                    self._last_realtime_text = text
                    self.log(f"实时识别: {text}")

                    # 通过回调更新 GUI
                    if self._realtime_callback:
                        self._realtime_callback(text)
            except Exception as e:
                self.log(f"实时识别错误: {e}")
            finally:
                self._realtime_recognizing = False

    def stop_recording(self) -> str:
        """停止录音，返回音频路径"""
        if self.state != AppState.RECORDING:
            return None

        # 停止实时识别线程
        self._realtime_running = False
        if self._realtime_thread:
            self._realtime_thread.join(timeout=1)

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

        window_id = self.original_window

        # 尝试用保存的窗口ID激活
        if window_id:
            result = subprocess.run(
                ["xdotool", "windowactivate", "--sync", window_id],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                self.log(f"激活原始窗口: {window_id}")
                time.sleep(0.2)
            else:
                # 窗口ID失效，尝试用 PID 查找（最可靠，因为每个进程PID唯一）
                self.log("原始窗口ID失效，尝试查找窗口...")
                found = False

                # 优先用 PID 搜索（最可靠，不会混淆不同应用）
                if self.original_window_pid:
                    result = subprocess.run(
                        ["xdotool", "search", "--pid", self.original_window_pid],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        window_ids = result.stdout.strip().split('\n')
                        # 优先找名称匹配的窗口
                        matched_window_id = None
                        original_name_lower = self.original_window_name.lower() if self.original_window_name else ""

                        # 先找名称包含原始窗口名称的窗口
                        for wid in window_ids:
                            if wid.strip():
                                check = subprocess.run(
                                    ["xdotool", "getwindowname", wid.strip()],
                                    capture_output=True, text=True
                                )
                                if check.returncode == 0:
                                    found_name = check.stdout.strip().lower()
                                    # 如果名称包含原始窗口名称的关键词
                                    if original_name_lower and original_name_lower[:10] in found_name:
                                        matched_window_id = wid.strip()
                                        self.log(f"通过PID+名称匹配找到窗口: {matched_window_id} (名称: {found_name[:30]})")
                                        break

                        # 如果没找到匹配的，使用原来的第一个
                        if not matched_window_id:
                            for wid in window_ids:
                                if wid.strip():
                                    check = subprocess.run(
                                        ["xdotool", "getwindowname", wid.strip()],
                                        capture_output=True, text=True
                                    )
                                    if check.returncode == 0:
                                        matched_window_id = wid.strip()
                                        self.log(f"通过PID找到窗口: {matched_window_id} (名称: {check.stdout.strip()[:30]})")
                                        break

                        if matched_window_id:
                            window_id = matched_window_id
                            try:
                                subprocess.run(
                                    ["xdotool", "windowactivate", "--sync", window_id],
                                    capture_output=True,
                                    timeout=3
                                )
                            except subprocess.TimeoutExpired:
                                self.log("窗口激活超时，尝试使用其他方式")
                            time.sleep(0.2)
                            found = True

                # PID搜索失败，尝试用类名搜索
                if not found and self.original_window_class:
                    result = subprocess.run(
                        ["xdotool", "search", "--class", self.original_window_class],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        window_ids = result.stdout.strip().split('\n')
                        # 过滤并验证窗口
                        for wid in window_ids:
                            if wid.strip():
                                check = subprocess.run(
                                    ["xdotool", "getwindowname", wid.strip()],
                                    capture_output=True, text=True
                                )
                                if check.returncode == 0:
                                    window_id = wid.strip()
                                    self.log(f"通过类名找到窗口: {window_id} ({self.original_window_class})")
                                    subprocess.run(
                                        ["xdotool", "windowactivate", "--sync", window_id],
                                        capture_output=True,
                                        timeout=2
                                    )
                                    time.sleep(0.2)
                                    found = True
                                    break

                # 类名搜索失败，尝试用名称搜索
                if not found and self.original_window_name:
                    result = subprocess.run(
                        ["xdotool", "search", "--name", self.original_window_name],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        window_ids = result.stdout.strip().split('\n')
                        # 过滤并验证窗口
                        for wid in window_ids:
                            if wid.strip():
                                check = subprocess.run(
                                    ["xdotool", "getwindowname", wid.strip()],
                                    capture_output=True, text=True
                                )
                                if check.returncode == 0:
                                    window_id = wid.strip()
                                    self.log(f"通过名称找到窗口: {window_id}")
                                    subprocess.run(
                                        ["xdotool", "windowactivate", "--sync", window_id],
                                        capture_output=True,
                                        timeout=2
                                    )
                                    time.sleep(0.2)
                                    found = True
                                    break

                if not found:
                    self.log("无法找到原始窗口")
                    return
        else:
            self.log("无原始窗口信息")
            return

        # 注入
        inject_text(text, window_id)
        self.log("注入完成")

    def reset(self):
        """重置状态"""
        self._realtime_running = False
        if self._realtime_thread:
            self._realtime_thread.join(timeout=1)

        self.state = AppState.IDLE
        self.inject_done = False
        self.recorder = None
        self.original_window = None
        self.original_window_name = None
        self.original_window_class = None
        self.original_window_pid = None
        self._last_realtime_text = ""
        self._realtime_recognizing = False
