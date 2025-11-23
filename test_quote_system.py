"""測試行情系統 - 快速驗證功能"""

import asyncio
import sys
import os
from pathlib import Path

# 設定 UTF-8 輸出 (Windows)
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.quote_parser import QuoteParser, TradeData, DepthData
from src.quote_subscriber import QuoteSubscriber
from src.config import QUOTE_FILE_PATH, SUBSCRIBED_STOCKS


def test_parser():
    """測試解析器"""
    print("=" * 60)
    print("測試 1: 行情解析器")
    print("=" * 60)

    parser = QuoteParser()

    # 測試五檔
    print("\n[測試五檔解析]")
    depth_line = "Depth,8043  ,84127027089,BID:5,486000*3,485500*10,485000*25,483000*1,479500*1,ASK:5,492000*1,493000*1,494000*6,495000*2,496000*1"
    result = parser.parse_line(depth_line)
    if result:
        data_type, data = result
        print(f"[OK] 類型: {data_type}")
        print(f"[OK] 資料: {data}")
    else:
        print("[FAIL] 解析失敗")

    # 測試成交 (買盤)
    print("\n[測試成交解析 - 買盤]")
    trade_line = "Trade,8043  ,84127027089,1,492000,17,0"
    result = parser.parse_line(trade_line)
    if result:
        data_type, data = result
        print(f"[OK] 類型: {data_type}")
        print(f"[OK] 資料: {data}")
        print(f"[OK] 內外盤: {data.tick_type} (1=買盤, 2=賣盤)")
    else:
        print("[FAIL] 解析失敗")

    # 測試成交 (賣盤)
    print("\n[測試成交解析 - 賣盤]")
    trade_line2 = "Trade,8043  ,84127027089,0,485000,10,27"
    result = parser.parse_line(trade_line2)
    if result:
        data_type, data = result
        print(f"[OK] 類型: {data_type}")
        print(f"[OK] 資料: {data}")
        print(f"[OK] 內外盤: {data.tick_type} (1=買盤, 2=賣盤)")
    else:
        print("[FAIL] 解析失敗")

    print("\n[OK] 解析器測試完成\n")


async def test_subscriber():
    """測試訂閱器"""
    print("=" * 60)
    print("測試 2: 行情訂閱器 (檔案模式)")
    print("=" * 60)

    # 統計
    stats = {
        'trade_count': 0,
        'depth_count': 0,
        'buy_count': 0,
        'sell_count': 0,
    }

    def handle_trade(trade: TradeData):
        stats['trade_count'] += 1
        if trade.tick_type == "1":
            stats['buy_count'] += 1
        elif trade.tick_type == "2":
            stats['sell_count'] += 1

        # 顯示前 5 筆
        if stats['trade_count'] <= 5:
            print(f"  {trade}")

    def handle_depth(depth: DepthData):
        stats['depth_count'] += 1

    # 建立訂閱器
    subscriber = QuoteSubscriber(stock_ids=SUBSCRIBED_STOCKS)
    subscriber.add_trade_callback(handle_trade)
    subscriber.add_depth_callback(handle_depth)

    print(f"\n訂閱股票: {', '.join(sorted(SUBSCRIBED_STOCKS)) if SUBSCRIBED_STOCKS else '全部'}")
    print(f"資料來源: {QUOTE_FILE_PATH}\n")

    # 讀取檔案
    await subscriber.subscribe_from_file(QUOTE_FILE_PATH, delay_ms=0)

    # 顯示統計
    print("\n" + "=" * 60)
    print("統計結果")
    print("=" * 60)
    print(f"成交筆數: {stats['trade_count']}")
    print(f"  - 買盤: {stats['buy_count']} ({stats['buy_count']/stats['trade_count']*100:.1f}%)" if stats['trade_count'] > 0 else "  - 買盤: 0")
    print(f"  - 賣盤: {stats['sell_count']} ({stats['sell_count']/stats['trade_count']*100:.1f}%)" if stats['trade_count'] > 0 else "  - 賣盤: 0")
    print(f"五檔筆數: {stats['depth_count']}")
    print("\n[OK] 訂閱器測試完成\n")


async def test_performance():
    """測試效能"""
    print("=" * 60)
    print("測試 3: 效能測試")
    print("=" * 60)

    import time

    start_time = time.time()

    # 訂閱全部，測試處理速度
    subscriber = QuoteSubscriber(stock_ids=None)

    count = [0]

    def count_callback(data):
        count[0] += 1

    subscriber.add_trade_callback(count_callback)
    subscriber.add_depth_callback(count_callback)

    await subscriber.subscribe_from_file(QUOTE_FILE_PATH, delay_ms=0)

    elapsed = time.time() - start_time
    rate = count[0] / elapsed if elapsed > 0 else 0

    print(f"\n處理筆數: {count[0]:,}")
    print(f"耗時: {elapsed:.2f} 秒")
    print(f"處理速度: {rate:,.0f} 筆/秒")
    print("\n[OK] 效能測試完成\n")


async def main():
    """執行所有測試"""
    print("\n" + "=" * 60)
    print("行情系統測試")
    print("=" * 60 + "\n")

    # 測試 1: 解析器
    test_parser()

    # 測試 2: 訂閱器
    await test_subscriber()

    # 測試 3: 效能
    await test_performance()

    print("=" * 60)
    print("所有測試完成!")
    print("=" * 60)
    print("\n下一步: 執行 'python src/quote_bot.py' 啟動 Telegram Bot")


if __name__ == "__main__":
    asyncio.run(main())
