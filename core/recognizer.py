# 语音识别模块 (Qwen3-ASR 后端, transformers backend)
# 兼容旧 faster-whisper 接口 (Recognizer(model_name, language) / .recognize(audio_path))

import os
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

import torch

from .logger import logger


# 默认本地模型路径: 之前用 ModelScope 拉好的 1.7B (Qwen 官方分片版)
DEFAULT_MODEL_PATH = os.environ.get(
    "QWEN_ASR_MODEL_PATH",
    "/home/zsx/.cache/modelscope/Qwen/Qwen3-ASR-1___7B",
)

# 旧 faster-whisper 的 model name -> 视为"未指定" (Qwen-ASR 不需要选模型大小)
_WHISPER_MODEL_NAMES = {"tiny", "base", "small", "medium", "large", "large-v2", "large-v3",
                        "tiny.en", "base.en", "small.en", "medium.en"}


class Recognizer:
    def __init__(self, model_path=DEFAULT_MODEL_PATH, language="auto"):
        """
        Args:
            model_path: Qwen3-ASR 本地路径 / HF repo id;
                         若传入 faster-whisper 风格的 model name, 自动忽略, 用默认 Qwen 路径
            language:   "auto" 表示自动识别, 也可显式传 "Chinese" / "English" / "zh" / "en"
        """
        if isinstance(model_path, str) and model_path.lower() in _WHISPER_MODEL_NAMES:
            logger.info(f"model_path={model_path!r} 是旧 faster-whisper 名称, 忽略, 改用 {DEFAULT_MODEL_PATH}")
            model_path = DEFAULT_MODEL_PATH
        self.model_path = model_path
        self.language = self._normalize_lang(language)
        self.model = None

    @staticmethod
    def _normalize_lang(lang):
        """统一语言参数: 'zh' -> 'Chinese', 'en' -> 'English', 'auto'/''/None -> None"""
        if lang is None:
            return None
        s = str(lang).strip()
        if s.lower() in ("", "auto", "auto-detect", "multilingual"):
            return None
        # Whisper 风格短码 -> Qwen3-ASR 名称 (子集)
        mp = {"zh": "Chinese", "en": "English", "ja": "Japanese", "ko": "Korean",
              "fr": "French", "de": "German", "es": "Spanish", "ru": "Russian"}
        return mp.get(s.lower(), s)

    def load_model(self):
        """懒加载 Qwen3-ASR (transformers 后端)"""
        if self.model is None:
            from qwen_asr import Qwen3ASRModel

            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.bfloat16 if device == "cuda" else torch.float32
            logger.info(f"加载 Qwen3-ASR: {self.model_path} (设备: {device}, dtype: {dtype})")
            self.model = Qwen3ASRModel.from_pretrained(
                self.model_path,
                dtype=dtype,
                device_map=device,
                max_inference_batch_size=4,
                max_new_tokens=4096,
            )
            logger.info("Qwen3-ASR 模型加载完成")
        return self.model

    def recognize(self, audio_path):
        """识别音频文件 -> str"""
        model = self.load_model()
        lang = self.language  # None 表示自动识别
        logger.info(f"识别中: {audio_path} (lang={lang})")
        results = model.transcribe(
            audio=[audio_path],
            language=lang,
            return_time_stamps=False,
        )
        if not results:
            return ""
        text = (results[0].text or "").strip()
        logger.info(f"识别完成: {len(text)} 字符, language={results[0].language}")
        return text


def llm_refine(text, model="qwen2.5-coder:latest"):
    """使用 LLM 润色文本 (沿用原版 Ollama 流程)"""
    if not text or len(text) < 2:
        return text

    import requests

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
            timeout=30,
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


def recognize_audio(audio_path, model_name=None, language="auto", use_llm=True):
    """识别音频文件 (model_name 是旧参数, 兼容忽略)"""
    recognizer = Recognizer(model_path=DEFAULT_MODEL_PATH, language=language)
    text = recognizer.recognize(audio_path)
    if use_llm and text:
        logger.info("LLM 润色中...")
        text = llm_refine(text)
        logger.info(f"润色完成: {len(text)} 字符")
    return text
