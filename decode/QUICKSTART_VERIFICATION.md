# 验证脚本快速入门

## 一键验证（推荐）

```bash
conda activate my_project
cd C:\Users\tacor\Documents\_03_telegram

# 运行完整验证流程（自动运行 Python 和 Rust 解码器，并比较结果）
python decode/run_verification.py 20251119
```

## 分步验证

### 步骤 1: 测试 Python 解码器正确性
```bash
# 测试单行解析是否正确
python decode/test_single_line.py
```

**预期看到：**
- Trade 行解析正确（价格 = 原始值 / 10000）
- Depth 行解析正确（五档价格和数量）
- 时间戳格式正确

---

### 步骤 2: 生成 Python 基准输出
```bash
# 编辑 decode/test_decode.py，设置测试日期
# test_date = '20251119'

python decode/test_decode.py
```

**输出位置：**
```
data/decoded_quotes/20251119/*.parquet
```

---

### 步骤 3: 运行 Rust 解码器
```bash
cd decode/rust_decoder
cargo run --release -- 20251119
```

**输出位置：**
```
../../data/decoded_quotes/20251119/*.parquet
```

---

### 步骤 4: 验证输出一致性
```bash
cd ../..

# 验证单个股票
python decode/verify_rust_output.py 20251119 2330

# 验证所有股票
python decode/verify_rust_output.py 20251119
```

**成功标志：**
```
✓ 验证通过
✓ 所有验证通过！
```

---

## 验证检查清单

运行 Rust 解码器后，依次检查：

```bash
# 1. 单行解析测试
python decode/test_single_line.py

# 2. 验证单个股票
python decode/verify_rust_output.py 20251119 2330

# 3. 验证整个日期
python decode/verify_rust_output.py 20251119

# 4. 一键完整验证（可选）
python decode/run_verification.py 20251119
```

---

## 常用命令

```bash
# 查看 Python 输出
python -c "import pandas as pd; df = pd.read_parquet('data/decoded_quotes/20251119/2330.parquet'); print(df.head())"

# 查看 Rust 输出（假设输出到同一位置）
python -c "import pandas as pd; df = pd.read_parquet('data/decoded_quotes/20251119/2330.parquet'); print(df.info())"

# 比较两个文件
python decode/verify_rust_output.py 20251119 2330
```

---

## 故障排除

### 问题：验证失败

1. 检查错误信息中的具体不匹配点
2. 对比 Python 和 Rust 的解析逻辑
3. 运行 `test_single_line.py` 确认 Python 解析正确
4. 检查 Rust 代码中的数值计算（除以 10000）
5. 检查时间戳解析（12位补零）

### 问题：文件不存在

```bash
# 检查 Python 输出是否存在
ls -la data/decoded_quotes/20251119/

# 检查 Rust 输出是否存在
ls -la decode/rust_decoder/output/20251119/

# 检查源文件是否存在
ls -la C:/Users/tacor/Documents/tick-data/*Quote.20251119
```

### 问题：性能太慢

- Python 解码器：预期 30-60 秒/日期
- Rust 解码器：预期 1-3 秒/日期（10-30x 加速）

如果 Rust 慢于预期，检查：
1. 是否使用 `--release` 模式
2. 是否有不必要的 Debug 输出
3. 是否正确使用了并发处理

---

## 成功标准

验证通过的标准：

- [x] 行数完全一致
- [x] Trade 数量一致
- [x] Depth 数量一致
- [x] 所有价格字段在容差范围内（1e-6）
- [x] 所有整数字段精确匹配
- [x] 时间戳在微秒精度内一致
- [x] 空值位置完全一致
- [x] 性能提升明显（Rust 比 Python 快 10x+）

---

## 下一步

验证通过后：

1. 批量处理更多日期
2. 性能基准测试
3. 集成到主流程
4. 文档更新

```bash
# 批量验证多个日期
for date in 20251119 20251120 20251121; do
  echo "验证日期: $date"
  python decode/verify_rust_output.py $date
done
```
