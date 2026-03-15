# 热键模块

from pynput import keyboard


class HotkeyManager:
    """热键管理器"""

    def __init__(self, trigger_key='d', modifier_key='alt'):
        self.trigger_key = trigger_key
        self.modifier_key = modifier_key
        self.modifier_pressed = False
        self.trigger_pressed = False
        self.on_hotkey = None
        self.on_enter = None
        self.hotkey_listener = None
        self.enter_listener = None

    def set_callback(self, callback):
        """设置热键回调"""
        self.on_hotkey = callback

    def set_enter_callback(self, callback):
        """设置回车键回调"""
        self.on_enter = callback

    def start(self):
        """启动热键监听"""
        def on_press(key):
            try:
                # 检测修饰键 (Alt)
                if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
                    self.modifier_pressed = True

                # 检测触发键
                if hasattr(key, 'char') and key.char == self.trigger_key:
                    if self.modifier_pressed and not self.trigger_pressed:
                        self.trigger_pressed = True
                        if self.on_hotkey:
                            self.on_hotkey()

            except:
                pass

        def on_release(key):
            try:
                if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
                    self.modifier_pressed = False
                if hasattr(key, 'char') and key.char == self.trigger_key:
                    self.trigger_pressed = False
            except:
                pass

        # 主热键监听
        self.hotkey_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.hotkey_listener.start()

        # 全局回车键监听
        if self.on_enter:
            def on_enter_press(key):
                try:
                    if key == keyboard.Key.enter or key == keyboard.Key.num_lock:
                        if self.on_enter:
                            self.on_enter()
                except:
                    pass

            self.enter_listener = keyboard.Listener(on_press=on_enter_press)
            self.enter_listener.start()

    def stop(self):
        """停止热键监听"""
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        if self.enter_listener:
            self.enter_listener.stop()
