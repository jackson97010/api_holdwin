import asyncio
import os
import sys
from dotenv import load_dotenv
from telegram import Bot

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID'))

async def test_bot():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    print("開始測試 Telegram Bot...")
    print("=" * 50)

    try:
        # 測試 1: 取得 Bot 資訊
        print("\n[測試 1] 取得 Bot 資訊")
        me = await bot.get_me()
        print(f"[OK] Bot 名稱: {me.first_name}")
        print(f"[OK] Bot 使用者名稱: @{me.username}")
        print(f"[OK] Bot ID: {me.id}")

        # 測試 2: 發送測試訊息
        print("\n[測試 2] 發送測試訊息")
        print(f"[INFO] Chat ID: {TELEGRAM_CHAT_ID}")

        # 先獲取更新以確認 chat ID
        print("[INFO] 檢查最近的對話...")
        recent_updates = await bot.get_updates(limit=5)
        if recent_updates:
            print(f"[INFO] 找到 {len(recent_updates)} 個最近的更新")
            for update in recent_updates:
                if update.message:
                    print(f"[INFO] Chat ID from update: {update.message.chat.id}")

        message = await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text="自動測試訊息\n\n這是一個自動化測試。\n\n請在 Telegram 中測試以下指令：\n/start\n/help\n/test"
        )
        print(f"[OK] 訊息已發送 (Message ID: {message.message_id})")

        # 測試 3: 發送格式化訊息
        print("\n[測試 3] 發送格式化訊息")
        formatted_message = await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text="<b>測試格式化訊息</b>\n\n<i>斜體文字</i>\n<code>程式碼</code>\n<pre>程式碼區塊</pre>",
            parse_mode='HTML'
        )
        print(f"[OK] 格式化訊息已發送 (Message ID: {formatted_message.message_id})")

        # 測試 4: 檢查 Bot 狀態
        print("\n[測試 4] 檢查 Bot 狀態")
        updates = await bot.get_updates(limit=1)
        print(f"[OK] Bot 可以接收更新訊息")

        print("\n" + "=" * 50)
        print("[成功] 所有測試通過！")
        print("\n請在 Telegram 中手動測試以下指令：")
        print("  - /start  : 啟動 Bot")
        print("  - /help   : 顯示幫助訊息")
        print("  - /test   : 測試訊息回覆")
        print("  - 發送任意文字訊息測試回應功能")
        print("\n[提示] 請確保 Bot 正在運行 (python src/bot.py)")

    except Exception as e:
        print(f"\n[失敗] 測試失敗: {e}")
        return False

    return True

if __name__ == '__main__':
    success = asyncio.run(test_bot())
    exit(0 if success else 1)
