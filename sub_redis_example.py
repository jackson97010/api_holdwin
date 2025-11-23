import redis
import time

#channel為股票代碼, 可以一次訂多檔
CHANNELS = ['2303', '2330', '2324', '1815']


def parse_trade(line: str):
    """
    解析成交
    收到： "Trade,1815  ,83005993712,1,334500,6,1000"
    解析： Trade,股票代碼,成交時間,試撮旗標,成交價,成交單量,成交總量
    """
    # 防呆處理
    if not line or not line.startswith("Trade"):
        return {}

    # 拆解欄位
    parts = [x.strip() for x in line.split(',')]
    if len(parts) < 7:
        return {}  # 欄位不足時回傳空 dict

    # 組成結果
    print(f"訊息種類: {parts[0]}")
    print(f"股票代碼: {parts[1].lstrip()}")
    print(f"成交時間: {parts[2]}")
    print(f"試撮旗標: {parts[3]}")
    print(f"成交價:   {int(parts[4]) / 10000}")
    print(f"成交單量: {parts[5]}")
    print(f"成交總量: {parts[6]}")

def parse_depth(line: str):
    """
    解析五檔
    收到： Depth,2355  ,131219825776,BID:5,333000*27,332500*5,332000*32,331500*35,331000*62,ASK:5,333500*17,334000*5,334500*13,335000*44,335500*14
    解析：Depth,股票代碼,報價時間,BID:委買檔數,第1檔價格*數量,第2檔價格*數量,第3檔價格*數量,第4檔價格*數量,第5檔價格*數量,
            ASK:委賣檔數,第1檔價格*數量,第2檔價格*數量,第3檔價格*數量,第4檔價格*數量,第5檔價格*數量
    """
    # 防呆處理
    if not line or not line.startswith("Depth"):
        return {}

    # 拆解欄位
    parts = [x.strip() for x in line.split(',')]
    if len(parts) < 7:
        return {}  # 欄位不足時回傳空 dict

    print(f"訊息種類: {parts[0]}")
    print(f"股票代碼: {parts[1].lstrip()}")
    print(f"成交時間: {parts[2]}")

    bid_idx=0
    ask_idx = 0
    # 找出 BID/ASK 區段
    side = None
    for part in parts[3:]:
        if part.startswith("BID:"):
            side = "BID"            
            bid_count = part.split(":")[1]
            print(f"委買檔數: {bid_count}")
        elif part.startswith("ASK:"):
            side = "ASK"
            ask_count = part.split(":")[1]
            print(f"委買檔數: {ask_count}")
        else:
            # 處理價格*數量
            price = int(part.split("*")[0]) / 10000;
            qty = part.split("*")[1]
            if side == "BID":
                print(f"BID[{bid_idx}] 價格:{price} 數量:{qty}")
                bid_idx+=1
            elif side == "ASK":
                print(f"ASK[{ask_idx}] 價格:{price} 數量:{qty}")
                ask_idx+=1
                
def subscribe_and_listen():
    while True:
        try:
            print("Connecting to Redis server...")
            r = redis.Redis(host='192.168.100.130', port=6379, db=0, socket_timeout=5)
            p = r.pubsub(ignore_subscribe_messages=True)
            p.subscribe(CHANNELS)

            print(f"Subscribed to channels: {', '.join(CHANNELS)}")
            for message in p.listen():
                # message 格式: {'type': 'message', 'pattern': None, 'channel': b'quote', 'data': b'xxxx'}
                ch = message['channel'].decode('utf-8')
                data = message['data'].decode('utf-8')
                print(f"channel:[{ch}] data[{data}]")

                # 1️⃣ 先用逗號分割
                if data.startswith("Trade"): parse_trade(data)
                if data.startswith("Depth"): parse_depth(data)


        except redis.exceptions.ConnectionError:
            print("⚠️ Redis connection lost, retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    subscribe_and_listen()
