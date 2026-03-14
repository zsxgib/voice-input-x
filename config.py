# 配置

HOTKEY = "Alt+D"              # 全局热键
MAX_DURATION = 300             # 最大录音时长（秒）
WHISPER_MODEL = "large-v3"        # Whisper 模型: tiny/base/small/medium/large-v3
LANGUAGE = "zh"                # 识别语言
COMPUTE_TYPE = "float16"       # 计算类型: float16/int8
AUDIO_DEVICE = None              # 录音设备: None=默认, 4=UGREEN, 5=HDA, 14=pulse
INJECT_KEY = "ctrl+v"           # 注入快捷键: ctrl+v / ctrl+shift+v
USE_LLM = False                # 是否使用 LLM 整理（需要 Ollama 运行）
