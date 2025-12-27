#translate.py
# 最小可行懸浮翻譯
# 需求套件: PySide6, google-generativeai, python-dotenv, langdetect, keyboard, pyperclip
# pip install PySide6 google-generativeai python-dotenv langdetect keyboard pyperclip

import os
import sys
from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit
from PySide6.QtCore import Qt, QThread, Signal, Slot, QMetaObject, Q_ARG
from google import genai 
from langdetect import detect
import keyboard
import pyperclip
from functools import partial

# ---------- 設定 ----------
load_dotenv() # 載入 .env 檔案中的環境變數
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # 讀取 Google API Key
TARGET_LANG = "Traditional Chinese (繁體中文)"
MODEL_NAME = "gemini-2.5-flash"
# ---------- 背景工作執行緒 ----------
class TranslateWorker(QThread):
    # 定義訊號：一個傳送成功結果，一個傳送錯誤訊息
    result_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, api_key, text, target_lang):
        super().__init__()
        self.api_key = api_key
        self.text = text
        self.target_lang = target_lang

    def run(self):
        """
        這裡面的程式碼會在背景執行緒跑，絕對不能碰 UI 元件！
        只負責運算，算完用 Signal 發出去。
        """
        if not self.api_key:
            self.error_occurred.emit("錯誤：未設定 GOOGLE_API_KEY")
            return

        try:
            # 初始化新版 Client (在 run 裡面做，確保執行緒安全)
            client = genai.Client(api_key=self.api_key)
            
            prompt = (
                f"Translate the following text into {self.target_lang}. "
                f"Output ONLY the translated text without explanations.\n\n"
                f"{self.text}"
            )

            # 發送請求
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )
            
            # 取得文字結果
            if response.text:
                self.result_ready.emit(response.text.strip())
            else:
                self.error_occurred.emit("翻譯失敗：模型未回傳內容")

        except Exception as e:
            # 捕捉所有錯誤並傳回主執行緒
            self.error_occurred.emit(f"連線或API錯誤：{str(e)}")

