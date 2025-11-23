"""整合行情訂閱的 Telegram Bot"""

import os
import asyncio
from datetime import datetime
from typing import Set, Optional
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from quote_subscriber import QuoteSubscriber
from quote_parser import TradeData, DepthData

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


class QuoteBot:
    """行情推送 Bot"""

    def __init__(self):
        self.bot: Optional[Bot] = None
        self.chat_id = TELEGRAM_CHAT_ID
        self.subscriber: Optional[QuoteSubscriber] = None
        self.subscribed_stocks: Set[str] = set()

        # 推送控制
        self.notify_trades = True  # 是否推送成交
        self.notify_depth = False  # 是否推送五檔 (通常不需要)
        self.trade_count = 0
        self.last_notify_time = None

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """啟動指令"""
        await update.message.reply_text(
            '歡迎使用量化交易 Bot！\n\n'
            '可用指令:\n'
            '/start - 啟動 Bot\n'
            '/help - 顯示幫助\n'
            '/subscribe <股票代碼> - 訂閱股票 (例: /subscribe 2330)\n'
            '/unsubscribe <股票代碼> - 取消訂閱\n'
            '/list - 顯示訂閱清單\n'
            '/stats - 顯示統計資訊\n'
            '/test_file - 測試檔案讀取'
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """幫助指令"""
        help_text = '''
📊 <b>量化交易 Bot 指令說明</b>

<b>訂閱管理:</b>
/subscribe 2330 - 訂閱台積電
/subscribe 2330 2303 - 訂閱多檔股票
/unsubscribe 2330 - 取消訂閱
/list - 顯示目前訂閱清單

<b>資訊查詢:</b>
/stats - 顯示統計資訊
/test_file - 測試從檔案讀取行情

<b>說明:</b>
• 訂閱後會即時推送成交資訊
• 自動判斷內外盤 (買盤/賣盤)
• 支援試撮旗標顯示
        '''
        await update.message.reply_text(help_text, parse_mode='HTML')

    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """訂閱股票"""
        if not context.args:
            await update.message.reply_text('請提供股票代碼\n例如: /subscribe 2330')
            return

        for stock_id in context.args:
            stock_id = stock_id.strip().upper()
            self.subscribed_stocks.add(stock_id)

        await update.message.reply_text(
            f'✓ 已訂閱: {", ".join(sorted(self.subscribed_stocks))}\n\n'
            f'目前訂閱 {len(self.subscribed_stocks)} 檔股票'
        )

    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """取消訂閱"""
        if not context.args:
            await update.message.reply_text('請提供股票代碼\n例如: /unsubscribe 2330')
            return

        removed = []
        for stock_id in context.args:
            stock_id = stock_id.strip().upper()
            if stock_id in self.subscribed_stocks:
                self.subscribed_stocks.remove(stock_id)
                removed.append(stock_id)

        if removed:
            await update.message.reply_text(
                f'✓ 已取消訂閱: {", ".join(removed)}\n\n'
                f'剩餘訂閱 {len(self.subscribed_stocks)} 檔股票'
            )
        else:
            await update.message.reply_text('未找到要取消的股票')

    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """顯示訂閱清單"""
        if not self.subscribed_stocks:
            await update.message.reply_text('目前沒有訂閱任何股票\n使用 /subscribe 開始訂閱')
        else:
            stocks_list = '\n'.join([f'• {stock}' for stock in sorted(self.subscribed_stocks)])
            await update.message.reply_text(
                f'📋 <b>訂閱清單</b> ({len(self.subscribed_stocks)} 檔)\n\n{stocks_list}',
                parse_mode='HTML'
            )

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """顯示統計"""
        await update.message.reply_text(
            f'📊 <b>統計資訊</b>\n\n'
            f'訂閱股票數: {len(self.subscribed_stocks)}\n'
            f'總成交筆數: {self.trade_count}\n'
            f'推送成交: {"開啟" if self.notify_trades else "關閉"}\n'
            f'推送五檔: {"開啟" if self.notify_depth else "關閉"}',
            parse_mode='HTML'
        )

    async def test_file_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """測試檔案讀取"""
        await update.message.reply_text('開始測試檔案讀取...')

        # 使用測試股票
        test_stocks = {'8043', '6223', '1785'}
        subscriber = QuoteSubscriber(stock_ids=test_stocks)

        # 計數器
        trade_count = [0]
        depth_count = [0]

        def count_trade(trade: TradeData):
            trade_count[0] += 1

        def count_depth(depth: DepthData):
            depth_count[0] += 1

        subscriber.add_trade_callback(count_trade)
        subscriber.add_depth_callback(count_depth)

        # 讀取檔案
        file_path = r"C:\Users\tacor\Documents\tick-data\OTCQuote.20251031"
        await subscriber.subscribe_from_file(file_path, delay_ms=0)

        await update.message.reply_text(
            f'✓ 測試完成\n\n'
            f'測試股票: {", ".join(sorted(test_stocks))}\n'
            f'成交筆數: {trade_count[0]}\n'
            f'五檔筆數: {depth_count[0]}'
        )

    async def handle_trade(self, trade: TradeData):
        """處理成交資料 - 推送到 Telegram"""
        if not self.notify_trades or not self.chat_id:
            return

        self.trade_count += 1

        # 格式化訊息
        tick_emoji = {"1": "🟢", "2": "🔴"}.get(trade.tick_type, "⚪")
        tick_label = {"1": "買盤", "2": "賣盤"}.get(trade.tick_type, "未知")
        trial_text = " [試撮]" if trade.trial_flag == "1" else ""

        message = (
            f"{tick_emoji} <b>{trade.stock_id}</b> {tick_label}{trial_text}\n"
            f"成交價: <b>${trade.price:.2f}</b>\n"
            f"單量: {trade.volume} | 總量: {trade.total_volume}"
        )

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"推送訊息失敗: {e}")

    async def handle_depth(self, depth: DepthData):
        """處理五檔資料 (通常不推送，僅用於內外盤判斷)"""
        if not self.notify_depth:
            return
        # 可以選擇性推送五檔更新
        pass

    async def run_subscriber_task(self, mode: str = 'file', **kwargs):
        """背景執行訂閱任務"""
        if not self.subscribed_stocks and mode == 'redis':
            print("警告: 未訂閱任何股票")
            return

        stock_ids = self.subscribed_stocks if self.subscribed_stocks else None
        self.subscriber = QuoteSubscriber(stock_ids=stock_ids)

        # 註冊回調
        self.subscriber.add_trade_callback(self.handle_trade)
        self.subscriber.add_depth_callback(self.handle_depth)

        # 開始訂閱
        if mode == 'file':
            file_path = kwargs.get('file_path', r"C:\Users\tacor\Documents\tick-data\OTCQuote.20251031")
            delay_ms = kwargs.get('delay_ms', 0)
            await self.subscriber.subscribe_from_file(file_path, delay_ms)
        elif mode == 'redis':
            host = kwargs.get('host', '192.168.100.130')
            port = kwargs.get('port', 6379)
            await self.subscriber.subscribe_from_redis(host=host, port=port)

    def run(self, mode: str = 'bot_only'):
        """
        啟動 Bot

        Args:
            mode: 'bot_only' | 'file' | 'redis'
                - bot_only: 僅啟動 Bot，手動使用指令測試
                - file: 啟動 Bot + 自動從檔案讀取
                - redis: 啟動 Bot + Redis 訂閱
        """
        if not TELEGRAM_BOT_TOKEN:
            print("錯誤: 未設定 TELEGRAM_BOT_TOKEN")
            return

        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.bot = application.bot

        # 註冊指令
        application.add_handler(CommandHandler('start', self.start_command))
        application.add_handler(CommandHandler('help', self.help_command))
        application.add_handler(CommandHandler('subscribe', self.subscribe_command))
        application.add_handler(CommandHandler('unsubscribe', self.unsubscribe_command))
        application.add_handler(CommandHandler('list', self.list_command))
        application.add_handler(CommandHandler('stats', self.stats_command))
        application.add_handler(CommandHandler('test_file', self.test_file_command))

        print(f"🤖 Bot 啟動中... (模式: {mode})")

        # 根據模式決定是否啟動訂閱任務
        if mode in ['file', 'redis']:
            # 在背景執行訂閱任務
            asyncio.create_task(self.run_subscriber_task(mode=mode))

        application.run_polling()


if __name__ == "__main__":
    bot = QuoteBot()

    # 模式選擇
    # 1. 僅啟動 Bot，手動測試
    bot.run(mode='bot_only')

    # 2. 啟動 Bot + 自動從檔案讀取 (測試用)
    # bot.subscribed_stocks = {'8043', '6223', '1785'}
    # bot.run(mode='file')

    # 3. 啟動 Bot + Redis 訂閱 (實際使用)
    # bot.subscribed_stocks = {'2330', '2303'}
    # bot.run(mode='redis')