# 簡化版行情 API 專案

參考 `sub_redis_example.py` 的簡潔風格重構。

## 專案結構

```
_03_telegram/
├── src/
│   ├── quote_parser.py      # 行情解析器（原有）
│   ├── quote_subscriber.py  # 行情訂閱器（原有）
│   ├── simple_api.py        # 簡化版 API（新）
│   └── simple_bot.py        # 簡化版 Telegram Bot（新）
├── sub_redis_example.py     # 原始訂閱範例
└── README.md
```

## 核心功能

### 1. quote_parser.py
- 解析成交資料（Trade）
- 解析五檔資料（Depth）
- 自動判斷內外盤

### 2. quote_subscriber.py
- 支援 Redis 訂閱
- 支援檔案讀取
- Callback 機制

### 3. simple_api.py（新）
- FastAPI 實現的簡單 REST API
- WebSocket 實時推送
- 內存緩存最新行情

### 4. simple_bot.py（新）
- Telegram Bot 整合
- 自動推送成交訊息
- 簡單指令支援

## 快速開始

### 安裝依賴

```bash
pip install fastapi uvicorn websockets python-telegram-bot redis
```

### 1. 啟動 API 服務器

編輯 `src/simple_api.py` 配置區：

```python
# 要訂閱的股票代碼
SUBSCRIBED_STOCKS = {'2330', '2317', '2454'}

# 選擇數據源：檔案或 Redis
TEST_FILE = r"C:\Users\tacor\Documents\tick-data\OTCQuote.20251031"
# 或
# REDIS_HOST = '192.168.100.130'
```

啟動服務器：

```bash
cd src
python simple_api.py
```

訪問：
- API 文檔: http://localhost:8000/docs
- 所有成交: http://localhost:8000/trades
- 單一成交: http://localhost:8000/trades/2330
- 五檔資料: http://localhost:8000/depths/2330
- WebSocket: ws://localhost:8000/ws

### 2. 啟動 Telegram Bot（可選）

編輯 `src/simple_bot.py` 配置區：

```python
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"
SUBSCRIBED_STOCKS = {'2330', '2317'}
```

啟動 Bot：

```bash
cd src
python simple_bot.py
```

Bot 會自動連接 API WebSocket 並推送成交訊息到 Telegram。

## API 端點

### REST API

| 端點 | 說明 |
|------|------|
| `GET /` | 服務資訊 |
| `GET /trades` | 所有最新成交 |
| `GET /trades/{stock_id}` | 指定股票最新成交 |
| `GET /depths/{stock_id}` | 指定股票最新五檔 |

### WebSocket

**端點**: `ws://localhost:8000/ws`

**接收訊息格式**:

成交訊息：
```json
{
  "type": "trade",
  "stock_id": "2330",
  "price": 550.0,
  "volume": 100,
  "tick_type": "1",
  "timestamp": "131219825776"
}
```

五檔訊息：
```json
{
  "type": "depth",
  "stock_id": "2330",
  "bid1_price": 549.5,
  "bid1_volume": 50,
  "ask1_price": 550.0,
  "ask1_volume": 30,
  "timestamp": "131219825776"
}
```

## 配置說明

### simple_api.py 配置區

```python
# 要訂閱的股票
SUBSCRIBED_STOCKS = {'2330', '2317', '2454', '2881'}

# Redis 配置（如果使用 Redis）
REDIS_HOST = '192.168.100.130'
REDIS_PORT = 6379

# 測試檔案（如果使用檔案）
TEST_FILE = r"C:\path\to\your\quote\file"

# API 配置
API_HOST = "0.0.0.0"
API_PORT = 8000
```

在 `startup()` 函數中選擇數據源：

```python
# 模式1：從檔案讀取（測試用）
asyncio.create_task(
    quote_subscriber.subscribe_from_file(TEST_FILE, delay_ms=0)
)

# 模式2：從 Redis 訂閱（實時）
# asyncio.create_task(
#     quote_subscriber.subscribe_from_redis(
#         host=REDIS_HOST,
#         port=REDIS_PORT
#     )
# )
```

### simple_bot.py 配置區

```python
# Telegram 配置
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"

# API WebSocket
API_WS_URL = "ws://localhost:8000/ws"

# 訂閱股票
SUBSCRIBED_STOCKS = {'2330', '2317', '2454'}
```

## 使用範例

### Python 客戶端

```python
import requests
import json
import websockets
import asyncio

# REST API 查詢
response = requests.get("http://localhost:8000/trades/2330")
print(response.json())

# WebSocket 訂閱
async def subscribe():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        async for message in ws:
            data = json.loads(message)
            print(data)

asyncio.run(subscribe())
```

### curl 測試

```bash
# 查詢所有成交
curl http://localhost:8000/trades

# 查詢單一股票
curl http://localhost:8000/trades/2330

# 查詢五檔
curl http://localhost:8000/depths/2330
```

## 與原始範例對比

### sub_redis_example.py
- 單純訂閱 Redis
- 直接 print 輸出
- 適合測試和學習

### simple_api.py + simple_bot.py
- 提供 REST API 和 WebSocket
- 可整合到其他系統
- 支援 Telegram 推送
- 保持簡潔風格（單檔案、清晰配置）

## 特點

✅ **簡單直接** - 參考 sub_redis_example.py 的風格
✅ **配置清晰** - 所有配置集中在檔案開頭
✅ **單檔案實現** - 每個功能一個檔案
✅ **零依賴原有代碼** - 完美整合 quote_parser 和 quote_subscriber
✅ **雙模式支援** - Redis 或檔案
✅ **WebSocket 推送** - 實時行情
✅ **Telegram 整合** - 自動推送訊息

## 下一步

1. 修改 `simple_api.py` 中的 `SUBSCRIBED_STOCKS`
2. 選擇數據源（檔案或 Redis）
3. 啟動 API: `python simple_api.py`
4. （可選）配置並啟動 Bot: `python simple_bot.py`
5. 訪問 http://localhost:8000/docs 查看 API 文檔

簡單、直接、有效！
