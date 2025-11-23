import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.message.chat.id
    logger.info(f'User {user.id} (Chat ID: {chat_id}) started the bot')

    await update.message.reply_text(
        f'你好 {user.mention_html()}！\n\n'
        f'歡迎使用量化交易 Bot！\n'
        f'輸入 /help 查看可用指令。\n\n'
        f'你的 Chat ID: <code>{chat_id}</code>',
        parse_mode='HTML'
    )
    print(f'\n[重要] Chat ID: {chat_id}')
    print(f'[提示] 請將此 Chat ID 更新到 .env 檔案中\n')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = '''
📋 <b>可用指令</b>

/start - 啟動 Bot
/help - 顯示此幫助訊息
/test - 測試訊息回覆

<b>專案說明</b>
這是一個 Telegram Bot 測試專案。
未來將整合 Shioaji API 進行量化交易系統開發。

<b>下一步功能</b>
• Shioaji API 連接
• 即時報價推送
• 交易訊號通知
• 策略回測結果
    '''
    await update.message.reply_text(help_text, parse_mode='HTML')
    logger.info(f'User {update.effective_user.id} requested help')

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        '✅ 測試成功！\n\n'
        '✓ Bot 運行正常\n'
        '✓ 訊息發送功能正常\n'
        '✓ 指令處理正常\n\n'
        '準備進行下一步開發！'
    )
    logger.info(f'User {update.effective_user.id} tested the bot')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    user_id = update.effective_user.id
    chat_id = update.message.chat.id

    logger.info(f'Received message from user {user_id} (Chat ID: {chat_id}): {user_message}')
    print(f'\n[訊息] Chat ID: {chat_id} | User: {user_id} | 訊息: {user_message}\n')

    response = f'收到您的訊息：「{user_message}」\n\n目前處於測試階段，請使用 /help 查看可用指令。\n\n你的 Chat ID: <code>{chat_id}</code>'
    await update.message.reply_text(response, parse_mode='HTML')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f'Update {update} caused error {context.error}')

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error('TELEGRAM_BOT_TOKEN not found in environment variables')
        return

    logger.info('Starting bot...')

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('test', test_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logger.info('Bot is running... Press Ctrl+C to stop')
    application.run_polling()

if __name__ == '__main__':
    main()
