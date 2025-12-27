# main 負責組合所有模組並啟動應用程式。
import ctypes
try:
    # 告訴 Windows：我自己會處理 DPI，不要幫我縮放
    ctypes.windll.shcore.SetProcessDpiAwareness(2) 
except:
    pass
import sys
import os
# os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QMetaObject, Qt
import keyboard
from functools import partial
from gui.result_window import ResultWindow

def hotkey_callback(window_ref):
    # 跨執行緒呼叫
    QMetaObject.invokeMethod(window_ref, "trigger_translation", Qt.QueuedConnection)

def main():
    app = QApplication(sys.argv)
    
    result_window = ResultWindow()
    result_window.move(800, 100)
    
    try:
        cb = partial(hotkey_callback, result_window)
        keyboard.add_hotkey("F9", cb)
        print("服務啟動。按 F9 翻譯。")
    except Exception as e:
        print(f"熱鍵註冊失敗: {e}")

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
