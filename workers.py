import cv2 
import numpy as np
import mss 
import mss.tools
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QGuiApplication # [新增] 用來查詢螢幕資訊
from PySide6.QtCore import QPoint
from deep_translator import GoogleTranslator 
import pytesseract
import ctypes

# 設定 Tesseract 路徑
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# OCR 引擎初始化
print("OCR 引擎已切換為 Tesseract。")

class OCRTranslateWorker(QThread):
    result_ready = Signal(str, str)
    error_occurred = Signal(str)

    def __init__(self, region, scale_factor=1.0):
        super().__init__()
        self.region = region # Qt 全域邏輯座標 (x, y, w, h)
        self.scale_factor = scale_factor # (這個參數在這個新版本其實用不太到，我們會重新抓)

    def run(self):
        try:
            x, y, w, h = self.region
            
            # 1. 找出綠色視窗中心點 (邏輯座標)
            center_x = x + w / 2
            center_y = y + h / 2
            
            # 2. 找出該點所在的 Qt 螢幕 (QScreen)
            # screenAt 需要整數座標
            target_screen = QGuiApplication.screenAt(QPoint(int(center_x), int(center_y)))
            
            if not target_screen:
                # 如果找不到 (例如視窗在邊界外)，回退到主螢幕
                target_screen = QGuiApplication.primaryScreen()
                print("[WARN] 無法偵測視窗所在螢幕，使用主螢幕。")

            # 3. 獲取 Qt 螢幕的「邏輯」幾何資訊
            qt_geo = target_screen.geometry()
            qt_origin_x = qt_geo.x()
            qt_origin_y = qt_geo.y()
            
            # 獲取該螢幕的縮放比例
            # 注意：在 SetProcessDpiAwareness(2) 下，Qt 的 devicePixelRatio 應該是準確的
            current_scale = target_screen.devicePixelRatio()
            
            print(f"[DEBUG] Target Screen: {target_screen.name()}")
            print(f"[DEBUG] Qt Logical Origin: ({qt_origin_x}, {qt_origin_y})")
            print(f"[DEBUG] Screen Scale: {current_scale}")
            
            # 4. 找出對應的 mss 螢幕 (實體)
            # 我們假設 mss.monitors[1:] 的順序與 QGuiApplication.screens() 一致
            # 這通常是真的，但為了保險，我們用「相對位置」來匹配
            
            screens = QGuiApplication.screens()
            screen_index = 0
            
            # 找出 target_screen 是第幾個螢幕
            if target_screen in screens:
                screen_index = screens.index(target_screen)
            
            # mss 的 monitors[0] 是全虛擬桌面，所以實體螢幕從 index 1 開始
            # 對應關係: screens[0] -> mss.monitors[1]
            mss_monitor_idx = screen_index + 1
            
            final_x, final_y, final_w, final_h = 0, 0, 0, 0

            with mss.mss() as sct:
                if mss_monitor_idx < len(sct.monitors):
                    mss_mon = sct.monitors[mss_monitor_idx]
                    
                    mss_origin_x = mss_mon['left']
                    mss_origin_y = mss_mon['top']
                    
                    print(f"[DEBUG] MSS Physical Origin: ({mss_origin_x}, {mss_origin_y})")
                    
                    # 5. ★★★ 核心公式：座標轉換 ★★★
                    # 實體座標 = 實體原點 + ( (邏輯座標 - 邏輯原點) * 縮放比例 )
                    
                    # 計算視窗相對於該螢幕左上角的偏移 (邏輯)
                    rel_x = x - qt_origin_x
                    rel_y = y - qt_origin_y
                    
                    # 轉換為實體偏移
                    phy_rel_x = rel_x * current_scale
                    phy_rel_y = rel_y * current_scale
                    
                    # 加上實體原點
                    final_x = int(mss_origin_x + phy_rel_x)
                    final_y = int(mss_origin_y + phy_rel_y)
                    
                    # 寬高直接縮放
                    final_w = int(w * current_scale)
                    final_h = int(h * current_scale)
                    
                else:
                    # 如果匹配失敗，回退到舊方法 (主螢幕縮放)
                    print("[ERROR] Monitor index mismatch. Fallback to simple scaling.")
                    final_x = int(x * current_scale)
                    final_y = int(y * current_scale)
                    final_w = int(w * current_scale)
                    final_h = int(h * current_scale)

                print(f"[DEBUG] Final Region: {final_x}, {final_y}, {final_w}, {final_h}")

                monitor = {"top": final_y, "left": final_x, "width": final_w, "height": final_h}
                sct_img = sct.grab(monitor)
                
                img_np = np.array(sct_img)
                gray = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)
                
                # Debug
                mss.tools.to_png(sct_img.rgb, sct_img.size, output="debug_mss_screenshot.png")

            # 2. 圖像預處理
            scaled = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
            _, binary = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 3. OCR
            detected_text = pytesseract.image_to_string(binary, lang='eng', config='--psm 6')
            detected_text = detected_text.strip()
            print(f"[DEBUG] Tesseract Result: {detected_text}")

            if not detected_text:
                self.error_occurred.emit("OCR 未偵測到文字")
                return

            # 4. 翻譯 (DeepTranslator)
            dt = GoogleTranslator(source='auto', target='zh-TW')
            translated = dt.translate(detected_text)
            self.result_ready.emit(detected_text, translated)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(f"處理錯誤：{str(e)}")
