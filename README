# 🌟 AI Overlay Translator (AI 懸浮翻譯助手)

這是一個基於 Python 與 PySide6 開發的智慧懸浮翻譯工具。它能透過**螢幕截圖**與**AI 模型 (Google Gemini)** 結合，即時將螢幕上選定範圍內的文字翻譯成繁體中文。

本專案解決了傳統螢幕截圖的座標偏移問題，並提供直覺的懸浮視窗介面，讓你在閱讀原文文件、遊玩英文遊戲或瀏覽網頁時，能獲得無縫的翻譯體驗。

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-orange)

## ✨ 主要功能 (Features)

*   **🎯 精準框選翻譯**：提供半透明綠色懸浮視窗，可自由拖曳與縮放，精確覆蓋欲翻譯的區域。
*   **🤖 強大 AI 核心**：串接 **Google Gemini 1.5 Flash** 模型，翻譯品質遠勝傳統機器翻譯，更能理解語境與專業術語。
*   **📐 智慧座標修正**：內建座標偏移補償演算法，解決在高 DPI 螢幕（如 Windows 縮放 125%/150%）下的截圖錯位問題。
*   **🛡️ 防呆機制**：視窗具備最小縮放範圍限制 (100x60 px)，防止因範圍過小導致的辨識錯誤。
*   **⚡ 全域快速鍵**：支援自訂快速鍵 (預設 `Ctrl+Shift+T`)，一鍵觸發截圖與翻譯。

## 🛠️ 安裝指南 (Installation)

### 1. 環境準備
請確保您的電腦已安裝 [Python 3.10](https://www.python.org/) 或以上版本。

### 2. 下載專案
```
git clone https://github.com/YourUsername/ai-overlay-translator.git
cd ai-overlay-translator
```

### 3. 安裝依賴套件
建議使用虛擬環境 (venv) 進行安裝：
```
# 建立虛擬環境
python -m venv .venv

# 啟用虛擬環境 (Windows)
.venv\Scripts\activate

# 安裝套件
pip install -r requirements.txt
```

> **Requirements 內容範例：**
> `PySide6`, `google-genai`, `python-dotenv`, `keyboard`, `pyperclip`, `Pillow`

## ⚙️ 設定 (Configuration)

本專案使用 Google Gemini API，請先前往 [Google AI Studio](https://aistudio.google.com/) 申請免費的 API Key。

1. 在專案根目錄建立一個名為 `.env` 的檔案。
2. 在檔案中填入您的 API 金鑰：

```
GOOGLE_API_KEY=你的_API_KEY_貼在這裡
```

## 🚀 使用方法 (Usage)

1. **啟動程式**：
   ```
   python main.py
   ```
   *(請將 `main.py` 替換為您的主程式檔名)*

2. **選取範圍**：
   螢幕上會出現一個半透明的綠色視窗。將其拖曳並縮放，覆蓋住您想要翻譯的文字區域。

3. **觸發翻譯**：
   按下預設快速鍵 **`Ctrl + Shift + T`**（或您設定的按鍵）。
   *   程式會自動隱藏選取框 -> 截圖 -> 恢復選取框。
   *   翻譯結果將顯示於結果視窗中。

## 📂 專案結構 (Project Structure)

```
ai-overlay-translator/
├── .env                # 環境變數 (存放 API Key，請勿上傳)
├── .gitignore          # Git 忽略清單
├── main.py             # 主程式入口 (GUI 與 邏輯核心)
├── requirements.txt    # 依賴套件清單
└── README.md           # 專案說明文件
```

## 🤝 貢獻 (Contributing)

歡迎提交 Issue 或 Pull Request！
如果您發現任何 Bug 或有新功能建議，請隨時告訴我。

## 📄 授權 (License)

本專案採用 [MIT License](LICENSE) 授權。
```