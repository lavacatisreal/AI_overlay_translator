# gui/result_window.py 懸浮視窗

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                               QTextEdit, QHBoxLayout, QApplication, QSizeGrip)
from PySide6.QtCore import Qt, Slot
from .overlay import SelectionWindow
from workers import OCRTranslateWorker
import keyboard # 記得 import 這個，如果 exit_app 有用到

class ResultWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.selection_win = SelectionWindow() 
        self.worker = None
        self.init_ui()
        self.selection_win.show()
        self.show()

    def init_ui(self):
        
        self.setWindowTitle("翻譯結果")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        
        self.setWindowOpacity(0.9)

        self.setFixedWidth(400)
        self.setMinimumSize(300, 200) # [新增] 設定最小尺寸
        self.setStyleSheet("""
            QWidget { background-color: #2D2D2D; color: #E0E0E0; border: 1px solid #454545; border-radius: 8px; font-family: "Microsoft JhengHei UI", sans-serif; }
            QTextEdit { background-color: #1E1E1E; border: none; padding: 5px; font-size: 14px; }
            QPushButton { background-color: #0E639C; color: white; border: none; padding: 5px; border-radius: 4px; }
            QPushButton:hover { background-color: #1177BB; }
            QLabel { border: none; color: #AAAAAA; font-size: 12px; }
        """)
        
        layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        self.lbl_status = QLabel("按 F9 翻譯選取區")
        self.btn_close = QPushButton("X")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.clicked.connect(self.exit_app) # 連接到 exit_app
        top_layout.addWidget(self.lbl_status)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_close)
        
        self.text_src = QTextEdit()
        self.text_src.setPlaceholderText("OCR 辨識原文...")
        self.text_src.setMaximumHeight(60)
        self.text_src.setReadOnly(True)
        
        self.text_trans = QTextEdit()
        self.text_trans.setPlaceholderText("翻譯結果...")
        # self.text_trans.setMinimumHeight(80)
        self.text_trans.setReadOnly(True)

        layout.addLayout(top_layout)
        layout.addWidget(QLabel("原文 (OCR):"))
        layout.addWidget(self.text_src)
        layout.addWidget(QLabel("譯文:"))
        layout.addWidget(self.text_trans)
        self.setLayout(layout)
        
        # [新增] 右下角調整大小的手柄
        self.sizegrip = QSizeGrip(self)
        # 讓手柄在最上層
        self.sizegrip.raise_()

        self._drag_pos = None

    # [新增] 當視窗大小改變時，隨時移動 SizeGrip 到右下角
    def resizeEvent(self, event):
        rect = self.geometry()
        # QSizeGrip 預設就會貼在右下角，但如果要自訂位置可以寫在這裡
        # 通常 QSizeGrip 放在 Layout 裡會怪怪的，所以我們手動給它位置
        sz = self.sizegrip.sizeHint()
        self.sizegrip.move(rect.width() - sz.width(), rect.height() - sz.height())
        super().resizeEvent(event)

    # --- 滑鼠拖曳邏輯 ---
    def mousePressEvent(self, event):
        # [修正] 避免在點擊 SizeGrip 時也觸發視窗拖曳
        # 檢查點擊位置是否在右下角區域
        if self.sizegrip.geometry().contains(event.position().toPoint()):
            event.ignore() # 交給 SizeGrip 處理
            return
        
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
            return
        self.lbl_status.setText("辨識中...")
        region = self.selection_win.get_region()
        self.worker = OCRTranslateWorker(region)
        
        # [新增] 獲取綠色視窗所在的螢幕縮放比例
        # windowHandle() 可能為 None，如果視窗還沒完全顯示
        win_handle = self.selection_win.windowHandle()
        if win_handle:
            screen = win_handle.screen()
            scale = screen.devicePixelRatio() # 獲取 DPI 縮放 (例如 1.25 或 1.5)
        else:
            # fallback: 用應用程式主螢幕的縮放
            scale = QApplication.primaryScreen().devicePixelRatio()

        print(f"[DEBUG] Detected Window Scale Factor: {scale}")

        # [修改] 傳入 scale
        self.worker = OCRTranslateWorker(region, scale_factor=scale)

        self.worker.result_ready.connect(self.handle_result)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    # [補上缺失的方法]
    @Slot(str, str)
    def handle_result(self, src, trans):
        self.text_src.setPlainText(src)
        self.text_trans.setPlainText(trans)
        self.lbl_status.setText("翻譯完成")

    @Slot(str)
    def handle_error(self, err):
        self.lbl_status.setText("錯誤")
        self.text_trans.setPlainText(err)
        
    @Slot()
    def on_worker_finished(self):
        self.worker = None

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
