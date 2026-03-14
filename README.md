# voice-input

Linux 语音输入法 - 按键触发录音，识别后预览确认，自动输入

## 安装

```bash
# 克隆项目
git clone https://github.com/zsxgib/voice-input.git
cd voice-input

# 安装系统依赖
sudo apt install ffmpeg libportaudio2 xdotool

# 安装 Python 依赖
pip install -r requirements.txt

# 预热模型（首次运行自动下载）
python voice_input.py
```

## 使用

1. 运行程序：`python voice_input.py`
2. 按 `Ctrl+Shift+V` 开始录音
3. 再次按 `Ctrl+Shift+V` 结束录音（或等 5 分钟自动结束）
4. 预览窗口显示识别结果
5. 按 `Enter` 确认，或 `Esc` 取消
6. 确认后文字自动输入到当前应用

## 配置

修改 `config.py`:

```python
HOTKEY = "Ctrl+Shift+V"       # 全局热键
MAX_DURATION = 300             # 最大录音时长（秒）
WHISPER_MODEL = "small"        # Whisper 模型
LANGUAGE = "zh"                # 识别语言
```

## 依赖

- Python 3.8+
- ffmpeg
- xdotool
- python-keybinder3
- python-sounddevice
- faster-whisper
- pyperclip

## 注意事项

- 需要 X11 或 Wayland 会话
- 确保麦克风权限
- 首次运行会下载 Whisper 模型（约几百 MB）
