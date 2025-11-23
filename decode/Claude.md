# 行情報價解碼專案

由於行情封包資料太多，你在解碼的時候就是去下面這兩個比方把上市股票還有上櫃股票的報價拿出來，那解行情的方式就透過 @batch_decode_quotes.py來處理就好。
'''
C:\Users\tacor\Documents\tick-data\{OTC}Quote.{y-m-d}
C:\Users\tacor\Documents\tick-data\{TSE}Quote.{y-m-d}
'''

同時我們要的檔案就是在'lup_ma20_filtered.parquet'中有出現的漲停個股，包括今日漲停的個股還有昨日漲停個股的走勢。

此為'lup_ma20_filtered.parquet'的資料格式。
{"date":1584662400000,"stock_id":"1101","close_price":36.95,"limit_up_price":36.95}

舉例來說：
2020-01-02 漲停個股有 2201、2330。
2020-01-03 漲停個股有 2345。
那我們在解OTCQuote.20200103的資料時候就會出現2345、2201、2330的資料。

那資料解完之後需要將它存在 ../data/{Y-M-D}/{stock-id}.paruqet，其中因為用python解太慢，所以我希望可以改使用rust來解。



## tick 資料範例
參考下面的說明，把資料輸出成parquet。

五檔報價：
{"Type":"Depth","StockCode":"1503","Datetime":1761902294838.927,"Timestamp":91814838927,"Flag":null,"Price":null,"Volume":null,"TotalVolume":null,"BidCount":5,"AskCount":5,"Bid1_Price":193,"Bid1_Volume":60,"Bid2_Price":192.5,"Bid2_Volume":48,"Bid3_Price":192,"Bid3_Volume":59,"Bid4_Price":191.5,"Bid4_Volume":60,"Bid5_Price":191,"Bid5_Volume":27,"Ask1_Price":193.5,"Ask1_Volume":26,"Ask2_Price":194,"Ask2_Volume":40,"Ask3_Price":194.5,"Ask3_Volume":9,"Ask4_Price":195,"Ask4_Volume":145,"Ask5_Price":195.5,"Ask5_Volume":6}
成交明細：
{"Type":"Trade","StockCode":"1503","Datetime":1761902294907.5361,"Timestamp":91814907536,"Flag":0,"Price":193.5,"Volume":1,"TotalVolume":3553,"BidCount":null,"AskCount":null,"Bid1_Price":null,"Bid1_Volume":null,"Bid2_Price":null,"Bid2_Volume":null,"Bid3_Price":null,"Bid3_Volume":null,"Bid4_Price":null,"Bid4_Volume":null,"Bid5_Price":null,"Bid5_Volume":null,"Ask1_Price":null,"Ask1_Volume":null,"Ask2_Price":null,"Ask2_Volume":null,"Ask3_Price":null,"Ask3_Volume":null,"Ask4_Price":null,"Ask4_Volume":null,"Ask5_Price":null,"Ask5_Volume":null}
欄位說明：
Type: 資料類型，Depth 為五檔報價，Trade 為成交明細。
StockCode: 股票代碼。
Datetime: 資料發生的時間戳記。
Timestamp: 資料發生的時間戳記。
Flag: 在Trade 為0 (盤前試搓)、Trade為1(盤中交易)； Depth 為null。
Price: 成交價。
Volume: 單筆成交量 。在 Depth 資料中為 null。
TotalVolume: 累計成交量。
BidCount: 最佳五檔買進委託檔數 (僅在 Depth 資料中出現)。
AskCount: 最佳五檔賣出委託檔數 (僅在 Depth 資料中出現)。
Bid[1-5]_Price: 第1到第5檔最佳買進價格 (僅在 Depth 資料中出現)。
Bid[1-5]_Volume: 第1到第5檔最佳買進委託量 (僅在 Depth 資料中出現)。
Ask[1-5]_Price: 第1到第5檔最佳賣出價格 (僅在 Depth 資料中出現)。
Ask[1-5]_Volume: 第1到第5檔最佳賣出委託量 (僅在 Depth 資料中出現)。

## 備註：
使用conda，在虛擬環境中執行python 程式碼。　
```
conda activate my_project
```
如有需要可以使用agents，來讓任務分工更加完善。

## 總結
需要有測試還有驗證，rust解出來的資料和我上面在資料範例說明的一樣。