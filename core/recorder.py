# 录音模块

import sounddevice as sd
import numpy as np
import tempfile
import subprocess
import threading
import time
import os
import wave
import uuid

from .logger import logger


class Recorder:
    def __init__(self, max_duration=300, device=None):
        self.max_duration = max_duration
        self.recording = False
        self.audio_data = []
        self.sample_rate = 16000
        self.start_time = None
        self.stream = None
        self.device = device
        self.use_sounddevice = False
        self.use_arecord = False
        self._write_thread = None
        self._write_running = False
        self._wave_file = None

        # 获取设备支持的采样率
        if device is not None:
            try:
                d = sd.query_devices(device)
                self.sample_rate = int(d.get('default_samplerate', 16000))
                logger.info(f"使用设备 {device}: {d.get('name', '')[:30]}, 采样率: {self.sample_rate}")
            except:
                pass

    def start(self):
        """开始录音"""
        self.recording = True
        self.audio_data = []
        self.start_time = time.time()

        # 优先使用 sounddevice（实时写入文件）
        try:
            logger.info("使用 sounddevice 录音（实时写入）")
            self.use_soundfile = True
            # 使用 UUID 确保每次都是全新的文件
            self.temp_file = f"/tmp/voice_input_{uuid.uuid4().hex}.wav"

            # 确保目录存在
            os.makedirs("/tmp", exist_ok=True)

            # 创建 WAV 文件用于实时写入
            self._wave_file = wave.open(self.temp_file, 'wb')
            self._wave_file.setnchannels(1)
            self._wave_file.setsampwidth(2)
            self._wave_file.setframerate(16000)

            def callback(indata, frames, time_info, status):
                if status:
                    logger.debug(f"录音状态: {status}")
                # 实时写入音频数据到文件
                audio_int16 = (indata.flatten() * 32767).astype(np.int16)
                self._wave_file.writeframes(audio_int16.tobytes())
                self.audio_data.append(indata.copy())

            self.stream = sd.InputStream(
                device=self.device,
                samplerate=16000,
                channels=1,
                dtype='float32',
                callback=callback
            )
            self.stream.start()
            logger.info("sounddevice 录音已启动")
            return
        except Exception as e:
            logger.warning(f"sounddevice 失败: {e}")

        # 备用 ffmpeg
        try:
            logger.info("使用 ffmpeg 录音")
            self.use_ffmpeg = True
            self.temp_file = tempfile.mktemp(suffix=".wav")
            cmd = ["ffmpeg", "-f", "pulse", "-i", "default", "-ar", "16000", "-ac", "1", "-t", str(self.max_duration), "-y", self.temp_file]
            self.process = subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
            return
        except Exception as e:
            logger.warning(f"ffmpeg 失败: {e}")

        # 备用 arecord
        try:
            logger.info("使用 arecord 录音 (pulse)")
            self.use_arecord = True
            self.temp_file = tempfile.mktemp(suffix=".wav")
            cmd = ["arecord", "-D", "pulse", "-f", "S16_LE", "-r", "16000", "-c", "1", "-d", str(self.max_duration), self.temp_file]
            self.process = subprocess.Popen(cmd)
        except Exception as e:
            logger.error(f"arecord 也失败: {e}")

    def stop(self):
        """停止录音"""
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        # 关闭实时写入的 WAV 文件
        if getattr(self, '_wave_file', None):
            try:
                self._wave_file.close()
            except:
                pass
            self._wave_file = None
        elif getattr(self, 'use_ffmpeg', False):
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                try:
                    self.process.kill()
                except:
                    pass
        elif getattr(self, 'use_arecord', False):
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                try:
                    self.process.kill()
                except:
                    pass

    def get_temp_file(self):
        """获取当前录音的临时文件路径（用于实时识别）"""
        return getattr(self, 'temp_file', None)

    def is_recording(self):
        """检查是否正在录音"""
        return self.recording

    def get_duration(self):
        if self.start_time:
            return time.time() - self.start_time
        return 0

    def save(self, filepath, target_rate=16000):
        """保存音频到文件"""
        if getattr(self, 'use_ffmpeg', False):
            # ffmpeg 已保存到文件，直接移动
            if os.path.exists(self.temp_file):
                import shutil
                shutil.move(self.temp_file, filepath)
                return filepath
            return None

        if getattr(self, 'use_arecord', False):
            # arecord 已保存到文件，直接移动
            if os.path.exists(self.temp_file):
                import shutil
                shutil.move(self.temp_file, filepath)
                return filepath
            return None

        if not self.audio_data:
            return None

        audio = np.concatenate(self.audio_data)
        # 转换为 float
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # 转码到目标采样率
        if self.sample_rate != target_rate:
            import scipy.signal as signal
            num_samples = int(len(audio) * target_rate / self.sample_rate)
            audio = signal.resample(audio, num_samples)

        # 转换为 int16
        audio = (audio * 32767).astype(np.int16)

        # 写入 WAV 文件
        import wave
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(target_rate)
            wf.writeframes(audio.tobytes())

        return filepath


def record_audio(max_duration=300, callback=None):
    """录音函数"""
    recorder = Recorder(max_duration=max_duration)
    recorder.start()

    logger.info(f"录音中... (最长 {max_duration} 秒，按 Enter 结束)")

    try:
        while recorder.recording:
            duration = recorder.get_duration()
            if callback:
                callback(duration)
            if duration >= max_duration:
                logger.info(f"已达最大时长 {max_duration} 秒，自动结束")
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("录音取消")
    finally:
        recorder.stop()

    if recorder.audio_data:
        audio_path = tempfile.mktemp(suffix=".wav")
        recorder.save(audio_path)
        return audio_path

    return None
