# overlay  (選取框)
from PySide6.QtWidgets import QWidget, QSizeGrip, QVBoxLayout
from PySide6.QtCore import Qt

class SelectionWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("翻譯區域")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        
        # 改成：不使用像素級透明，改用視窗級透明 (比較穩定)
        self.setWindowOpacity(0.3) # 整體 30% 透明
        self.setStyleSheet("background-color: green; border: 2px solid green;")
        self.setGeometry(100, 100, 400, 150)

        # [新增] 設定最小縮放範圍 (防止視窗過小導致截圖錯誤)
        self.setMinimumSize(100, 60) 
        
        # [新增] 右下角調整大小手柄
        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("background-color: transparent; width: 20px; height: 20px;")
        self.sizegrip.raise_() # 確保在最上層

        self._drag_pos = None

    # [新增] 保持 SizeGrip 在右下角
    def resizeEvent(self, event):
        rect = self.geometry()
        sz = self.sizegrip.sizeHint()
        self.sizegrip.move(rect.width() - sz.width(), rect.height() - sz.height())
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # [新增] 避免誤觸 SizeGrip
            if self.sizegrip.geometry().contains(event.position().toPoint()):
                event.ignore()
                return
            
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
    
    def get_region(self):
        geo = self.geometry()
        return (geo.x(), geo.y(), geo.width(), geo.height())
