import os
from dotenv import load_dotenv
from google import genai

# 1. 載入 .env 檔案
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("錯誤：找不到 GOOGLE_API_KEY，請檢查 .env 檔案。")
    exit()

# 2. 初始化 Client
try:
    client = genai.Client(api_key=api_key)
    
    print("正在查詢可用模型...\n")
    print(f"{'Model Name':<40} {'Display Name'}")
    print("-" * 60)

    # 3. 列出模型
    # 使用 client.models.list() 取得所有模型
    for model in client.models.list():
        # 我們只關心支援 "generateContent" (文字生成) 的模型
        if "generateContent" in model.supported_actions:
             # 有些模型名稱是 "models/gemini-1.5-flash-001"，我們只取後面
            print(f"{model.name:<40} {model.display_name}")

except Exception as e:
    print(f"發生錯誤：{e}")
    print("\n常見原因：API Key 無效、網路問題、或 SDK 版本過舊。")
