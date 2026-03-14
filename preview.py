# 预览窗口模块

import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading


class PreviewWindow:
    def __init__(self, title="语音输入", auto_start_recording=False):
        self.result = None
        self.confirmed = False
        self.recording = False
        self.recognizing = False
        self.auto_start = auto_start_recording
        self.inject_done = False  # 注入是否已完成
        self.window = tk.Tk()
        self.window.title(title)
        self.window.geometry("400x200")
        self.window.attributes("-topmost", True)  # 置顶
        self.window.attributes("-alpha", 0.95)  # 半透明

        # 回调函数（由主程序设置）
        self.on_start_recording = None
        self.on_stop_recording = None
        self.recognizer = None

        # 获取鼠标位置并定位窗口
        self._position_near_cursor()

        self._build_ui()

    def _position_near_cursor(self):
        """窗口定位在光标附近"""
        try:
            # 获取鼠标位置
            result = subprocess.run(
                ["xdotool", "getmouselocation"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                # 解析 x:xxx y:xxx
                parts = result.stdout.strip().split()
                x = int(parts[0].split(':')[1])
                y = int(parts[1].split(':')[1])

                # 偏移一点，避免挡住光标
                x += 20
                y += 20

                # 确保窗口在屏幕内
                screen_w = self.window.winfo_screenwidth()
                screen_h = self.window.winfo_screenheight()

                if x + 400 > screen_w:
                    x = screen_w - 420
                if y + 200 > screen_h:
                    y = screen_h - 220

                self.window.geometry(f"400x200+{x}+{y}")
        except:
            # 失败则居中
            self.window.update_idletasks()
            x = (self.window.winfo_screenwidth() - 400) // 2
            y = (self.window.winfo_screenheight() - 200) // 2
            self.window.geometry(f"400x200+{x}+{y}")

    def _build_ui(self):
        # 状态标签
        self.status_label = tk.Label(
            self.window,
            text="按 Enter 结束录音并注入...",
            font=("Arial", 12),
            fg="blue"
        )
        self.status_label.pack(pady=10)

        # 文本区域
        self.text_area = scrolledtext.ScrolledText(
            self.window,
            width=50,
            height=6,
            font=("Arial", 11)
        )
        self.text_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.text_area.insert("1.0", "请说话，按 Enter 结束录音...")

        # 绑定快捷键
        self.window.bind("<Return>", self._on_enter)
        self.window.bind("<Escape>", lambda e: self.cancel())

        # 获取焦点
        self.window.focus_force()

        # 如果是自动开始模式，立即开始录音
        if self.auto_start:
            self.window.after(100, self._start_recording)

    def _start_recording(self):
        """开始录音"""
        self.recording = True
        self.status_label.config(text="录音中... 请说话", fg="red")
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", "录音中...")

        if self.on_start_recording:
            self.on_start_recording()

    def _on_enter(self, event):
        """处理 Enter 键 - 停止录音并注入"""
        # 防止重复触发
        if self.inject_done:
            return

        if self.recording:
            # 停止录音并识别
            self.recording = False
            self.status_label.config(text="识别中...", fg="orange")

            # 调用停止录音回调，获取音频路径
            audio_path = None
            if self.on_stop_recording:
                audio_path = self.on_stop_recording()

            # 在后台线程进行识别
            if audio_path:
                threading.Thread(target=self._recognize_and_inject, args=(audio_path,), daemon=True).start()
            else:
                self.status_label.config(text="录音失败", fg="red")
        elif self.recognizing:
            # 识别中按 Enter 无效
            return

    def _recognize_and_inject(self, audio_path):
        """识别并注入（在线程中运行）"""
        try:
            text = self.recognizer.recognize(audio_path)

            # 更新 UI（需要在主线程）
            self.window.after(0, self._on_recognized, text)
        except Exception as e:
            self.window.after(0, self._show_error, str(e))

    def _on_recognized(self, text):
        """识别完成，注入文字"""
        self.recognizing = False

        if not text:
            self.status_label.config(text="未识别到文字，请重试", fg="red")
            return

        # 显示识别结果
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", text)

        # 获取文字并注入
        self.result = text
        self.confirmed = True
        self.inject_done = True

        # 注入文字
        from injector import inject_text
        inject_text(text)

        self.status_label.config(text="已注入！", fg="green")

        # 延迟关闭，让用户看到结果
        self.window.after(500, self.window.destroy)

    def _show_error(self, error_msg):
        """显示错误"""
        self.recognizing = False
        self.status_label.config(text=f"识别失败: {error_msg}", fg="red")

    def show(self):
        """显示窗口"""
        self.window.focus_force()
        self.window.mainloop()
        return self.confirmed, self.result

    def confirm(self):
        """确认"""
        self.result = self.text_area.get("1.0", tk.END).strip()
        self.confirmed = True
        self.window.destroy()

    def cancel(self):
        """取消"""
        self.confirmed = False
        self.result = None
        self.window.destroy()

    def close(self):
        """关闭窗口"""
        self.window.destroy()


def show_preview(text=""):
    """显示预览窗口，返回 (confirmed, result)"""
    window = PreviewWindow()
    if text:
        window.show_text(text)
    return window.show()
