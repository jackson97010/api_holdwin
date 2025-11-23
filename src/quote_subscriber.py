"""行情訂閱器 - 支援 Redis 訂閱和檔案讀取兩種模式"""

import time
import asyncio
from pathlib import Path
from typing import Set, Callable, Optional, List
from quote_parser import QuoteParser, TradeData, DepthData

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: redis module not available. Only file mode is supported.")


class QuoteSubscriber:
    """行情訂閱器 - 高效能處理行情資料"""

    def __init__(self, stock_ids: Optional[Set[str]] = None):
        """
        初始化訂閱器

        Args:
            stock_ids: 要訂閱的股票代碼集合，None 表示訂閱所有
        """
        self.stock_ids = stock_ids  # None = 訂閱全部
        self.parser = QuoteParser()
        self.trade_callbacks: List[Callable] = []
        self.depth_callbacks: List[Callable] = []
        self._running = False

    def add_trade_callback(self, callback: Callable[[TradeData], None]):
        """註冊成交資料回調函數"""
        self.trade_callbacks.append(callback)

    def add_depth_callback(self, callback: Callable[[DepthData], None]):
        """註冊五檔資料回調函數"""
        self.depth_callbacks.append(callback)

    def _should_process(self, stock_id: str) -> bool:
        """判斷是否處理該股票"""
        if self.stock_ids is None:
            return True  # 訂閱全部
        return stock_id in self.stock_ids

    async def _process_line(self, line: str):
        """處理單行資料"""
        result = self.parser.parse_line(line)
        if not result:
            return

        data_type, data = result

        # 檢查是否需要處理該股票
        stock_id = data.stock_id if hasattr(data, 'stock_id') else None
        if stock_id and not self._should_process(stock_id):
            return

        # 呼叫對應的回調函數
        if data_type == "trade" and self.trade_callbacks:
            for callback in self.trade_callbacks:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)

        elif data_type == "depth" and self.depth_callbacks:
            for callback in self.depth_callbacks:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)

    async def subscribe_from_file(self, file_path: str, delay_ms: float = 0):
        """
        從檔案讀取行情資料並處理

        Args:
            file_path: 行情檔案路徑
            delay_ms: 每行之間的延遲時間(毫秒)，用於模擬即時行情
        """
        self._running = True
        path = Path(file_path)

        if not path.exists():
            print(f"錯誤: 檔案不存在 {file_path}")
            return

        print(f"開始讀取檔案: {file_path}")
        if self.stock_ids:
            print(f"訂閱股票: {', '.join(sorted(self.stock_ids))}")
        else:
            print("訂閱模式: 全部股票")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                line_count = 0
                processed_count = 0

                for line in f:
                    if not self._running:
                        break

                    line = line.strip()
                    line_count += 1

                    # 跳過系統訊息
                    if not line or not (line.startswith("Trade") or line.startswith("Depth")):
                        continue

                    await self._process_line(line)
                    processed_count += 1

                    # 模擬延遲
                    if delay_ms > 0:
                        await asyncio.sleep(delay_ms / 1000)

                    # 定期輸出進度
                    if processed_count % 1000 == 0:
                        print(f"已處理 {processed_count} 筆資料...")

                print(f"\n處理完成! 總行數: {line_count}, 處理筆數: {processed_count}")

        except Exception as e:
            print(f"讀取檔案時發生錯誤: {e}")
        finally:
            self._running = False

    async def subscribe_from_redis(
        self,
        host: str = '192.168.100.130',
        port: int = 6379,
        db: int = 0
    ):
        """
        從 Redis 訂閱行情資料

        Args:
            host: Redis 主機位址
            port: Redis 埠號
            db: Redis 資料庫編號
        """
        if not REDIS_AVAILABLE:
            print("錯誤: redis 模組未安裝，請執行: pip install redis")
            return

        if not self.stock_ids:
            print("錯誤: Redis 訂閱模式必須指定 stock_ids")
            return

        self._running = True
        channels = list(self.stock_ids)

        print(f"正在連接 Redis: {host}:{port}")
        print(f"訂閱股票: {', '.join(sorted(channels))}")

        while self._running:
            try:
                r = redis.Redis(host=host, port=port, db=db, socket_timeout=5)
                p = r.pubsub(ignore_subscribe_messages=True)
                p.subscribe(channels)

                print("✓ 已訂閱，等待行情資料...")

                for message in p.listen():
                    if not self._running:
                        break

                    ch = message['channel'].decode('utf-8')
                    data = message['data'].decode('utf-8')

                    await self._process_line(data)

            except redis.exceptions.ConnectionError:
                print("⚠️ Redis 連線中斷，5秒後重試...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"錯誤: {e}")
                await asyncio.sleep(5)

    def stop(self):
        """停止訂閱"""
        self._running = False
        print("正在停止訂閱...")


# ============ 使用範例 ============

def example_trade_handler(trade: TradeData):
    """成交資料處理範例"""
    print(f"✓ {trade}")


def example_depth_handler(depth: DepthData):
    """五檔資料處理範例 (僅顯示買賣一檔)"""
    # 可以選擇不輸出，或只輸出特定條件
    pass


async def main():
    """測試範例"""

    # 範例1: 訂閱特定股票 (從檔案讀取)
    subscriber = QuoteSubscriber(stock_ids={'8043', '6223', '1785'})

    # 註冊回調函數
    subscriber.add_trade_callback(example_trade_handler)
    subscriber.add_depth_callback(example_depth_handler)

    # 從檔案讀取 (不延遲，全速處理)
    file_path = r"C:\Users\tacor\Documents\tick-data\OTCQuote.20251031"
    await subscriber.subscribe_from_file(file_path, delay_ms=0)

    # 範例2: 訂閱全部股票
    # subscriber = QuoteSubscriber(stock_ids=None)
    # await subscriber.subscribe_from_file(file_path, delay_ms=0)

    # 範例3: Redis 訂閱 (需要 Redis 可用)
    # subscriber = QuoteSubscriber(stock_ids={'2330', '2303'})
    # subscriber.add_trade_callback(example_trade_handler)
    # await subscriber.subscribe_from_redis()


if __name__ == "__main__":
    asyncio.run(main())