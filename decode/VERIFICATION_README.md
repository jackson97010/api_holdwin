# Rust 解码器验证指南

本文档说明如何验证 Rust 解码器的输出是否与 Python 解码器一致。

## 验证脚本概览

### 1. `test_single_line.py` - 单行解析测试
快速测试 Python 解码器对单行数据的解析是否正确。

**用途：**
- 验证 Trade 和 Depth 行的解析逻辑
- 测试时间戳转换
- 测试价格计算（除以 10000）
- 测试边界情况

**使用方法：**
```bash
conda activate my_project
python decode/test_single_line.py
```

**预期输出：**
```
[测试 1] Trade 格式
输入: Trade,2355  ,131219825776,0,333500,1,1530,1234
实际输出:
{
  "Type": "Trade",
  "StockCode": "2355",
  "Datetime": "2025-11-19 13:12:19.825776",
  "Timestamp": 131219825776,
  "Flag": 0,
  "Price": 33.35,
  "Volume": 1,
  "TotalVolume": 1530
}
```

---

### 2. `verify_rust_output.py` - 输出对比验证
比较 Python 和 Rust 解码器的输出，验证数据一致性。

**验证内容：**
- ✓ 数据行数是否相同
- ✓ 每个字段的数据类型是否一致
- ✓ Datetime 时间戳格式是否一致
- ✓ Trade 数据的价格、数量是否精确匹配
- ✓ Depth 数据的五档价格和数量是否精确匹配
- ✓ 空值（NaN）位置是否一致
- ✓ 浮点数精度比较（默认容差 1e-6）

**使用方法：**
```bash
# 验证整个日期的所有股票
python decode/verify_rust_output.py 20251119

# 验证特定股票
python decode/verify_rust_output.py 20251119 2330
```

**输出示例：**
```
验证报告: 2330
================================================================================

统计信息:
  Python 总行数: 1530
  Rust 总行数:   1530
  Python Trade:  500
  Rust Trade:    500
  Python Depth:  1030
  Rust Depth:    1030

结果: ✓ 验证通过

================================================================================
验证总结
================================================================================

验证股票数: 5
通过: 5
失败: 0

总计数据:
  Python 总行数: 7650
  Rust 总行数:   7650
  Python Trade:  2500
  Rust Trade:    2500
  Python Depth:  5150
  Rust Depth:    5150

✓ 所有验证通过！
```

---

### 3. `run_verification.py` - 完整验证流程
自动化运行完整的验证流程。

**流程步骤：**
1. 使用 Python 解码器生成基准输出
2. 使用 Rust 解码器生成输出
3. 自动比较两者的输出结果

**使用方法：**
```bash
# 验证整个日期
python decode/run_verification.py 20251119

# 验证特定股票
python decode/run_verification.py 20251119 2330
```

**注意：** 此脚本会自动执行以下命令：
- `python test_decode.py`（修改日期后）
- `cargo run --release -- 20251119`
- `python verify_rust_output.py 20251119`

---

## 验证流程详解

### 第一步：准备测试数据

确保以下文件存在：
```
C:\Users\tacor\Documents\tick-data\OTCQuote.20251119
C:\Users\tacor\Documents\tick-data\TSEQuote.20251119
C:\Users\tacor\Documents\_03_telegram\data\lup_ma20_filtered.parquet
```

### 第二步：生成 Python 基准输出

```bash
# 方法 1: 使用 test_decode.py（单个日期）
python decode/test_decode.py

# 方法 2: 使用 batch_decode_quotes.py（批量）
python decode/batch_decode_quotes.py
```

输出目录：
```
data/decoded_quotes/20251119/
├── 2330.parquet
├── 2355.parquet
└── ...
```

### 第三步：运行 Rust 解码器

```bash
cd decode/rust_decoder
cargo run --release -- 20251119
```

或指定股票：
```bash
cargo run --release -- 20251119 2330
```

### 第四步：验证输出一致性

