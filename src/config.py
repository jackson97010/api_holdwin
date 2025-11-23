"""配置檔案 - 集中管理訂閱股票和檔案路徑"""

import os
from pathlib import Path
from typing import Optional, Set
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# ============ API 服務設定 ============

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_VERSION = "1.0.0"
API_TITLE = "Stock Quote API"
API_DESCRIPTION = "High-performance real-time stock quote API with WebSocket support"

# CORS 設定
CORS_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
    "*"  # 開發環境允許所有來源，生產環境應限制
]

# ============ 訂閱股票設定 ============

# 要訂閱的股票代碼 (None = 訂閱全部)
SUBSCRIBED_STOCKS: Optional[Set[str]] = {
    '8043',   # 範例
    '6223',   # 範例
    '1785',   # 範例
    # '2330',  # 台積電
    # '2303',  # 聯電
}

# 設為 None 可訂閱全部股票
# SUBSCRIBED_STOCKS = None


# ============ 檔案路徑設定 ============

# 行情檔案路徑 (用於測試)
QUOTE_FILE_PATH = r"C:\Users\tacor\Documents\tick-data\OTCQuote.20251031"


# ============ Redis 設定 ============

REDIS_HOST = os.getenv("REDIS_HOST", "192.168.100.130")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_POOL_SIZE = int(os.getenv("REDIS_POOL_SIZE", "10"))


# ============ Telegram 設定 ============

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


# ============ 推送設定 ============

# 是否推送成交資訊到 Telegram
NOTIFY_TRADES = True

# 是否推送五檔資訊到 Telegram (通常不需要)
NOTIFY_DEPTH = False

# 每 N 筆成交推送一次 (設為 1 表示每筆都推送)
NOTIFY_EVERY_N_TRADES = 1


# ============ 效能設定 ============

# 檔案讀取模式的延遲時間(毫秒)，0 = 全速處理
FILE_DELAY_MS = 0

# WebSocket 心跳間隔(秒)
WEBSOCKET_HEARTBEAT_INTERVAL = 30

# 最大連接數
MAX_WEBSOCKET_CONNECTIONS = int(os.getenv("MAX_WEBSOCKET_CONNECTIONS", "1000"))

# 數據緩存大小 (每個股票保留最近 N 筆數據)
CACHE_SIZE_PER_STOCK = int(os.getenv("CACHE_SIZE_PER_STOCK", "100"))


# ============ 日誌設定 ============

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = os.getenv("LOG_FILE", None)  # None = 只輸出到 console
