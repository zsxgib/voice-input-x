# GUI 模块

import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import queue


class VoiceGUI:
    """语音输入 GUI 窗口"""

    def __init__(self):
        self.root = None
        self.status_label = None
        self.text_area = None
        self._enter_callback = None
        self._escape_callback = None
        self._text_queue = queue.Queue()  # 用于接收后台线程的文字

    def create_window(self):
        """创建窗口"""
        self.root = tk.Tk()
        self.root.title("语音输入")
        self.root.geometry("400x200")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)

        # 定位在光标附近
        self._position_near_cursor()

        # 状态标签
        self.status_label = tk.Label(
            self.root,
            text="按 Enter 结束录音并注入...",
            font=("Arial", 12),
            fg="blue"
        )
        self.status_label.pack(pady=10)

        # 文本区域
        self.text_area = scrolledtext.ScrolledText(
            self.root,
            width=50,
            height=6,
            font=("Arial", 11)
        )
        self.text_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.text_area.insert("1.0", "请说话，按 Enter 结束录音...")

        # 让 root 获取焦点，而不是 text_area
        self.root.focus_set()

        # 绑定快捷键
        self.root.bind("<Return>", lambda e: self._on_enter())
        self.root.bind("<KP_Enter>", lambda e: self._on_enter())
        self.root.bind("<Escape>", lambda e: self._on_escape())

        self.root.focus_force()

    def _position_near_cursor(self):
        """窗口定位在光标附近"""
        try:
            result = subprocess.run(
                ["xdotool", "getmouselocation"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                x = int(parts[0].split(':')[1]) + 20
                y = int(parts[1].split(':')[1]) + 20

                screen_w = self.root.winfo_screenwidth()
                screen_h = self.root.winfo_screenheight()

                if x + 400 > screen_w:
                    x = screen_w - 420
                if y + 200 > screen_h:
                    y = screen_h - 220

                self.root.geometry(f"400x200+{x}+{y}")
        except:
            pass

    def _on_enter(self):
        """处理 Enter 键"""
        if self._enter_callback:
            self._enter_callback()

    def _on_escape(self):
        """处理 Escape 键"""
        if self._escape_callback:
            self._escape_callback()

    def set_enter_callback(self, callback):
        """设置 Enter 回调"""
        self._enter_callback = callback

    def set_escape_callback(self, callback):
        """设置 Escape 回调"""
        self._escape_callback = callback

    def update_status(self, text: str, color: str = "blue"):
        """更新状态"""
        if self.status_label:
            self.status_label.config(text=text, fg=color)

    def show_text(self, text: str):
        """显示文本（替换全部内容）"""
        if self.text_area:
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", text)

    def append_text(self, text: str):
        """追加文本（用于实时显示）"""
        if self.text_area:
            current = self.text_area.get("1.0", tk.END).strip()
            if current and not current.endswith('\n'):
                self.text_area.insert(tk.END, '\n')
            self.text_area.insert(tk.END, text)
            # 自动滚动到底部
            self.text_area.see(tk.END)

    def show_text_thread_safe(self, text: str):
        """线程安全地显示文本（从后台线程调用）"""
        # 直接放入队列，由主循环处理
        self._text_queue.put(text)

    def _do_show_text(self, text: str):
        """实际执行显示文本"""
        if self.text_area:
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", text)

    def update(self):
        """更新窗口"""
        # 处理队列中的文字（来自后台线程）
        while not self._text_queue.empty():
            try:
                text = self._text_queue.get_nowait()
                self._do_show_text(text)
            except queue.Empty:
                break

        if self.root:
            try:
                self.root.update()
            except:
                return False
        return True

    def destroy(self):
        """销毁窗口"""
        if self.root:
            try:
                self.root.destroy()
            except:
                pass
            self.root = None

    def hide(self):
        """隐藏窗口（最小化到托盘）"""
        if self.root:
            try:
                self.root.withdraw()  # 隐藏窗口但不完全销毁
            except:
                pass

    def show(self):
        """显示窗口"""
        if self.root:
            try:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
            except:
                pass

    def is_active(self) -> bool:
        """检查窗口是否活跃"""
        if self.root is None:
            return False
        try:
            return self.root.winfo_exists()
        except:
            return False
