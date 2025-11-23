"""
测试单行 Quote 数据的解析

用于快速验证 Python 解码器的正确性
"""

import pandas as pd
from datetime import datetime
import json


def parse_timestamp(timestamp_str, date_str):
    """
    解析时间戳并转换为 datetime
    时间戳格式: HHMMSSffffff (时分秒+微秒，共12位)
    """
    try:
        ts = str(timestamp_str).zfill(12)
        dt_str = date_str + ts
        return pd.to_datetime(dt_str, format='%Y%m%d%H%M%S%f', errors='coerce')
    except:
        return pd.NaT


def parse_trade_line(line, date_str):
    """
    解析 Trade 资料行
    格式: Trade,股票代码,成交时间,试撮旗标,成交价,成交单量,成交总量[,序号]
    """
    fields = line.strip().split(',')
    if len(fields) < 7:
        return None

    try:
        stock_code = fields[1].strip()
        timestamp = fields[2].strip()
        flag = int(fields[3])
        price_raw = int(fields[4])
        volume = int(fields[5])
        total_volume = int(fields[6])

        # 价格除以 10000（4位小数）
        price = price_raw / 10000.0
        dt = parse_timestamp(timestamp, date_str)

        return {
            'Type': 'Trade',
            'StockCode': stock_code,
            'Datetime': dt,
            'Timestamp': int(timestamp) if timestamp.isdigit() else None,
            'Flag': flag,
            'Price': price,
            'Volume': volume,
            'TotalVolume': total_volume
        }
    except (ValueError, IndexError):
        return None


def parse_depth_line(line, date_str):
    """
    解析 Depth 资料行
    格式: Depth,股票代码,报价时间,BID:委买档数,买盘档位...,ASK:委卖档数,卖盘档位...[,序号]
    """
    fields = line.strip().split(',')
    if len(fields) < 4:
        return None

    try:
        stock_code = fields[1].strip()
        timestamp = fields[2].strip()

        # 寻找 BID 和 ASK
        bid_idx = -1
        ask_idx = -1
        bid_count = 0
        ask_count = 0

        for i, field in enumerate(fields):
            if 'BID:' in field:
                bid_idx = i
                bid_count = int(field.split(':')[1])
            elif 'ASK:' in field:
                ask_idx = i
                ask_count = int(field.split(':')[1])

        if bid_idx == -1 or ask_idx == -1:
            return None

        dt = parse_timestamp(timestamp, date_str)

        result = {
            'Type': 'Depth',
            'StockCode': stock_code,
            'Datetime': dt,
            'Timestamp': int(timestamp) if timestamp.isdigit() else None,
            'BidCount': bid_count,
            'AskCount': ask_count
        }

        # 解析买盘5档
        bid_fields = fields[bid_idx+1:ask_idx]
        for i in range(5):
            if i < len(bid_fields) and i < bid_count and '*' in bid_fields[i]:
                price_str, volume_str = bid_fields[i].split('*')
                price = int(price_str) / 10000.0
                volume = int(volume_str)
                result[f'Bid{i+1}_Price'] = price
                result[f'Bid{i+1}_Volume'] = volume
            else:
                result[f'Bid{i+1}_Price'] = None
                result[f'Bid{i+1}_Volume'] = None

        # 解析卖盘5档
        last_field = fields[-1]
        end_idx = -1 if '*' not in last_field else None
        ask_fields = fields[ask_idx+1:end_idx] if end_idx else fields[ask_idx+1:]

        for i in range(5):
            if i < len(ask_fields) and i < ask_count and '*' in ask_fields[i]:
                price_str, volume_str = ask_fields[i].split('*')
                price = int(price_str) / 10000.0
                volume = int(volume_str)
                result[f'Ask{i+1}_Price'] = price
                result[f'Ask{i+1}_Volume'] = volume
            else:
                result[f'Ask{i+1}_Price'] = None
                result[f'Ask{i+1}_Volume'] = None

        return result

    except (ValueError, IndexError):
        return None


def format_result(result: dict) -> str:
    """格式化输出结果为 JSON"""
    if result is None:
        return "解析失败"

    # 转换 Datetime 为字符串
    output = result.copy()
    if 'Datetime' in output and pd.notna(output['Datetime']):
        output['Datetime'] = str(output['Datetime'])

    return json.dumps(output, indent=2, ensure_ascii=False)


def main():
    """主程序"""
    import sys
    import io

    # Windows 控制台编码修复
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("="*80)
    print("单行 Quote 数据解析测试")
    print("="*80)

    # 测试日期
    date_str = '20251119'

    # 测试 Trade 行
    print("\n[测试 1] Trade 格式")
    print("-"*80)

    trade_line = "Trade,2355  ,131219825776,0,333500,1,1530,1234"
    print(f"输入: {trade_line}")
    print("\n预期输出:")
    print("  Type: Trade")
    print("  StockCode: 2355")
    print("  Timestamp: 131219825776")
    print("  Flag: 0")
    print("  Price: 33.35 (333500 / 10000)")
    print("  Volume: 1")
    print("  TotalVolume: 1530")

    print("\n实际输出:")
    result = parse_trade_line(trade_line, date_str)
    print(format_result(result))

    # 测试 Depth 行
    print("\n[测试 2] Depth 格式")
    print("-"*80)

    depth_line = "Depth,2355  ,131219825776,BID:5,333000*27,332500*5,332000*32,331500*35,331000*62,ASK:5,333500*17,334000*5,334500*13,335000*44,335500*14,1234"
    print(f"输入: {depth_line}")
    print("\n预期输出:")
    print("  Type: Depth")
    print("  StockCode: 2355")
    print("  Timestamp: 131219825776")
    print("  BidCount: 5")
    print("  AskCount: 5")
    print("  Bid1_Price: 33.30, Bid1_Volume: 27")
    print("  Ask1_Price: 33.35, Ask1_Volume: 17")

    print("\n实际输出:")
    result = parse_depth_line(depth_line, date_str)
    print(format_result(result))

    # 测试边界情况
    print("\n[测试 3] 边界情况 - 不完整的五档")
    print("-"*80)

    depth_line_partial = "Depth,1234  ,91814838927,BID:3,193000*60,192500*48,192000*59,ASK:3,193500*26,194000*40,194500*9,1234"
    print(f"输入: {depth_line_partial}")

    result = parse_depth_line(depth_line_partial, date_str)
    print("\n实际输出:")
    print(format_result(result))

    # 测试时间戳解析
    print("\n[测试 4] 时间戳解析")
    print("-"*80)

    test_timestamps = [
        ('91814838927', '09:18:14.838927'),
        ('131219825776', '13:12:19.825776'),
        ('84127027089', '08:41:27.027089'),
    ]

    for ts_str, expected in test_timestamps:
        dt = parse_timestamp(ts_str, date_str)
        print(f"  {ts_str} -> {dt} (预期: {date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {expected})")

    print("\n" + "="*80)
    print("测试完成")
    print("="*80)


if __name__ == "__main__":
    main()
