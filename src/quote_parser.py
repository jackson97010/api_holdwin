"""高效能行情解析器 - 支援 Trade 和 Depth 資料解析與內外盤判斷"""

from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TradeData:
    """成交資料"""
    stock_id: str
    timestamp: str
    trial_flag: str  # 0:一般揭示 1:試算揭示
    price: float
    volume: int
    total_volume: int
    tick_type: Optional[str] = None  # 1:買盤(內盤) 2:賣盤(外盤)

    def __str__(self) -> str:
        tick_label = {"1": "買盤", "2": "賣盤"}.get(self.tick_type, "未知")
        trial = "試撮" if self.trial_flag == "1" else "一般"
        return (f"[{self.stock_id}] 成交 ${self.price:.2f} "
                f"量:{self.volume} 總量:{self.total_volume} "
                f"[{tick_label}] ({trial})")


@dataclass
class DepthLevel:
    """單一檔位資料"""
    price: float
    volume: int


@dataclass
class DepthData:
    """五檔資料"""
    stock_id: str
    timestamp: str
    bid_levels: List[DepthLevel]  # 買盤
    ask_levels: List[DepthLevel]  # 賣盤

    @property
    def bid1_price(self) -> Optional[float]:
        return self.bid_levels[0].price if self.bid_levels else None

    @property
    def ask1_price(self) -> Optional[float]:
        return self.ask_levels[0].price if self.ask_levels else None

    def __str__(self) -> str:
        bid1 = f"${self.bid1_price:.2f}x{self.bid_levels[0].volume}" if self.bid_levels else "N/A"
        ask1 = f"${self.ask1_price:.2f}x{self.ask_levels[0].volume}" if self.ask_levels else "N/A"
        return f"[{self.stock_id}] 買1:{bid1} 賣1:{ask1}"


class QuoteParser:
    """行情解析器 - 高效能處理 Trade 和 Depth 資料"""

    def __init__(self):
        # 快取每檔股票的最新五檔資料，用於判斷內外盤
        self._depth_cache: Dict[str, DepthData] = {}

    def parse_trade(self, line: str) -> Optional[TradeData]:
        """
        解析成交資料
        格式: Trade,股票代碼,成交時間,試撮旗標,成交價,成交單量,成交總量
        範例: Trade,8043  ,84127027089,1,492000,17,0
        """
        if not line or not line.startswith("Trade"):
            return None

        try:
            parts = line.split(',')
            if len(parts) < 7:
                return None

            stock_id = parts[1].strip()
            price = int(parts[4]) / 10000  # 4位小數轉換

            trade = TradeData(
                stock_id=stock_id,
                timestamp=parts[2],
                trial_flag=parts[3],
                price=price,
                volume=int(parts[5]),
                total_volume=int(parts[6])
            )

            # 使用最新五檔判斷內外盤
            trade.tick_type = self._determine_tick_type(stock_id, price)

            return trade

        except (ValueError, IndexError):
            return None

    def parse_depth(self, line: str) -> Optional[DepthData]:
        """
        解析五檔資料
        格式: Depth,股票代碼,報價時間,BID:檔數,價格*數量...,ASK:檔數,價格*數量...
        範例: Depth,8043  ,84127027089,BID:5,486000*3,485500*10,485000*25,483000*1,479500*1,ASK:5,492000*1,493000*1,494000*6,495000*2,496000*1
        """
        if not line or not line.startswith("Depth"):
            return None

        try:
            parts = line.split(',')
            if len(parts) < 4:
                return None

            stock_id = parts[1].strip()
            timestamp = parts[2]

            bid_levels = []
            ask_levels = []
            current_side = None

            for part in parts[3:]:
                part = part.strip()

                if part.startswith("BID:"):
                    current_side = "BID"
                    continue
                elif part.startswith("ASK:"):
                    current_side = "ASK"
                    continue

                # 解析 價格*數量
                if '*' in part:
                    price_str, vol_str = part.split('*', 1)
                    price = int(price_str) / 10000
                    volume = int(vol_str)

                    level = DepthLevel(price=price, volume=volume)

                    if current_side == "BID":
                        bid_levels.append(level)
                    elif current_side == "ASK":
                        ask_levels.append(level)

            depth = DepthData(
                stock_id=stock_id,
                timestamp=timestamp,
                bid_levels=bid_levels,
                ask_levels=ask_levels
            )

            # 更新快取
            self._depth_cache[stock_id] = depth

            return depth

        except (ValueError, IndexError):
            return None

    def _determine_tick_type(self, stock_id: str, price: float) -> Optional[str]:
        """
        判斷內外盤
        - 成交價 >= 賣1價 → 買盤 (1)
        - 成交價 <= 買1價 → 賣盤 (2)
        - 成交價在買賣價之間 → 比較距離，較接近賣價為買盤，較接近買價為賣盤
        """
        depth = self._depth_cache.get(stock_id)

        if not depth:
            return None  # 無五檔資料，無法判斷

        bid1 = depth.bid1_price
        ask1 = depth.ask1_price

        # 情況1: 成交價 >= 賣1 → 買盤 (主動買進，吃掉賣單)
        if ask1 is not None and price >= ask1:
            return "1"

        # 情況2: 成交價 <= 買1 → 賣盤 (主動賣出，吃掉買單)
        if bid1 is not None and price <= bid1:
            return "2"

        # 情況3: 成交價在買賣之間，比較距離
        if bid1 is not None and ask1 is not None:
            dist_to_bid = abs(price - bid1)
            dist_to_ask = abs(price - ask1)
            # 較接近賣價 → 買盤，較接近買價 → 賣盤
            return "1" if dist_to_ask <= dist_to_bid else "2"

        # 情況4: 只有單邊報價
        elif ask1 is not None:
            return "1"  # 只有賣單，推測為買盤
        elif bid1 is not None:
            return "2"  # 只有買單，推測為賣盤

        return None  # 無法判斷

    def parse_line(self, line: str) -> Optional[Tuple[str, object]]:
        """
        解析單行資料，自動判斷類型
        Returns: (data_type, data_object) or None
        data_type: 'trade' or 'depth'
        """
        line = line.strip()

        if line.startswith("Trade"):
            trade = self.parse_trade(line)
            return ("trade", trade) if trade else None
        elif line.startswith("Depth"):
            depth = self.parse_depth(line)
            return ("depth", depth) if depth else None

        return None

    def get_latest_depth(self, stock_id: str) -> Optional[DepthData]:
        """取得指定股票的最新五檔資料"""
        return self._depth_cache.get(stock_id)

    def clear_cache(self):
        """清空五檔快取"""
        self._depth_cache.clear()


if __name__ == "__main__":
    # 測試範例
    parser = QuoteParser()

    # 先接收五檔
    depth_line = "Depth,8043  ,84127027089,BID:5,486000*3,485500*10,485000*25,483000*1,479500*1,ASK:5,492000*1,493000*1,494000*6,495000*2,496000*1"
    _, depth = parser.parse_line(depth_line)
    print(depth)

    # 再接收成交
    trade_line = "Trade,8043  ,84127027089,1,492000,17,0"
    _, trade = parser.parse_line(trade_line)
    print(trade)

    # 測試買盤成交
    trade_line2 = "Trade,8043  ,84127027089,0,493000,10,27"
    _, trade2 = parser.parse_line(trade_line2)
    print(trade2)