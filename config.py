# config 負責載入環境變數與定義常數，其他檔案都從這裡讀取設定。
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TARGET_LANG = "Traditional Chinese (繁體中文)"
# 記得改成你實際可用的模型名稱
MODEL_NAME = "gemini-2.0-flash" 
