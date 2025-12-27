# game_translate.py
# 遊戲懸浮翻譯 (OCR版)
# 需求套件: PySide6, google-genai, python-dotenv, keyboard, pyautogui, paddleocr, opencv-python
# pip install PySide6 google-genai python-dotenv keyboard pyautogui paddleocr paddlepaddle opencv-python

import os
import sys
import pyautogui
import numpy as np
from dotenv import load_dotenv
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                               QPushButton, QTextEdit, QFrame, QHBoxLayout)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QColor, QPalette
from google import genai
import keyboard
from paddleocr import PaddleOCR # 引入 PaddleOCR

# ---------- 設定 ----------
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TARGET_LANG = "Traditional Chinese (繁體中文)"
MODEL_NAME = "gemini-2.0-flash" 

# 初始化 OCR 引擎 (只載入一次，避免重複載入卡頓)
# use_angle_cls=True 可以辨識旋轉文字，lang='en' 支援英文，若遊戲有中文可改 'ch'
print("正在載入 OCR 模型，請稍候...")
ocr_engine = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
print("OCR 模型載入完成。")

# ---------- 背景工作執行緒 (OCR + LLM) ----------
class OCRTranslateWorker(QThread):
    result_ready = Signal(str, str) # (原文, 譯文)
    error_occurred = Signal(str)

    def __init__(self, api_key, region):
        super().__init__()
        self.api_key = api_key
        self.region = region # (x, y, w, h)

    def run(self):
        try:
            # 1. 螢幕截圖
            x, y, w, h = self.region
            # pyautogui.screenshot 需處理高解析度螢幕縮放問題，這裡假設 100% 縮放
            screenshot = pyautogui.screenshot(region=(x, y, w, h))
            
            # 2. OCR 辨識
            # PaddleOCR 需要 numpy array 格式的圖片
            img_np = np.array(screenshot)
            # 轉換顏色 BGR (OpenCV格式) -> RGB (雖PaddleOCR沒差，但習慣上轉一下)
            # 其實 pyautogui 截出來是 RGB，PaddleOCR 內部會處理
            
            result = ocr_engine.ocr(img_np, cls=True)
            
            detected_text = ""
            if result and result[0]:
                # result 結構: [[[[x,y],..], (text, conf)], ...]
                # 我們把所有辨識到的文字串接起來
                texts = [line[1][0] for line in result[0]]
                detected_text = " ".join(texts)
            
            if not detected_text.strip():
                self.error_occurred.emit("OCR 未偵測到文字")
                return

            # 3. LLM 翻譯
            if not self.api_key:
                self.error_occurred.emit("錯誤：未設定 GOOGLE_API_KEY")
                return

            client = genai.Client(api_key=self.api_key)
            prompt = (
                f"Translate the following game text into {TARGET_LANG}. "
                f"Output ONLY the translated text without explanations.\n\n"
                f"{detected_text}"
            )

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )
            
            if response.text:
                self.result_ready.emit(detected_text, response.text.strip())
            else:
                self.error_occurred.emit("翻譯失敗：模型未回傳內容")

        except Exception as e:
            self.error_occurred.emit(f"處理錯誤：{str(e)}")

# ---------- 選取框視窗 (Selection Overlay) ----------
class SelectionWindow(QWidget):
    def __init__(self, parent_controller):
        super().__init__()
        self.controller = parent_controller
        self.setWindowTitle("翻譯區域 (拖曳調整)")
        
        # 設定為無邊框、置頂
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        
        # 設定半透明綠色背景
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background-color: rgba(0, 255, 0, 50); border: 2px solid green;")
        
        self.setGeometry(100, 100, 400, 150) # 預設大小
        
        # 拖曳邏輯
        self._drag_pos = None
        self.is_locked = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 記錄點擊位置用於拖曳，或改變大小 (這裡簡化為移動)
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
    
    # 取得當前區域 (x, y, w, h)
    def get_region(self):
        geo = self.geometry()
        # 注意：在高 DPI 螢幕上，Qt 的座標可能與 pyautogui 的實體像素不同步
        # 若發現截圖位置跑掉，需乘上縮放倍率 (scale factor)
        return (geo.x(), geo.y(), geo.width(), geo.height())

