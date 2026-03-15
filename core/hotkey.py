# 热键模块

from pynput import keyboard


class HotkeyManager:
    """热键管理器"""

    def __init__(self, trigger_key='d', modifier_key='alt'):
        self.trigger_key = trigger_key.lower()
        self.modifier_key = modifier_key.lower()
        self.on_hotkey = None
        self.on_enter = None
        self.on_escape = None
        self.hotkey_listener = None
        self.key_listener = None

    def set_callback(self, callback):
        """设置热键回调"""
        self.on_hotkey = callback

    def set_enter_callback(self, callback):
        """设置回车键回调"""
        self.on_enter = callback

    def set_escape_callback(self, callback):
        """设置 ESC 键回调"""
        self.on_escape = callback

    def start(self):
        """启动热键监听"""
        # 构建热键字符串，如 <alt>+d 或 <alt>+<shift>+d
        parts = self.modifier_key.split('+')
        hotkey_parts = [f'<{p}>' for p in parts] + [self.trigger_key]
        hotkey_str = '+'.join(hotkey_parts)

        # 使用 GlobalHotKeys
        self.hotkey_listener = keyboard.GlobalHotKeys({
            hotkey_str: self._on_hotkey_pressed
        })

        # 同时监听回车和 ESC
        def on_press(key):
            if self.on_enter:
                if key == keyboard.Key.enter or key == keyboard.Key.num_lock:
                    self.on_enter()
            if self.on_escape:
                if key == keyboard.Key.esc:
                    self.on_escape()

        self.key_listener = keyboard.Listener(on_press=on_press)

        self.hotkey_listener.start()
        self.key_listener.start()

    def _on_hotkey_pressed(self):
        """热键触发回调"""
        if self.on_hotkey:
            self.on_hotkey()

    def stop(self):
        """停止热键监听"""
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        if self.key_listener:
            self.key_listener.stop()
