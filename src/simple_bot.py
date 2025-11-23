"""簡化版 Telegram Bot - 訂閱行情並推送到 Telegram"""

import asyncio
import json
import websockets
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# =========================
# 配置區（從 .env 或直接設定）
# =========================

# Telegram 配置
TELEGRAM_BOT_TOKEN = "8118795450:AAHrBa9U_INfFiSu9F9YEnQxSrsLH0OsXfg"
TELEGRAM_CHAT_ID = "7036959349"

# API WebSocket 配置
API_WS_URL = "ws://localhost:8000/ws"

# 要訂閱的股票
SUBSCRIBED_STOCKS = {'2330', '2317', '2454'}

# =========================
# 全局變數
# =========================

bot_app = None
websocket_connection = None

# =========================
# Telegram 指令處理
# =========================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理 /start 指令"""
    await update.message.reply_text(
        "行情推送 Bot 已啟動!\n"
        f"訂閱股票: {', '.join(SUBSCRIBED_STOCKS)}\n\n"
        "指令:\n"
        "/start - 顯示此訊息\n"
        "/status - 查看狀態"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理 /status 指令"""
    ws_status = "已連接" if websocket_connection else "未連接"
    await update.message.reply_text(
        f"WebSocket: {ws_status}\n"
        f"訂閱股票: {', '.join(SUBSCRIBED_STOCKS)}"
    )

# =========================
# WebSocket 處理
# =========================

async def send_telegram_message(text: str):
    """發送 Telegram 訊息"""
    if bot_app:
        try:
            await bot_app.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=text
            )
        except Exception as e:
            print(f"Send message error: {e}")

async def handle_quote_message(data: dict):
    """處理行情訊息並推送到 Telegram"""
    msg_type = data.get("type")

    if msg_type == "trade":
        # 成交訊息
        stock_id = data.get("stock_id")
        price = data.get("price")
        volume = data.get("volume")
        tick_type = data.get("tick_type")

        tick_label = "買盤" if tick_type == "1" else "賣盤" if tick_type == "2" else "未知"

        message = f"[{stock_id}] 成交\n價格: ${price:.2f}\n量: {volume}\n類型: {tick_label}"
        await send_telegram_message(message)

    elif msg_type == "depth":
        # 五檔訊息（可選擇不推送或只推送特定條件）
        pass

async def websocket_listener():
    """監聽 WebSocket 行情"""
    global websocket_connection

    while True:
        try:
            print(f"Connecting to {API_WS_URL}...")
            async with websockets.connect(API_WS_URL) as ws:
                websocket_connection = ws
                print("WebSocket connected!")

                await send_telegram_message("行情 Bot 已連線！")

                async for message in ws:
                    try:
                        data = json.loads(message)
                        await handle_quote_message(data)
                    except Exception as e:
                        print(f"Message error: {e}")

        except Exception as e:
            print(f"WebSocket error: {e}")
            websocket_connection = None
            await asyncio.sleep(5)  # 重連延遲

# =========================
# 主程式
# =========================

async def main():
    """主程式"""
    global bot_app

    print("="*50)
    print("Simple Telegram Quote Bot")
    print("="*50)
    print(f"Subscribed stocks: {', '.join(SUBSCRIBED_STOCKS)}")
    print(f"API WebSocket: {API_WS_URL}")
    print("="*50)

    # 創建 Telegram Bot
    bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # 註冊指令
    bot_app.add_handler(CommandHandler("start", start_command))
    bot_app.add_handler(CommandHandler("status", status_command))

    # 啟動 Bot（非阻塞）
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()

    print("Telegram Bot started!")

    # 啟動 WebSocket 監聽
    await websocket_listener()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped.")
