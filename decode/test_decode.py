"""
OTC/TSE Quote 資料解碼程式
根據文件規格正確解析 Trade 和 Depth 資料
"""
import pandas as pd
import os
import re
from datetime import datetime, timedelta
from pathlib import Path


def load_limit_up_list(parquet_file):
    """載入漲停清單並建立日期到股票的映射"""
    df = pd.read_parquet(parquet_file)
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')
    df['stock_id'] = df['stock_id'].astype(str).str.strip()

    date_stocks = {}
    for _, row in df.iterrows():
        date_str = row['date']
        stock_id = row['stock_id']
        if date_str not in date_stocks:
            date_stocks[date_str] = set()
        date_stocks[date_str].add(stock_id)

    return date_stocks


def get_target_stocks(limit_up_dict, current_date):
    """獲取需要解析的股票（當日 + 前一交易日漲停）"""
    target_stocks = set()

    # 當日漲停股票
    if current_date in limit_up_dict:
        target_stocks.update(limit_up_dict[current_date])

    # 前一交易日漲停股票（向前找最多7天）
    try:
        current_dt = datetime.strptime(current_date, '%Y%m%d')
        for days_back in range(1, 8):
            prev_date = (current_dt - timedelta(days=days_back)).strftime('%Y%m%d')
            if prev_date in limit_up_dict:
                target_stocks.update(limit_up_dict[prev_date])
                break
    except:
        pass

    return target_stocks


def parse_timestamp(timestamp_str, date_str):
    """
    解析時間戳並轉換為 datetime
    時間戳格式: HHMMSSffffff (時分秒+微秒，共12位)
    例如: 84127027089 -> 08:41:27.027089
    """
    try:
        # 補0到12位
        ts = str(timestamp_str).zfill(12)
        # 組合日期和時間
        dt_str = date_str + ts  # YYYYMMDD + HHMMSSffffff
        return pd.to_datetime(dt_str, format='%Y%m%d%H%M%S%f', errors='coerce')
    except:
        return pd.NaT