# ---------- 主控制視窗 (顯示翻譯結果) ----------
class ResultWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.selection_win = SelectionWindow(self)
        self.worker = None
        self.init_ui()
        
        # 顯示兩個視窗
        self.selection_win.show()
        self.show()

    def init_ui(self):
        self.setWindowTitle("翻譯結果")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(400)

        self.setStyleSheet("""
            QWidget { background-color: #2D2D2D; color: #E0E0E0; border: 1px solid #454545; border-radius: 8px; font-family: "Microsoft JhengHei UI", sans-serif; }
            QTextEdit { background-color: #1E1E1E; border: none; padding: 5px; font-size: 14px; }
            QPushButton { background-color: #0E639C; color: white; border: none; padding: 5px; border-radius: 4px; }
            QPushButton:hover { background-color: #1177BB; }
            QLabel { border: none; color: #AAAAAA; font-size: 12px; }
        """)

        layout = QVBoxLayout()
        
        # 標題列與控制鈕
        top_layout = QHBoxLayout()
        self.lbl_status = QLabel("按 F9 翻譯選取區")
        self.btn_close = QPushButton("X")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.clicked.connect(self.exit_app)
        top_layout.addWidget(self.lbl_status)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_close)
        
        self.text_src = QTextEdit()
        self.text_src.setPlaceholderText("OCR 辨識原文...")
        self.text_src.setMaximumHeight(60)
        self.text_src.setReadOnly(True)
        
        self.text_trans = QTextEdit()
        self.text_trans.setPlaceholderText("翻譯結果...")
        self.text_trans.setMinimumHeight(80)
        self.text_trans.setReadOnly(True)

        layout.addLayout(top_layout)
        layout.addWidget(QLabel("原文 (OCR):"))
        layout.addWidget(self.text_src)
        layout.addWidget(QLabel("譯文:"))
        layout.addWidget(self.text_trans)

        self.setLayout(layout)
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

    @Slot()
    def trigger_translation(self):
        if self.worker and self.worker.isRunning():
            return # 避免重複觸發

        self.lbl_status.setText("OCR 辨識與翻譯中...")
        region = self.selection_win.get_region()
        
        self.worker = OCRTranslateWorker(GOOGLE_API_KEY, region)
        self.worker.result_ready.connect(self.handle_result)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    @Slot()
    def on_worker_finished(self):
        self.worker = None

    @Slot(str, str)
    def handle_result(self, src, trans):
        self.text_src.setPlainText(src)
        self.text_trans.setPlainText(trans)
        self.lbl_status.setText("翻譯完成 (F9 再次翻譯)")

    @Slot(str)
    def handle_error(self, err):
        self.lbl_status.setText("錯誤")
        self.text_trans.setPlainText(err)

    @Slot()
    def exit_app(self):
        if self.worker:
            self.worker.terminate()
        try:
            keyboard.unhook_all()
        except:
            pass
        self.selection_win.close()
        QApplication.instance().quit()

# ---------- 全域快速鍵監聽 ----------
def hotkey_callback(window_ref):
    # 使用 invokeMethod 確保在主執行緒執行
    from PySide6.QtCore import QMetaObject, Qt
    QMetaObject.invokeMethod(window_ref, "trigger_translation", Qt.QueuedConnection)

def main():
    app = QApplication(sys.argv)
    
    # 建立主視窗
    result_window = ResultWindow()
    result_window.move(800, 100) # 預設位置
    
    # 註冊 F9 為翻譯熱鍵
    try:
        from functools import partial
        cb = partial(hotkey_callback, result_window)
        keyboard.add_hotkey("F9", cb)
        print("服務啟動。請將綠色框框拖到遊戲對話上，按 F9 翻譯。")
    except Exception as e:
        print(f"熱鍵註冊失敗: {e}")

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
