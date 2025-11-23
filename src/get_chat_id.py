import asyncio
import os
import sys
from dotenv import load_dotenv
from telegram import Bot

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def get_chat_id():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    print("=" * 60)
    print("Chat ID 獲取工具")
    print("=" * 60)

    print("\n[步驟 1] 請在 Telegram 中執行以下操作：")
    print("   1. 搜尋你的 Bot：@exhaustionStock_bot")
    print("   2. 點擊 'START' 或發送 /start")
    print("   3. 發送任意訊息給 Bot（例如：'Hello'）")
    print("\n按 Enter 繼續...")
    input()

    print("\n[步驟 2] 正在獲取更新...")

    try:
        updates = await bot.get_updates(timeout=10)

        if not updates:
            print("\n[警告] 沒有找到任何訊息！")
            print("   請確認你已經：")
            print("   1. 在 Telegram 中找到 Bot")
            print("   2. 發送了訊息給 Bot")
            print("\n[提示] 請重新執行此腳本並發送訊息")
            return

        print(f"\n[成功] 找到 {len(updates)} 個更新")
        print("\n可用的 Chat IDs：")
        print("-" * 60)

        chat_ids = set()
        for update in updates:
            if update.message:
                chat_id = update.message.chat.id
                username = update.message.from_user.username or "N/A"
                first_name = update.message.from_user.first_name or "N/A"
                message_text = update.message.text[:30] if update.message.text else "N/A"

                chat_ids.add(chat_id)

                print(f"\nChat ID: {chat_id}")
                print(f"使用者名稱: @{username}")
                print(f"名稱: {first_name}")
                print(f"訊息: {message_text}")
                print("-" * 60)

        if chat_ids:
            print(f"\n[結果] 找到 {len(chat_ids)} 個獨特的 Chat ID")
            print("\n請將以下內容更新到 .env 檔案：")
            print("=" * 60)
            for chat_id in chat_ids:
                print(f"TELEGRAM_CHAT_ID={chat_id}")
            print("=" * 60)

            # 測試發送訊息
            print("\n[測試] 嘗試發送測試訊息...")
            for chat_id in chat_ids:
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text="測試成功！Bot 可以正常發送訊息。\n\n請檢查你的 .env 檔案是否已更新 TELEGRAM_CHAT_ID。"
                    )
                    print(f"[成功] 訊息已發送到 Chat ID: {chat_id}")
                except Exception as e:
                    print(f"[失敗] 無法發送到 Chat ID {chat_id}: {e}")

    except Exception as e:
        print(f"\n[錯誤] {e}")
        return

if __name__ == '__main__':
    asyncio.run(get_chat_id())
