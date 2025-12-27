#translate.py
# 最小可行懸浮翻譯（示範版）
# 需求套件: PySide6, httpx, openai, langdetect, keyboard, pyperclip
# pip install PySide6 httpx openai langdetect keyboard pyperclip

import os
import sys
import asyncio
from functools import partial

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit
from PySide6.QtCore import Qt, QThread, Signal, Slot
import httpx
import openai
from langdetect import detect
import keyboard  # 全域快捷鍵
import pyperclip

# ---------- 設定 ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # 請將 API Key 設為環境變數 OPENAI_API_KEY
TARGET_LANG = "zh-TW"  # 目標語言（示範：繁體中文）
MODEL = "gpt-4o-mini"  # 範例模型名稱，可依帳號權限更改
# -------------------------

openai.api_key = OPENAI_API_KEY

# ---------- 非同步執行器（在背景執行網路請求） ----------
class AsyncWorker(QThread):
    result_ready = Signal(str)
    error = Signal(str)

    def __init__(self, text: str, target: str):
        super().__init__()
        self.text = text
        self.target = target

    def run(self):
        # 在 QThread 中呼叫 asyncio 事件迴圈
        try:
            res = asyncio.run(self._translate_async(self.text, self.target))
            self.result_ready.emit(res)
        except Exception as e:
            self.error.emit(str(e))

    async def _translate_async(self, text: str, target: str) -> str:
        # 使用 OpenAI 的 chat completions via httpx (可改為 openai.ChatCompletion)
        # 這裡以 httpx 呼叫 REST API 範例（較通用）
        if not OPENAI_API_KEY:
            raise RuntimeError("OpenAI API Key 未設定。請設定環境變數 OPENAI_API_KEY。")

        system_prompt = "You are a helpful translation assistant. Keep formatting and code blocks. Prefer Traditional Chinese when target is zh-TW."
        user_prompt = f"Translate the following text into {target}. Preserve code blocks and formatting.\n\n---\n{text}\n---"

        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 1500
            }
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
            r = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            j = r.json()
            content = j["choices"][0]["message"]["content"].strip()
            return content

# ---------- GUI ----------
class FloatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("懸浮翻譯（MVP）")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(520)

        layout = QVBoxLayout()
        self.text_in = QTextEdit()
        self.text_in.setPlaceholderText("原文（可由剪貼簿貼上或按快捷鍵擷取）")
        self.text_out = QTextEdit()
        self.text_out.setReadOnly(True)
        self.translate_btn = QPushButton("翻譯")
        self.copy_btn = QPushButton("複製譯文")

        layout.addWidget(QLabel("原文："))
        layout.addWidget(self.text_in)
        layout.addWidget(QLabel("譯文（目標語言: 繁體中文）"))
        layout.addWidget(self.text_out)
        layout.addWidget(self.translate_btn)
        layout.addWidget(self.copy_btn)

        self.setLayout(layout)

        # 事件
        self.translate_btn.clicked.connect(self.on_translate)
        self.copy_btn.clicked.connect(self.on_copy)

        # 可拖曳視窗
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def set_input_text(self, txt: str):
        self.text_in.setPlainText(txt)

    @Slot()
    def on_translate(self):
        src = self.text_in.toPlainText().strip()
        if not src:
            self.text_out.setPlainText("沒有輸入文字。")
            return

        # 顯示狀態
        self.text_out.setPlainText("翻譯中 ...")
        self.translate_btn.setEnabled(False)

        # 啟動背景執行緒
        self.worker = AsyncWorker(src, TARGET_LANG)
        self.worker.result_ready.connect(self.on_result)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    @Slot(str)
    def on_result(self, res: str):
        self.text_out.setPlainText(res)
        self.translate_btn.setEnabled(True)

    @Slot(str)
    def on_error(self, err: str):
        self.text_out.setPlainText("發生錯誤：" + err)
        self.translate_btn.setEnabled(True)

    @Slot()
    def on_copy(self):
        txt = self.text_out.toPlainText().strip()
        if txt:
            pyperclip.copy(txt)

# ---------- 全域快速鍵處理 ----------
def on_global_hotkey(win: FloatWindow):
    # 從剪貼簿讀取文字（假設使用者已將選取文字複製）
    text = pyperclip.paste()
    if not text:
        win.text_out.setPlainText("剪貼簿無文字，請先選取並複製文字。")
        win.show()
        win.raise_()
        return

    # 自動偵測語言（示意）
    try:
        lang = detect(text)
    except Exception:
        lang = "unknown"

    # 將原文放入 GUI 並啟動翻譯
    win.set_input_text(text)
    win.show()
    win.raise_()
    win.on_translate()

# ---------- 主程式 ----------
def main():
    app = QApplication(sys.argv)
    win = FloatWindow()
    win.move(100, 100)  # 初始位置

    # 註冊全域快速鍵 (Ctrl+Shift+T)
    try:
        keyboard.add_hotkey("ctrl+shift+t", lambda: on_global_hotkey(win))
    except Exception as e:
        print("無法註冊全域快速鍵：", e)
        print("請確認已安裝 keyboard 且在該平台允許全域鍵盤攔截。")

    win.show()
    # 建議在背景顯示時仍保持事件迴圈
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
