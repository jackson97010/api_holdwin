"""簡化版行情 API - 參考 sub_redis_example.py 的簡潔風格"""

import asyncio
from typing import Set, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

from quote_parser import QuoteParser, TradeData, DepthData
from quote_subscriber import QuoteSubscriber

# =========================
# 配置區
# =========================

# 要訂閱的股票代碼
SUBSCRIBED_STOCKS = {'2330', '2317', '2454', '2881'}

# Redis 配置（如果使用 Redis 訂閱）
REDIS_HOST = '192.168.100.130'
REDIS_PORT = 6379

# 或者使用檔案測試
TEST_FILE = r"C:\Users\tacor\Documents\tick-data\OTCQuote.20251031"

# API 配置
API_HOST = "0.0.0.0"
API_PORT = 8000

# =========================
# 全局變數
# =========================

app = FastAPI(title="Simple Quote API")

# 數據存儲：每個股票的最新資料
latest_trades: Dict[str, TradeData] = {}
latest_depths: Dict[str, DepthData] = {}

# WebSocket 連接管理
active_connections: list[WebSocket] = []

# 訂閱器
quote_subscriber: Optional[QuoteSubscriber] = None

# =========================
# 數據處理回調
# =========================

async def handle_trade(trade: TradeData):
    """處理成交資料"""
    latest_trades[trade.stock_id] = trade

    # 廣播給所有 WebSocket 客戶端
    message = {
        "type": "trade",
        "stock_id": trade.stock_id,
        "price": trade.price,
        "volume": trade.volume,
        "tick_type": trade.tick_type,
        "timestamp": trade.timestamp
    }
    await broadcast(message)

async def handle_depth(depth: DepthData):
    """處理五檔資料"""
    latest_depths[depth.stock_id] = depth

    # 只廣播買賣一檔
    message = {
        "type": "depth",
        "stock_id": depth.stock_id,
        "bid1_price": depth.bid1_price,
        "bid1_volume": depth.bid_levels[0].volume if depth.bid_levels else 0,
        "ask1_price": depth.ask1_price,
        "ask1_volume": depth.ask_levels[0].volume if depth.ask_levels else 0,
        "timestamp": depth.timestamp
    }
    await broadcast(message)

async def broadcast(message: dict):
    """廣播訊息給所有連接的客戶端"""
    disconnected = []
    for ws in active_connections:
        try:
            await ws.send_json(message)
        except:
            disconnected.append(ws)

    # 移除斷線的客戶端
    for ws in disconnected:
        active_connections.remove(ws)

# =========================
# API 端點
# =========================

@app.get("/")
async def root():
    """根路徑"""
    return {
        "service": "Simple Quote API",
        "subscribed_stocks": list(SUBSCRIBED_STOCKS),
        "websocket": "/ws",
        "latest_trades": f"/trades (total: {len(latest_trades)})",
        "latest_depths": f"/depths (total: {len(latest_depths)})"
    }

@app.get("/trades")
async def get_all_trades():
    """獲取所有最新成交"""
    return {
        stock_id: {
            "price": trade.price,
            "volume": trade.volume,
            "tick_type": trade.tick_type,
            "timestamp": trade.timestamp
        }
        for stock_id, trade in latest_trades.items()
    }

@app.get("/trades/{stock_id}")
async def get_trade(stock_id: str):
    """獲取指定股票的最新成交"""
    trade = latest_trades.get(stock_id)
    if not trade:
        return {"error": "No data"}

    return {
        "stock_id": trade.stock_id,
        "price": trade.price,
        "volume": trade.volume,
        "tick_type": trade.tick_type,
        "timestamp": trade.timestamp
    }

@app.get("/depths/{stock_id}")
async def get_depth(stock_id: str):
    """獲取指定股票的最新五檔"""
    depth = latest_depths.get(stock_id)
    if not depth:
        return {"error": "No data"}

    return {
        "stock_id": depth.stock_id,
        "bid1_price": depth.bid1_price,
        "bid1_volume": depth.bid_levels[0].volume if depth.bid_levels else 0,
        "ask1_price": depth.ask1_price,
        "ask1_volume": depth.ask_levels[0].volume if depth.ask_levels else 0,
        "timestamp": depth.timestamp
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端點 - 實時推送行情"""
    await websocket.accept()
    active_connections.append(websocket)
    print(f"New WebSocket connection. Total: {len(active_connections)}")

    try:
        while True:
            # 保持連接，接收客戶端訊息（如果有）
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print(f"WebSocket disconnected. Total: {len(active_connections)}")

# =========================
# 啟動/關閉
# =========================

@app.on_event("startup")
async def startup():
    """啟動時初始化訂閱"""
    global quote_subscriber

    print("Starting Quote API...")
    print(f"Subscribed stocks: {', '.join(SUBSCRIBED_STOCKS)}")

    # 創建訂閱器
    quote_subscriber = QuoteSubscriber(stock_ids=SUBSCRIBED_STOCKS)
    quote_subscriber.add_trade_callback(handle_trade)
    quote_subscriber.add_depth_callback(handle_depth)

    # 啟動訂閱（選擇一種模式）
    # # 模式1：從檔案讀取（測試用）
    # asyncio.create_task(
    #     quote_subscriber.subscribe_from_file(TEST_FILE, delay_ms=0)
    # )

    # 模式2：從 Redis 訂閱（實時）
    asyncio.create_task(
        quote_subscriber.subscribe_from_redis(
            host=REDIS_HOST,
            port=REDIS_PORT
        )
    )

    print("Quote API started!")

@app.on_event("shutdown")
async def shutdown():
    """關閉時清理"""
    print("Shutting down Quote API...")
    if quote_subscriber:
        quote_subscriber.stop()

# =========================
# 主程式
# =========================

if __name__ == "__main__":
    print("="*50)
    print("Simple Quote API Server")
    print("="*50)
    print(f"API: http://{API_HOST}:{API_PORT}")
    print(f"Docs: http://localhost:{API_PORT}/docs")
    print(f"WebSocket: ws://localhost:{API_PORT}/ws")
    print("="*50)

    uvicorn.run(app, host=API_HOST, port=API_PORT)