def parse_trade_line(line, date_str):
    """
    解析 Trade 資料行
    格式: Trade,股票代碼,成交時間,試撮旗標,成交價,成交單量,成交總量[,序號]

    參數:
        - 試撮旗標: 0=一般揭示, 1=試算揭示
        - 成交價: 4位小數，需除以10000

    範例: Trade,2355  ,131219825776,0,333500,1,1530,1234
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

        # 價格需要除以 10000（4位小數）
        price = price_raw / 10000.0

        # 解析時間
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
    except (ValueError, IndexError) as e:
        return None


def parse_depth_line(line, date_str):
    """
    解析 Depth 資料行
    格式: Depth,股票代碼,報價時間,BID:委買檔數,買盤檔位...,ASK:委賣檔數,賣盤檔位...[,序號]

    檔位格式: 價格*數量
    價格需除以10000（4位小數）

    範例: Depth,2355  ,131219825776,BID:5,333000*27,332500*5,ASK:5,333500*17,334000*5,1234
    """
    fields = line.strip().split(',')

    if len(fields) < 4:
        return None

    try:
        stock_code = fields[1].strip()
        timestamp = fields[2].strip()

        # 尋找 BID 和 ASK 的位置
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

        # 解析時間
        dt = parse_timestamp(timestamp, date_str)

        result = {
            'Type': 'Depth',
            'StockCode': stock_code,
            'Datetime': dt,
            'Timestamp': int(timestamp) if timestamp.isdigit() else None,
            'BidCount': bid_count,
            'AskCount': ask_count
        }

        # 解析買盤5檔
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

        # 解析賣盤5檔（ASK之後到倒數第二個欄位，最後可能是序號）
        # 如果最後一個欄位不包含*，則認為是序號
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

    except (ValueError, IndexError) as e:
        return None


def process_quote_file(file_path, target_stocks, date_str, output_dir):
    """
    處理單個 Quote 檔案，提取目標股票的資料並保存

    參數:
        file_path: Quote 檔案路徑
        target_stocks: 要提取的股票代碼集合
        date_str: 日期字串 (YYYYMMDD)
        output_dir: 輸出目錄
    """
    print(f"\n處理檔案: {os.path.basename(file_path)}")
    print(f"目標股票數: {len(target_stocks)}")

    # 初始化資料容器
    stock_data = {stock: [] for stock in target_stocks}

    # 統計
    stats = {'trade': 0, 'depth': 0, 'error': 0, 'total_lines': 0}

    # 逐行讀取並解析
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                stats['total_lines'] += 1

                # 跳過非資料行
                if not line.startswith('Trade,') and not line.startswith('Depth,'):
                    continue

                # 提取股票代碼（第二個欄位）
                fields = line.split(',')
                if len(fields) < 2:
                    continue

                stock_code = fields[1].strip()

                # 只處理目標股票
                if stock_code not in target_stocks:
                    continue

                # 根據類型解析
                if line.startswith('Trade,'):
                    parsed = parse_trade_line(line, date_str)
                    if parsed:
                        stock_data[stock_code].append(parsed)
                        stats['trade'] += 1
                    else:
                        stats['error'] += 1

                elif line.startswith('Depth,'):
                    parsed = parse_depth_line(line, date_str)
                    if parsed:
                        stock_data[stock_code].append(parsed)
                        stats['depth'] += 1
                    else:
                        stats['error'] += 1

    except Exception as e:
        print(f"讀取檔案時發生錯誤: {e}")
        return 0

    print(f"讀取完成: 總行數={stats['total_lines']}, Trade={stats['trade']}, Depth={stats['depth']}, 錯誤={stats['error']}")

    # 保存每支股票的資料
    saved_count = 0
    os.makedirs(output_dir, exist_ok=True)

    for stock_code, records in stock_data.items():
        if not records:
            continue

        # 建立 DataFrame
        df = pd.DataFrame(records)

        # 按時間排序
        if 'Datetime' in df.columns:
            df = df.sort_values('Datetime').reset_index(drop=True)

        # 保存為 parquet
        output_path = os.path.join(output_dir, f"{stock_code}.parquet")
        df.to_parquet(output_path, index=False)

        saved_count += 1
        print(f"  已保存: {stock_code}.parquet ({len(df)} 筆記錄)")

    return saved_count


def main():
    """主程式"""
    print("=" * 80)
    print("OTC/TSE Quote 資料解碼程式")
    print("=" * 80)

    # 設定路徑
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_dir = os.path.join(project_root, 'data')

    limit_up_file = os.path.join(data_dir, 'lup_ma20_filtered.parquet')
    output_base_dir = os.path.join(data_dir, 'decoded_quotes')

    # 檢查漲停清單檔案
    if not os.path.exists(limit_up_file):
        print(f"錯誤: 找不到漲停清單檔案 {limit_up_file}")
        return

    # 載入漲停清單
    print(f"\n載入漲停清單: {limit_up_file}")
    limit_up_dict = load_limit_up_list(limit_up_file)
    print(f"共載入 {len(limit_up_dict)} 個日期的漲停資料")

    # 測試日期: 2025-10-31
    test_date = '20251119'

    print(f"\n處理日期: {test_date}")
    target_stocks = get_target_stocks(limit_up_dict, test_date)
    print(f"目標股票數: {len(target_stocks)}")
    print(f"股票清單: {sorted(target_stocks)}")

    if not target_stocks:
        print("沒有需要處理的股票")
        return

    # 處理 OTC 和 TSE 檔案
    output_dir = os.path.join(output_base_dir, test_date)

    for market in ['OTC', 'TSE']:
        quote_file = os.path.join(data_dir, f"{market}Quote.{test_date}")

        if os.path.exists(quote_file):
            saved = process_quote_file(quote_file, target_stocks, test_date, output_dir)
            print(f"\n{market}Quote 處理完成，保存 {saved} 支股票")
        else:
            print(f"\n未找到 {market}Quote.{test_date}")

    print("\n" + "=" * 80)
    print("解碼完成！")
    print(f"輸出目錄: {output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
