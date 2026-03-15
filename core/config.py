# 配置

from dataclasses import dataclass
from typing import Optional


@dataclass
class HotkeyConfig:
    """热键配置"""
    trigger: str = "alt+d"  # 主热键，可选: alt+d, alt+v, alt+q, alt+z, alt+`


@dataclass
class RecorderConfig:
    """录音配置"""
    max_duration: int = 300
    sample_rate: int = 16000
    device: Optional[int] = None


@dataclass
class ASRConfig:
    """ASR 配置"""
    model: str = "large-v3"
    language: str = "zh"
    compute_type: str = "float16"


@dataclass
class LLMConfig:
    """LLM 配置"""
    enabled: bool = True
    model: str = "qwen2.5-coder:latest"
    url: str = "http://localhost:11434/api/generate"
    timeout: int = 30


@dataclass
class InjectorConfig:
    """注入配置"""
    method: str = "ctrl+v"


@dataclass
class AppConfig:
    """应用配置"""
    hotkey: HotkeyConfig = None
    recorder: RecorderConfig = None
    asr: ASRConfig = None
    llm: LLMConfig = None
    injector: InjectorConfig = None

    def __post_init__(self):
        if self.hotkey is None:
            self.hotkey = HotkeyConfig()
        if self.recorder is None:
            self.recorder = RecorderConfig()
        if self.asr is None:
            self.asr = ASRConfig()
        if self.llm is None:
            self.llm = LLMConfig()
        if self.injector is None:
            self.injector = InjectorConfig()


# 全局配置实例
config = AppConfig()