```bash
python decode/verify_rust_output.py 20251119
```

---

## 验证指标说明

### 1. 行数验证
- Python 和 Rust 输出的总行数必须相同
- Trade 记录数必须相同
- Depth 记录数必须相同

### 2. 字段验证

#### 字符串字段（精确匹配）
- `Type`: "Trade" 或 "Depth"
- `StockCode`: 股票代码

#### 整数字段（精确匹配）
- `Timestamp`: 时间戳（12位整数）
- `Flag`: 试撮旗标（0 或 1）
- `Volume`: 成交单量
- `TotalVolume`: 累计成交量
- `BidCount`, `AskCount`: 买卖档数
- `Bid[1-5]_Volume`, `Ask[1-5]_Volume`: 各档委托量

#### 浮点数字段（容差匹配，默认 1e-6）
- `Price`: 成交价（除以 10000 后的结果）
- `Bid[1-5]_Price`, `Ask[1-5]_Price`: 各档价格（除以 10000 后）

#### 时间字段（微秒精度）
- `Datetime`: 完整时间戳（允许 1 微秒误差）

### 3. 空值验证
- 空值（NaN/None）的位置必须完全一致
- Trade 记录中的五档字段应为空
- Depth 记录中的 Price/Volume 字段应为空

---

## 常见问题处理

### 问题 1: 时间戳格式不一致

**症状：**
```
列 'Datetime' 有 100 处时间戳不匹配
  行 0: Python=2025-11-19 09:18:14.838927, Rust=2025-11-19 09:18:14.838926
```

**原因：** 微秒精度计算不一致

**解决：** 检查 Rust 代码中的时间戳解析逻辑，确保与 Python 相同：
```rust
// 正确的解析方式
let timestamp_str = format!("{:012}", timestamp); // 补零到12位
let datetime_str = format!("{}{}", date_str, timestamp_str);
```

### 问题 2: 价格计算错误

**症状：**
```
列 'Price' 有 50 处价格差异 > 1e-6
  行 0: Python=33.3500, Rust=333500.0000
```

**原因：** 忘记除以 10000

**解决：** 检查 Rust 代码中的价格计算：
```rust
// 正确的计算方式
let price = price_raw as f64 / 10000.0;
```

### 问题 3: 行数不一致

**症状：**
```
行数不一致: Python=1530, Rust=1525
```

**原因：**
- Rust 解析失败跳过了某些行
- 过滤逻辑不一致

**解决：**
1. 检查 Rust 的错误处理，确保不会静默跳过数据
2. 对比 Python 和 Rust 的股票过滤逻辑
3. 检查是否正确处理了 OTC 和 TSE 两个文件

### 问题 4: 五档数据不匹配

**症状：**
```
列 'Bid1_Price' 有 10 处值不匹配
  行 5: Python=33.30, Rust=None
```

**原因：**
- 五档解析逻辑错误
- BID/ASK 分隔符识别错误

**解决：**
1. 检查 BID: 和 ASK: 的位置识别
2. 确保正确处理档位不足 5 档的情况
3. 验证价格*数量的分割逻辑

---

## 性能基准

### Python 解码器
- 单日期（约 10 支股票）：~30-60 秒
- 批量处理（100+ 日期）：~30-60 分钟

### Rust 解码器（预期）
- 单日期（约 10 支股票）：~1-3 秒（10-30x 加速）
- 批量处理（100+ 日期）：~2-5 分钟（10-30x 加速）

---

## 验证检查清单

在 Rust 解码器完成后，按以下顺序验证：

- [ ] 1. 运行单行解析测试
  ```bash
  python decode/test_single_line.py
  ```

- [ ] 2. 手动生成 Python 基准输出
  ```bash
  python decode/test_decode.py
  ```

- [ ] 3. 运行 Rust 解码器
  ```bash
  cd decode/rust_decoder
  cargo run --release -- 20251119
  ```