# ---------- GUI 主視窗 ----------
class FloatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.worker = None #以此屬性追蹤執行緒

    def init_ui(self):
        self.setWindowTitle("懸浮翻譯 (Gemini v2)")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(500)

        # 現代化深色介面樣式
        self.setStyleSheet("""
            QWidget {
                background-color: #2D2D2D;
                color: #E0E0E0;
                border: 1px solid #454545;
                border-radius: 8px;
                font-family: "Microsoft JhengHei UI", sans-serif;
            }
            QTextEdit {
                background-color: #1E1E1E;
                border: none;
                padding: 8px;
                selection-background-color: #007ACC;
            }
            QPushButton {
                background-color: #0E639C;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:pressed {
                background-color: #094770;
            }
            QLabel {
                border: none;
                color: #AAAAAA;
                font-size: 12px;
                margin-top: 4px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15) # 增加內距
        layout.setSpacing(10)

        self.label_in = QLabel("原文")
        self.text_in = QTextEdit()
        self.text_in.setPlaceholderText("複製文字後按 Ctrl+Shift+T...")
        self.text_in.setMaximumHeight(80)

        self.label_out = QLabel("譯文")
        self.text_out = QTextEdit()
        self.text_out.setPlaceholderText("翻譯結果...")
        self.text_out.setReadOnly(True)
        # 讓譯文區塊自適應高度，但設個最小值
        self.text_out.setMinimumHeight(80)

        self.btn_translate = QPushButton("手動翻譯")
        self.btn_copy = QPushButton("複製結果")
        self.btn_close = QPushButton("關閉") # 新增一個關閉按鈕方便離開

        layout.addWidget(self.label_in)
        layout.addWidget(self.text_in)
        layout.addWidget(self.label_out)
        layout.addWidget(self.text_out)
        
        # 按鈕列
        btn_layout = QVBoxLayout() # 為了簡單先垂直，也可以用 QHBoxLayout 水平排列
        btn_layout.addWidget(self.btn_translate)
        btn_layout.addWidget(self.btn_copy)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # 綁定訊號
        self.btn_translate.clicked.connect(self.start_translation)
        self.btn_copy.clicked.connect(self.copy_result)
        self.btn_close.clicked.connect(self.exit_app) # 綁定關閉事件

        # 拖曳視窗邏輯
        self._drag_pos = None

    # --- 視窗拖曳功能 ---
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

    # --- 邏輯功能 ---
    def set_input(self, text):
        self.text_in.setPlainText(text)

    @Slot()
    def start_translation(self):
        src_text = self.text_in.toPlainText().strip()
        if not src_text:
            return

        self.text_out.setPlainText("翻譯中...")
        self.btn_translate.setEnabled(False)

        # 建立並啟動執行緒
        self.worker = TranslateWorker(GOOGLE_API_KEY, src_text, TARGET_LANG)
        # 將執行緒的訊號連接到主視窗的槽函數 (Slot)
        self.worker.result_ready.connect(self.handle_result)
        self.worker.error_occurred.connect(self.handle_error)
        
        # 修改這裡：除了 deleteLater，還要加上我們自己的 cleanup
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.on_worker_finished) # 新增這行

        self.worker.start()

    @Slot()
    def on_worker_finished(self):
        self.worker = None

    @Slot(str)
    def handle_result(self, result):
        self.text_out.setPlainText(result)
        self.btn_translate.setEnabled(True)

    @Slot(str)
    def handle_error(self, error_msg):
        self.text_out.setPlainText(error_msg)
        self.btn_translate.setEnabled(True)

    @Slot()
    def copy_result(self):
        text = self.text_out.toPlainText()
        if text:
            pyperclip.copy(text)
            # 可以做個小動畫或變色提示複製成功，這裡省略
    # [新增] 強制結束程式的方法
    @Slot()
    def exit_app(self):
        print("正在關閉程式...")
        if self.worker is not None: 
            # 為了保險，再加一個 try-except 避免已經刪除但還沒設為 None 的邊緣情況
            try:
                if self.worker.isRunning():
                    self.worker.terminate()
                    self.worker.wait()
            except RuntimeError:
                pass # 忽略已經刪除的錯誤
        
        # 2. 移除鍵盤熱鍵監聽 (雖然不是必須，但好習慣)
        try:
            keyboard.unhook_all()
        except:
            pass
            
        # 3. 強制退出 QApplication
        QApplication.instance().quit()

    # [覆寫] 視窗關閉事件 (例如按 Alt+F4 或系統關閉鈕)
    def closeEvent(self, event):
        self.exit_app()
        event.accept()

# ---------- 全域快速鍵處理 ----------
def on_hotkey_triggered(window_ref):
    """
    這是 keyboard 的 callback，它會在一個獨立的 thread 執行。
    所以這裡不能直接操作 UI，必須透過 Signal 或 QMetaObject.invokeMethod。
    但在 PyQt/PySide 簡單應用中，直接呼叫 show/activate 偶爾可行，
    最安全的做法是用 Signal。這裡為了 MVP 簡化，直接呼叫但需小心。
    """
    text = pyperclip.paste()
    if not text:
        return

    # 這裡其實有點危險，因為是在非 GUI thread 呼叫 GUI method。
    # 嚴謹的做法應該是發送一個 Signal 給 Window。
    # 但為了修復你原本的錯誤，我們讓它盡量簡單。
    
    # 解決方案：使用 QMetaObject.invokeMethod 確保在主執行緒執行
    
    # 設定文字並顯示視窗
    QMetaObject.invokeMethod(window_ref.text_in, "setPlainText", Qt.QueuedConnection, Q_ARG(str, text))
    QMetaObject.invokeMethod(window_ref, "showNormal", Qt.QueuedConnection)
    QMetaObject.invokeMethod(window_ref, "activateWindow", Qt.QueuedConnection)
    QMetaObject.invokeMethod(window_ref, "start_translation", Qt.QueuedConnection)


def main():
    app = QApplication(sys.argv)
    window = FloatWindow()
    window.move(100, 100)
    window.show()

    # 註冊熱鍵
    try:
        # 使用 partial 傳遞 window 物件
        callback = partial(on_hotkey_triggered, window)
        keyboard.add_hotkey("ctrl+shift+t", callback)
        print("服務已啟動。請選取文字複製後，按下 Ctrl+Shift+T")
    except Exception as e:
        print(f"熱鍵註冊失敗: {e}")

    sys.exit(app.exec())

if __name__ == "__main__":
    main()