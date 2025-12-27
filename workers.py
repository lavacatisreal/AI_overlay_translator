import cv2
import numpy as np
import mss
import mss.tools
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtCore import QPoint
from deep_translator import GoogleTranslator
import pytesseract
import config  # 引入設定檔
from google import genai  # 引入 Gemini SDK

# 設定 Tesseract 路徑 (請確認路徑正確)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

print("OCR 引擎已就緒。優先使用 Gemini 翻譯，失敗時回退 Google Translator。")

class OCRTranslateWorker(QThread):
    result_ready = Signal(str, str)
    error_occurred = Signal(str)

    def __init__(self, region, scale_factor=1.0):
        super().__init__()
        self.region = region  # (x, y, w, h)
        self.scale_factor = scale_factor
        
        # 初始化 Gemini Client (如果 Key 存在)
        self.gemini_client = None
        if config.GOOGLE_API_KEY:
            try:
                self.gemini_client = genai.Client(api_key=config.GOOGLE_API_KEY)
            except Exception as e:
                print(f"[WARN] Gemini Client 初始化失敗: {e}")

    def run(self):
        try:
            x, y, w, h = self.region
            
            # --- 1. 螢幕截圖邏輯 (保留原本的 DPI 修正) ---
            center_x = x + w / 2
            center_y = y + h / 2
            target_screen = QGuiApplication.screenAt(QPoint(int(center_x), int(center_y)))
            if not target_screen:
                target_screen = QGuiApplication.primaryScreen()

            qt_geo = target_screen.geometry()
            qt_origin_x = qt_geo.x()
            qt_origin_y = qt_geo.y()
            current_scale = target_screen.devicePixelRatio()

            screens = QGuiApplication.screens()
            screen_index = screens.index(target_screen) if target_screen in screens else 0
            mss_monitor_idx = screen_index + 1

            with mss.mss() as sct:
                if mss_monitor_idx < len(sct.monitors):
                    mss_mon = sct.monitors[mss_monitor_idx]
                    mss_origin_x = mss_mon['left']
                    mss_origin_y = mss_mon['top']
                    
                    rel_x = x - qt_origin_x
                    rel_y = y - qt_origin_y
                    
                    final_x = int(mss_origin_x + (rel_x * current_scale))
                    final_y = int(mss_origin_y + (rel_y * current_scale))
                    final_w = int(w * current_scale)
                    final_h = int(h * current_scale)
                else:
                    final_x = int(x * current_scale)
                    final_y = int(y * current_scale)
                    final_w = int(w * current_scale)
                    final_h = int(h * current_scale)

                monitor = {"top": final_y, "left": final_x, "width": final_w, "height": final_h}
                sct_img = sct.grab(monitor)
                img_np = np.array(sct_img)
                gray = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)

            # --- 2. 圖像預處理 & OCR ---
            scaled = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
            _, binary = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            detected_text = pytesseract.image_to_string(binary, lang='eng+chi_tra', config='--psm 6')
            detected_text = detected_text.strip()
            
            print(f"[DEBUG] OCR Result: {detected_text}")

            if not detected_text:
                self.error_occurred.emit("OCR 未偵測到文字")
                return

            # --- 3. 翻譯邏輯 (Gemini -> Fallback) ---
            translated_text = self._translate_text(detected_text)
            self.result_ready.emit(detected_text, translated_text)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(f"處理錯誤：{str(e)}")

    def _translate_text(self, text):
        """雙層翻譯策略：Gemini -> Google Translator"""
        
        # 嘗試 1: Gemini API
        if self.gemini_client:
            try:
                print("[INFO] 嘗試使用 Gemini 翻譯...")
                prompt = (
                    f"Translate the following text into {config.TARGET_LANG}. "
                    f"Output ONLY the translated text without explanations.\n\n"
                    f"{text}"
                )
                response = self.gemini_client.models.generate_content(
                    model=config.MODEL_NAME,
                    contents=prompt
                )
                if response.text:
                    return f"[Gemini] {response.text.strip()}"
            except Exception as e:
                print(f"[WARN] Gemini 翻譯失敗 ({e})，切換至備用方案。")
        else:
            print("[INFO] 未設定 Gemini API Key，直接使用備用方案。")

        # 嘗試 2: Google Translator (Fallback)
        try:
            print("[INFO] 使用 Google Translator (Deep Translator)...")
            dt = GoogleTranslator(source='auto', target='zh-TW')
            result = dt.translate(text)
            return f"[Google] {result}"
        except Exception as e:
            return f"翻譯完全失敗: {str(e)}"
