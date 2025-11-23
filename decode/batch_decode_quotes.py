"""
OTC/TSE Quote 批次解碼程式
自動處理所有日期的 Quote 檔案
"""
import pandas as pd
import os
import re
import glob
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


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
    """
    try:
        ts = str(timestamp_str).zfill(12)
        dt_str = date_str + ts
        return pd.to_datetime(dt_str, format='%Y%m%d%H%M%S%f', errors='coerce')
    except:
        return pd.NaT


def parse_trade_line(line, date_str):
    """
    解析 Trade 資料行
    格式: Trade,股票代碼,成交時間,試撮旗標,成交價,成交單量,成交總量[,序號]
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

        # 價格除以 10000（4位小數）
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
    解析 Depth 資料行
    格式: Depth,股票代碼,報價時間,BID:委買檔數,買盤檔位...,ASK:委賣檔數,賣盤檔位...[,序號]
    """
    fields = line.strip().split(',')
    if len(fields) < 4:
        return None

    try:
        stock_code = fields[1].strip()
        timestamp = fields[2].strip()

        # 尋找 BID 和 ASK
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

        # 解析賣盤5檔
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


def process_quote_file(file_path, target_stocks, date_str, output_dir):
    """處理單個 Quote 檔案"""
    print(f"\n處理: {os.path.basename(file_path)}")

    # 初始化資料容器
    stock_data = {stock: [] for stock in target_stocks}
    stats = {'trade': 0, 'depth': 0, 'error': 0}

    # 讀取並解析
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.startswith('Trade,') and not line.startswith('Depth,'):
                    continue

                fields = line.split(',')
                if len(fields) < 2:
                    continue

                stock_code = fields[1].strip()
                if stock_code not in target_stocks:
                    continue

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
        print(f"  錯誤: {e}")
        return 0

    # 保存資料
    saved_count = 0
    os.makedirs(output_dir, exist_ok=True)

    for stock_code, records in stock_data.items():
        if not records:
            continue

        df = pd.DataFrame(records)

        if 'Datetime' in df.columns:
            df = df.sort_values('Datetime').reset_index(drop=True)

        output_path = os.path.join(output_dir, f"{stock_code}.parquet")
        df.to_parquet(output_path, index=False)
        saved_count += 1

    print(f"  Trade={stats['trade']}, Depth={stats['depth']}, 已保存={saved_count}支")
    return saved_count


def process_date(date_str, limit_up_dict, data_dir, output_base_dir):
    """處理單個日期的 OTC 和 TSE 檔案"""
    print(f"\n{'='*60}")
    print(f"處理日期: {date_str}")
    print(f"{'='*60}")

    target_stocks = get_target_stocks(limit_up_dict, date_str)

    if not target_stocks:
        print("  無目標股票，跳過")
        return 0

    print(f"  目標股票: {len(target_stocks)}支")

    # 檢查是否已處理完成
    output_dir = os.path.join(output_base_dir, date_str)
    if os.path.exists(output_dir):
        existing_files = set(os.listdir(output_dir))
        expected_files = {f"{stock}.parquet" for stock in target_stocks}
        if expected_files.issubset(existing_files):
            print("  所有檔案已存在，跳過")
            return 0

    total_saved = 0

    # 處理 OTC 和 TSE
    for market in ['OTC', 'TSE']:
        quote_file = os.path.join(data_dir, f"{market}Quote.{date_str}")

        if os.path.exists(quote_file):
            saved = process_quote_file(quote_file, target_stocks, date_str, output_dir)
            total_saved += saved
        else:
            print(f"  未找到 {market}Quote.{date_str}")

    print(f"  日期 {date_str} 完成，共保存 {total_saved} 支股票")
    return total_saved


def main():
    """主程式"""
    print("=" * 80)
    print("OTC/TSE Quote 批次解碼程式")
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

    # 掃描所有 Quote 檔案
    all_dates = set()

    for pattern in ['OTCQuote.*', 'TSEQuote.*']:
        files = glob.glob(os.path.join(data_dir, pattern))
        for f in files:
            match = re.search(r'(\d{8})$', os.path.basename(f))
            if match:
                all_dates.add(match.group(1))

    all_dates = sorted(all_dates)
    print(f"\n找到 {len(all_dates)} 個日期: {all_dates[0]} ~ {all_dates[-1]}")

    if not all_dates:
        print("沒有找到 Quote 檔案")
        return

    # 過濾出有漲停股票的日期
    dates_to_process = []
    for date_str in all_dates:
        target_stocks = get_target_stocks(limit_up_dict, date_str)
        if target_stocks:
            dates_to_process.append(date_str)

    print(f"需要處理的日期: {len(dates_to_process)} 個")

    if not dates_to_process:
        print("沒有需要處理的日期")
        return

    # 詢問是否使用多線程
    use_multithread = True
    max_workers = min(4, os.cpu_count() or 4)

    print(f"\n將使用 {max_workers} 個線程並行處理")
    print("\n開始處理...")

    # 處理
    total_files_saved = 0
    completed = {'count': 0}
    lock = threading.Lock()

    def process_with_progress(date_str):
        """帶進度顯示的處理函數"""
        try:
            saved = process_date(date_str, limit_up_dict, data_dir, output_base_dir)
            with lock:
                completed['count'] += 1
                print(f"\n[進度: {completed['count']}/{len(dates_to_process)}]")
            return saved
        except Exception as e:
            print(f"\n處理 {date_str} 時發生錯誤: {e}")
            return 0

    if use_multithread:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_with_progress, date) for date in dates_to_process]

            for future in as_completed(futures):
                try:
                    saved = future.result()
                    total_files_saved += saved
                except Exception as e:
                    print(f"執行錯誤: {e}")
    else:
        for date_str in dates_to_process:
            saved = process_with_progress(date_str)
            total_files_saved += saved

    print("\n" + "=" * 80)
    print("批次處理完成！")
    print(f"處理日期數: {len(dates_to_process)}")
    print(f"保存檔案數: {total_files_saved}")
    print(f"輸出目錄: {output_base_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
