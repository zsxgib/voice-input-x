# 系统托盘模块

import threading
from PIL import Image, ImageDraw
import pystray


class SystemTray:
    """系统托盘管理"""

    def __init__(self, app, gui_class):
        self.app = app
        self.gui_class = gui_class
        self.tray = None
        self.gui = None

    def _create_icon(self):
        """创建托盘图标（简单的麦克风图标）"""
        # 创建 64x64 的图像
        image = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(image)

        # 画一个简单的麦克风形状
        # 主体
        draw.ellipse([20, 10, 44, 34], outline='black', width=2)
        # 支架
        draw.line([32, 34, 32, 44], fill='black', width=2)
        draw.line([24, 44, 40, 44], fill='black', width=2)
        draw.line([32, 44, 32, 54], fill='black', width=2)

        return image

    def _on_show(self):
        """显示窗口"""
        # 如果有保存的 GUI 实例，恢复它
        if self.gui:
            try:
                self.gui.show()
            except:
                pass

    def _on_quit(self):
        """退出程序"""
        if self.app:
            self.app.running = False
        if self.tray:
            self.tray.stop()

    def create(self):
        """创建托盘图标"""
        image = self._create_icon()

        menu = pystray.Menu(
            pystray.MenuItem("显示", self._on_show),
            pystray.MenuItem("退出", self._on_quit)
        )

        self.tray = pystray.Icon(
            "voice_input",
            image,
            "Voice Input X (Alt+Shift+D)",
            menu
        )

    def run(self):
        """运行托盘（后台）"""
        if self.tray:
            self.tray.run_detached()

    def stop(self):
        """停止托盘"""
        if self.tray:
            self.tray.stop()

    def set_gui(self, gui):
        """设置 GUI 实例"""
        self.gui = gui
