import sys
import mss
import numpy as np
import cv2
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QTimer

class CalibrationWindow(QWidget):
    def __init__(self):
        super().__init__()
        # 設定一個全螢幕半透明視窗
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.showFullScreen()
        
        # 我們要在螢幕中心 (或指定位置) 畫一個紅色的矩形
        # 為了避免邊緣問題，我們選在 (200, 200) 這個絕對位置
        self.target_x = 200
        self.target_y = 200
        self.target_w = 50
        self.target_h = 50
        
        # 設定樣式：在 (200,200) 畫一個紅框
        # 注意：這裡是相對視窗的，因為我們是全螢幕，所以相對視窗=相對螢幕
        self.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
            }}
            QWidget#redbox {{
                background-color: #FF0000;
            }}
        """)
        
        self.red_box = QWidget(self)
        self.red_box.setObjectName("redbox")
        self.red_box.setGeometry(self.target_x, self.target_y, self.target_w, self.target_h)
        self.red_box.show()

        # 延遲 1 秒後開始截圖分析 (確保視窗已顯示)
        QTimer.singleShot(1000, self.analyze)

    def analyze(self):
        print("正在進行截圖分析...")
        
        # 1. 使用 mss 全螢幕截圖
        with mss.mss() as sct:
            # 抓取所有螢幕 (或主螢幕)
            # monitor 1 通常是主螢幕，如果多螢幕可能要改 monitor 0 (all) 或 2
            monitor = sct.monitors[1] 
            sct_img = sct.grab(monitor)
            img = np.array(sct_img)
            
            # 轉 RGB
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # 2. 在截圖中尋找紅色區塊
            # 定義紅色的範圍 (BGR 格式: Blue=0, Green=0, Red=255)
            # 稍微給一點容忍度
            lower_red = np.array([0, 0, 200])
            upper_red = np.array([50, 50, 255])
            
            mask = cv2.inRange(img, lower_red, upper_red)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # 找到最大的紅色區塊
                c = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(c)
                
                print("-" * 30)
                print(f"Qt 設定座標 (邏輯): x={self.target_x}, y={self.target_y}, w={self.target_w}, h={self.target_h}")
                print(f"MSS 截圖座標 (實體): x={x}, y={y}, w={w}, h={h}")
                print("-" * 30)
                
                # 3. 計算縮放比例與偏移
                scale_x = x / self.target_x
                scale_y = y / self.target_y
                scale_w = w / self.target_w
                scale_h = h / self.target_h
                
                print(f"推測縮放比例 (Scale Factor):")
                print(f"  X 軸: {scale_x:.2f}")
                print(f"  Y 軸: {scale_y:.2f}")
                print(f"  W (寬度): {scale_w:.2f}")
                print(f"  H (高度): {scale_h:.2f}")
                
                avg_scale = (scale_x + scale_y + scale_w + scale_h) / 4
                print(f"\n★ 建議 SCALE_FACTOR 設定為: {avg_scale:.2f}")
                
                if abs(avg_scale - 1.0) < 0.05:
                    # 如果比例接近 1，計算是否為純偏移
                    offset_x = x - self.target_x
                    offset_y = y - self.target_y
                    print(f"\n(如果不是縮放問題) 建議 OFFSET 設定為: X={offset_x}, Y={offset_y}")
                
            else:
                print("錯誤：在截圖中找不到紅色區塊。")
                # 儲存圖片幫忙除錯
                cv2.imwrite("debug_calibration.png", img)
                print("已儲存 debug_calibration.png 供檢查")

        self.close()
        QApplication.instance().quit()

if __name__ == "__main__":
    # 強制開啟 DPI 感知，模擬 main.py 的環境
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except:
        ctypes.windll.user32.SetProcessDPIAware()

    app = QApplication(sys.argv)
    win = CalibrationWindow()
    app.exec()