- [ ] 4. 验证单个股票输出
  ```bash
  python decode/verify_rust_output.py 20251119 2330
  ```

- [ ] 5. 验证整个日期输出
  ```bash
  python decode/verify_rust_output.py 20251119
  ```

- [ ] 6. 运行完整自动化验证
  ```bash
  python decode/run_verification.py 20251119
  ```

- [ ] 7. 批量验证多个日期
  ```bash
  for date in 20251119 20251120 20251121; do
    python decode/verify_rust_output.py $date
  done
  ```

---

## 数据格式参考

### Trade 行格式
```
Trade,股票代码,成交时间,试撮旗标,成交价,成交单量,成交总量[,序号]
```

**示例：**
```
Trade,2355  ,131219825776,0,333500,1,1530,1234
```

**解析结果：**
- Type: "Trade"
- StockCode: "2355"
- Timestamp: 131219825776
- Flag: 0（一般揭示）
- Price: 33.35（333500 / 10000）
- Volume: 1
- TotalVolume: 1530

### Depth 行格式
```
Depth,股票代码,报价时间,BID:委买档数,买盘档位...,ASK:委卖档数,卖盘档位...[,序号]
```

**示例：**
```
Depth,2355  ,131219825776,BID:5,333000*27,332500*5,332000*32,331500*35,331000*62,ASK:5,333500*17,334000*5,334500*13,335000*44,335500*14,1234
```

**解析结果：**
- Type: "Depth"
- StockCode: "2355"
- Timestamp: 131219825776
- BidCount: 5
- AskCount: 5
- Bid1_Price: 33.30, Bid1_Volume: 27
- Bid2_Price: 33.25, Bid2_Volume: 5
- ...
- Ask1_Price: 33.35, Ask1_Volume: 17
- Ask2_Price: 33.40, Ask2_Volume: 5
- ...

---

## 输出 Schema

所有 Parquet 文件应包含以下列（按顺序）：

```
Type              : string (Trade/Depth)
StockCode         : string
Datetime          : datetime64[ns]
Timestamp         : int64
Flag              : int64 (nullable)
Price             : float64 (nullable)
Volume            : int64 (nullable)
TotalVolume       : int64 (nullable)
BidCount          : int64 (nullable)
AskCount          : int64 (nullable)
Bid1_Price        : float64 (nullable)
Bid1_Volume       : int64 (nullable)
Bid2_Price        : float64 (nullable)
Bid2_Volume       : int64 (nullable)
Bid3_Price        : float64 (nullable)
Bid3_Volume       : int64 (nullable)
Bid4_Price        : float64 (nullable)
Bid4_Volume       : int64 (nullable)
Bid5_Price        : float64 (nullable)
Bid5_Volume       : int64 (nullable)
Ask1_Price        : float64 (nullable)
Ask1_Volume       : int64 (nullable)
Ask2_Price        : float64 (nullable)
Ask2_Volume       : int64 (nullable)
Ask3_Price        : float64 (nullable)
Ask3_Volume       : int64 (nullable)
Ask4_Price        : float64 (nullable)
Ask4_Volume       : int64 (nullable)
Ask5_Price        : float64 (nullable)
Ask5_Volume       : int64 (nullable)
```

**空值规则：**
- Trade 记录：BidCount, AskCount, Bid[1-5]_*, Ask[1-5]_* 为 None
- Depth 记录：Flag, Price, Volume 为 None
- TotalVolume: Trade 有值，Depth 为 None

---

## 总结

验证脚本已准备就绪，等待 rust-engineer 完成 Rust 解码器的修复后即可运行验证。

关键验证点：
1. ✓ 数据完整性（行数、字段）
2. ✓ 数值精度（价格、数量、时间戳）
3. ✓ 数据类型一致性
4. ✓ 空值处理正确性
5. ✓ 性能提升显著（预期 10-30x）

如有任何不一致，验证脚本会详细列出差异点，便于快速定位和修复问题。
