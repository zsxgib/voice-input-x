# 语音识别模块 (whisperX + faster-whisper 后端)

import sys
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pyannote")

import torch
import requests

from .logger import logger


class Recognizer:
    def __init__(self, model_name="large-v3", language="zh"):
        self.model_name = model_name
        self.language = language
        self.model = None

    def load_model(self):
        """加载模型"""
        if self.model is None:
            # 使用 faster-whisper 后端
            from faster_whisper import WhisperModel

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"加载模型: {self.model_name} (设备: {device})")
            self.model = WhisperModel(self.model_name, device=device, compute_type="float16")
            logger.info("模型加载完成")
        return self.model

    def recognize(self, audio_path):
        """识别音频文件"""
        model = self.load_model()

        logger.info(f"识别中: {audio_path}")
        segments, info = model.transcribe(audio_path, language=self.language, beam_size=5)

        # 提取文本
        text_parts = [seg.text for seg in segments]
        result = " ".join(text_parts)
        logger.info(f"识别完成: {len(result)} 字符")
        return result


def llm_refine(text, model="qwen2.5-coder:latest"):
    """使用 LLM 润色文本"""
    if not text or len(text) < 2:
        return text

    logger.info(f"LLM 整理: 调用 {model}...")

    prompt = f"""你是一个专业的文字编辑。请对以下语音识别结果进行优化：
1. 添加合适的标点符号
2. 纠正同音字错误（如"的/得/地"混用，根据上下文判断正确用字）
3. 根据上下文判断应该是中文还是英文
4. 保持原意和口语风格
5. 只删除连续重复超过2次的词
6. 输出简体中文，不要使用繁体字

原文：{text}

优化后："""

    try:
        logger.info("LLM: 发送请求到 Ollama...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30
        )
        logger.info(f"LLM: 响应状态 {response.status_code}")
        if response.status_code == 200:
            result = response.json().get("response", text)
            logger.info("LLM: 整理完成")
            return result.strip()
        else:
            logger.warning(f"LLM: 请求失败 {response.status_code}")
    except requests.exceptions.Timeout:
        logger.warning("LLM: 请求超时 (30秒)")
    except requests.exceptions.ConnectionError:
        logger.warning("LLM: 无法连接到 Ollama (服务是否启动?)")
    except Exception as e:
        logger.error(f"LLM 润色失败: {e}")

    return text


def recognize_audio(audio_path, model_name="small", language="zh", use_llm=True):
    """识别音频文件"""
    recognizer = Recognizer(model_name, language)
    text = recognizer.recognize(audio_path)

    # LLM 润色
    if use_llm and text:
        logger.info("LLM 润色中...")
        text = llm_refine(text)
        logger.info(f"润色完成: {len(text)} 字符")

    return text
