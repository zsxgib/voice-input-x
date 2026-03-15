# 状态定义

from enum import Enum


class AppState(Enum):
    """应用状态"""
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"
