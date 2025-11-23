# Telegram Bot 測試專案

## 專案目標

建立一個簡單的 Telegram Bot，測試基本的訊息發送功能。未來會整合 Shioaji API 進行量化交易系統開發。
如果必要可以使用.claude/agents來完成
## 當前階段：基本訊息測試

### 功能
1. Bot 啟動並回應基本指令
2. 接收使用者訊息並回覆
3. 主動推送測試訊息

### 專案結構
```
src/
├── bot.py              # 主程式
├── .env                # 環境變數
├── sub_redis_example.py # 訂閱程式碼
   # Python 套件依賴
```
## 訂閱 `subscriber.py`
參考`sub_redis_example.py`可以知道如何訂閱行情，其中一些進一步的資料結構長這樣，但目前並沒有分辨內外盤的方式，參考 `decoder.py`來實作，我希望你能夠把bot的程式碼進一步優化，我可以在本地端先設定好要訂閱那些 stock_id就可以把這些資料傳出來，另外程式碼要優化，讓他的速度盡量快。
1. 成交格式: Trade,股票代碼,成交時間,試撮旗標,成交價,成交單量,成交總量,序號
   試撮旗標: 0：一般揭示 1：試算揭示 	
   成交價: 4位小數, 333500 實際成交價 -> 33.35
   EX: Trade,2355  ,131219825776,0,333500,1,1530,1234

2. 五檔格式: Depth,股票代碼,報價時間,
			BID:委買檔數,第1檔價格*數量,第2檔價格*數量,第3檔價格*數量,第4檔價格*數量,第5檔價格*數量,
            ASK:委賣檔數,第1檔價格*數量,第2檔價格*數量,第3檔價格*數量,第4檔價格*數量,第5檔價格*數量
			,序號
   EX: Depth,2355  ,131219825776,BID:5,333000*27,332500*5,332000*32,331500*35,331000*62,ASK:5,333500*17,334000*5,334500*13,335000*44,335500*14,1234

## 環境設定

### 1. 建立 `.env` 檔案
```env
TELEGRAM_BOT_TOKEN=8118795450:AAHrBa9U_INfFiSu9F9YEnQxSrsLH0OsXfg
TELEGRAM_CHAT_ID=7036959349
```

### 2. 取得 Telegram Bot Token
1. 在 Telegram 搜尋 `@BotFather`
2. 發送 `/newbot` 建立新 Bot
3. 按照指示設定 Bot 名稱
4. 複製 Token 到 `.env` 檔案

### 3. 取得 Chat ID
1. 啟動 Bot 後，發送任意訊息給 Bot
2. 訪問：`https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. 在回傳的 JSON 中找到 `chat.id`
4. 複製 Chat ID 到 `.env` 檔案


###  Dececode行情
## 安裝套件

```bash
conda activate my_project
pip install python-telegram-bot 
```

## 測試指令

### 基本指令
- `/start` - 啟動 Bot
- `/help` - 顯示幫助訊息
- `/test` - 測試訊息回覆

## 執行 Bot

```bash
conda activate my_project
python bot.py
```

## 下一步

測試成功後，將逐步整合：
1. Shioaji API 連接
2. 即時報價推送
3. 交易訊號通知
4. 策略回測結果

## 參考資源

- Python Telegram Bot 文檔: https://docs.python-telegram-bot.org/
- Shioaji 文檔: https://ai.sinotrade.com.tw/python/Main/index.aspx