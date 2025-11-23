import sys
import subprocess
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("Telegram Bot 自動測試流程")
print("=" * 70)

print("\n[步驟 1] 啟動 Bot")
print("-" * 70)
print("即將啟動 Bot 服務...")
print("\n[重要說明]")
print("1. Bot 啟動後，請在 Telegram 中找到 @exhaustionStock_bot")
print("2. 發送 /start 命令給 Bot")
print("3. Bot 會回覆你的 Chat ID")
print("4. 將 Chat ID 更新到 .env 檔案")
print("5. 按 Ctrl+C 停止 Bot")
print("\n準備啟動 Bot...")
print("=" * 70)

time.sleep(2)

try:
    # 啟動 bot.py
    subprocess.run(["python", "src/bot.py"], check=True)
except KeyboardInterrupt:
    print("\n\n" + "=" * 70)
    print("[停止] Bot 已停止")
    print("=" * 70)
    print("\n如果你已經獲得了 Chat ID 並更新了 .env 檔案，")
    print("請執行以下命令測試 Bot 功能：")
    print("\n  python src/test_bot.py")
    print("\n" + "=" * 70)
except Exception as e:
    print(f"\n[錯誤] {e}")
