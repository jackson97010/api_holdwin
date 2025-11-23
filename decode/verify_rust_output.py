"""
验证 Rust 解码器输出与 Python 解码器输出的一致性

功能：
1. 读取同一个 Quote 文件，分别用 Python 和 Rust 解码器处理
2. 对比两者输出的 Parquet 文件
3. 验证所有字段的值是否一致
4. 输出详细的验证报告

使用方法：
    python verify_rust_output.py [日期] [股票代码]
    python verify_rust_output.py 20251119      # 验证整个日期
    python verify_rust_output.py 20251119 2330 # 验证特定股票
"""

import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime


class ColorPrint:
    """终端彩色输出"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

    @staticmethod
    def success(text: str) -> str:
        return f"{ColorPrint.GREEN}{text}{ColorPrint.END}"

    @staticmethod
    def error(text: str) -> str:
        return f"{ColorPrint.RED}{text}{ColorPrint.END}"

    @staticmethod
    def warning(text: str) -> str:
        return f"{ColorPrint.YELLOW}{text}{ColorPrint.END}"

    @staticmethod
    def info(text: str) -> str:
        return f"{ColorPrint.BLUE}{text}{ColorPrint.END}"

    @staticmethod
    def bold(text: str) -> str:
        return f"{ColorPrint.BOLD}{text}{ColorPrint.END}"


class VerificationResult:
    """验证结果"""
    def __init__(self, stock_code: str):
        self.stock_code = stock_code
        self.success = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats = {
            'python_rows': 0,
            'rust_rows': 0,
            'python_trade': 0,
            'rust_trade': 0,
            'python_depth': 0,
            'rust_depth': 0,
        }

    def add_error(self, message: str):
        """添加错误"""
        self.success = False
        self.errors.append(message)

    def add_warning(self, message: str):
        """添加警告"""
        self.warnings.append(message)

    def print_report(self):
        """打印验证报告"""
        print(f"\n{'='*80}")
        print(f"验证报告: {self.stock_code}")
        print(f"{'='*80}")

        # 统计信息
        print(f"\n统计信息:")
        print(f"  Python 总行数: {self.stats['python_rows']}")
        print(f"  Rust 总行数:   {self.stats['rust_rows']}")
        print(f"  Python Trade:  {self.stats['python_trade']}")
        print(f"  Rust Trade:    {self.stats['rust_trade']}")
        print(f"  Python Depth:  {self.stats['python_depth']}")
        print(f"  Rust Depth:    {self.stats['rust_depth']}")

        # 警告
        if self.warnings:
            print(f"\n{ColorPrint.warning('警告:')}")
            for warning in self.warnings:
                print(f"  - {warning}")

        # 错误
        if self.errors:
            print(f"\n{ColorPrint.error('错误:')}")
            for error in self.errors:
                print(f"  - {error}")

        # 结果
        print(f"\n结果: ", end="")
        if self.success:
            print(ColorPrint.success("✓ 验证通过"))
        else:
            print(ColorPrint.error("✗ 验证失败"))

        print(f"{'='*80}")


def compare_dataframes(
    df_python: pd.DataFrame,
    df_rust: pd.DataFrame,
    stock_code: str,
    tolerance: float = 1e-6
) -> VerificationResult:
    """
    比较两个 DataFrame 是否一致

    Args:
        df_python: Python 解码器输出
        df_rust: Rust 解码器输出
        stock_code: 股票代码
        tolerance: 浮点数比较容差

    Returns:
        验证结果对象
    """
    result = VerificationResult(stock_code)

    # 基本统计
    result.stats['python_rows'] = len(df_python)
    result.stats['rust_rows'] = len(df_rust)
    result.stats['python_trade'] = len(df_python[df_python['Type'] == 'Trade'])
    result.stats['rust_trade'] = len(df_rust[df_rust['Type'] == 'Trade'])
    result.stats['python_depth'] = len(df_python[df_python['Type'] == 'Depth'])
    result.stats['rust_depth'] = len(df_rust[df_rust['Type'] == 'Depth'])

    # 1. 检查行数
    if len(df_python) != len(df_rust):
        result.add_error(
            f"行数不一致: Python={len(df_python)}, Rust={len(df_rust)}"
        )
        return result

    if len(df_python) == 0:
        result.add_warning("两个文件都为空")
        return result

    # 2. 检查列名
    python_cols = set(df_python.columns)
    rust_cols = set(df_rust.columns)

    missing_in_rust = python_cols - rust_cols
    extra_in_rust = rust_cols - python_cols

    if missing_in_rust:
        result.add_error(f"Rust 缺少列: {missing_in_rust}")

    if extra_in_rust:
        result.add_warning(f"Rust 多余列: {extra_in_rust}")

    # 使用共同列进行比较
    common_cols = python_cols & rust_cols

    # 3. 对齐数据 - 按 Timestamp 排序
    if 'Timestamp' in common_cols:
        df_python = df_python.sort_values('Timestamp').reset_index(drop=True)
        df_rust = df_rust.sort_values('Timestamp').reset_index(drop=True)

    # 4. 逐列比较
    for col in sorted(common_cols):
        col_python = df_python[col]
        col_rust = df_rust[col]

        # 字符串类型比较
        if col in ['Type', 'StockCode']:
            mismatch = col_python != col_rust
            if mismatch.any():
                mismatch_count = mismatch.sum()
                result.add_error(
                    f"列 '{col}' 有 {mismatch_count} 处不匹配"
                )
                # 显示前几个不匹配的例子
                mismatch_indices = mismatch[mismatch].index[:3]
                for idx in mismatch_indices:
                    result.add_error(
                        f"  行 {idx}: Python='{col_python.iloc[idx]}', "
                        f"Rust='{col_rust.iloc[idx]}'"
                    )

        # Datetime 比较
        elif col == 'Datetime':
            # 转换为 datetime 类型
            try:
                dt_python = pd.to_datetime(col_python)
                dt_rust = pd.to_datetime(col_rust)

                # 检查是否有不匹配
                # 允许微秒级误差
                time_diff = (dt_python - dt_rust).abs()
                significant_diff = time_diff > pd.Timedelta(microseconds=1)

                if significant_diff.any():
                    mismatch_count = significant_diff.sum()
                    result.add_error(
                        f"列 'Datetime' 有 {mismatch_count} 处时间戳不匹配"
                    )
                    # 显示前几个例子
                    mismatch_indices = significant_diff[significant_diff].index[:3]
                    for idx in mismatch_indices:
                        result.add_error(
                            f"  行 {idx}: Python={dt_python.iloc[idx]}, "
                            f"Rust={dt_rust.iloc[idx]}, "
                            f"diff={time_diff.iloc[idx]}"
                        )
            except Exception as e:
                result.add_error(f"Datetime 比较失败: {e}")

        # 整数类型比较
        elif col in ['Timestamp', 'Flag', 'Volume', 'TotalVolume',
                     'BidCount', 'AskCount'] or \
             '_Volume' in col:
            # 处理 NaN
            python_notna = col_python.notna()
            rust_notna = col_rust.notna()

            # 检查 NaN 位置是否一致
            if not (python_notna == rust_notna).all():
                diff_count = (python_notna != rust_notna).sum()
                result.add_error(
                    f"列 '{col}' 的空值位置不一致 ({diff_count} 处)"
                )

            # 比较非 NaN 值
            both_notna = python_notna & rust_notna
            if both_notna.any():
                python_vals = col_python[both_notna].astype('Int64')
                rust_vals = col_rust[both_notna].astype('Int64')

                mismatch = python_vals != rust_vals
                if mismatch.any():
                    mismatch_count = mismatch.sum()
                    result.add_error(
                        f"列 '{col}' 有 {mismatch_count} 处值不匹配"
                    )
                    # 显示前几个例子
                    mismatch_indices = both_notna[both_notna].index[mismatch][:3]
                    for idx in mismatch_indices:
                        result.add_error(
                            f"  行 {idx}: Python={col_python.iloc[idx]}, "
                            f"Rust={col_rust.iloc[idx]}"
                        )

        # 浮点数类型比较（价格）
        elif col == 'Price' or '_Price' in col:
            # 处理 NaN
            python_notna = col_python.notna()
            rust_notna = col_rust.notna()

            # 检查 NaN 位置是否一致
            if not (python_notna == rust_notna).all():
                diff_count = (python_notna != rust_notna).sum()
                result.add_error(
                    f"列 '{col}' 的空值位置不一致 ({diff_count} 处)"
                )

            # 比较非 NaN 值（使用容差）
            both_notna = python_notna & rust_notna
            if both_notna.any():
                python_vals = col_python[both_notna].astype(float)
                rust_vals = col_rust[both_notna].astype(float)

                diff = np.abs(python_vals - rust_vals)
                significant_diff = diff > tolerance

                if significant_diff.any():
                    mismatch_count = significant_diff.sum()
                    result.add_error(
                        f"列 '{col}' 有 {mismatch_count} 处价格差异 > {tolerance}"
                    )
                    # 显示前几个例子
                    mismatch_indices = both_notna[both_notna].index[significant_diff][:3]
                    for idx in mismatch_indices:
                        result.add_error(
                            f"  行 {idx}: Python={col_python.iloc[idx]:.4f}, "
                            f"Rust={col_rust.iloc[idx]:.4f}, "
                            f"diff={diff.iloc[mismatch_indices.get_loc(idx)]:.8f}"
                        )

    return result


def verify_stock(
    stock_code: str,
    date_str: str,
    python_dir: Path,
    rust_dir: Path
) -> Optional[VerificationResult]:
    """
    验证单个股票的输出

    Args:
        stock_code: 股票代码
        date_str: 日期字符串 (YYYYMMDD)
        python_dir: Python 输出目录
        rust_dir: Rust 输出目录

    Returns:
        验证结果，如果文件不存在返回 None
    """
    python_file = python_dir / date_str / f"{stock_code}.parquet"
    rust_file = rust_dir / date_str / f"{stock_code}.parquet"

    # 检查文件是否存在
    if not python_file.exists() and not rust_file.exists():
        return None

    result = VerificationResult(stock_code)

    if not python_file.exists():
        result.add_error(f"Python 输出文件不存在: {python_file}")
        return result

    if not rust_file.exists():
        result.add_error(f"Rust 输出文件不存在: {rust_file}")
        return result

    try:
        # 读取 Parquet 文件
        df_python = pd.read_parquet(python_file)
        df_rust = pd.read_parquet(rust_file)

        # 比较数据
        result = compare_dataframes(df_python, df_rust, stock_code)

    except Exception as e:
        result.add_error(f"读取或比较文件时出错: {e}")

    return result


def verify_date(
    date_str: str,
    python_dir: Path,
    rust_dir: Path,
    stock_filter: Optional[str] = None
) -> List[VerificationResult]:
    """
    验证某个日期的所有股票

    Args:
        date_str: 日期字符串 (YYYYMMDD)
        python_dir: Python 输出目录
        rust_dir: Rust 输出目录
        stock_filter: 可选的股票代码过滤

    Returns:
        验证结果列表
    """
    results = []

    python_date_dir = python_dir / date_str
    rust_date_dir = rust_dir / date_str

    if not python_date_dir.exists() and not rust_date_dir.exists():
        print(ColorPrint.error(f"日期目录不存在: {date_str}"))
        return results

    # 收集所有股票代码
    stock_codes = set()

    if python_date_dir.exists():
        for file in python_date_dir.glob("*.parquet"):
            stock_codes.add(file.stem)

    if rust_date_dir.exists():
        for file in rust_date_dir.glob("*.parquet"):
            stock_codes.add(file.stem)

    # 过滤股票
    if stock_filter:
        stock_codes = {stock_filter} if stock_filter in stock_codes else set()

    stock_codes = sorted(stock_codes)

    print(f"\n{ColorPrint.info(f'找到 {len(stock_codes)} 支股票需要验证')}")

    # 逐个验证
    for i, stock_code in enumerate(stock_codes, 1):
        print(f"\n[{i}/{len(stock_codes)}] 验证 {stock_code}...", end=" ")

        result = verify_stock(stock_code, date_str, python_dir, rust_dir)

        if result is None:
            print(ColorPrint.warning("跳过 (文件不存在)"))
            continue

        if result.success:
            print(ColorPrint.success("✓"))
        else:
            print(ColorPrint.error("✗"))
            result.print_report()

        results.append(result)

    return results


def print_summary(results: List[VerificationResult]):
    """打印总结报告"""
    if not results:
        print(ColorPrint.warning("\n没有验证结果"))
        return

    total = len(results)
    success = sum(1 for r in results if r.success)
    failed = total - success

    total_python_rows = sum(r.stats['python_rows'] for r in results)
    total_rust_rows = sum(r.stats['rust_rows'] for r in results)
    total_python_trade = sum(r.stats['python_trade'] for r in results)
    total_rust_trade = sum(r.stats['rust_trade'] for r in results)
    total_python_depth = sum(r.stats['python_depth'] for r in results)
    total_rust_depth = sum(r.stats['rust_depth'] for r in results)

    print(f"\n{'='*80}")
    print(ColorPrint.bold("验证总结"))
    print(f"{'='*80}")
    print(f"\n验证股票数: {total}")
    print(f"通过: {ColorPrint.success(str(success))}")
    print(f"失败: {ColorPrint.error(str(failed)) if failed > 0 else '0'}")
    print(f"\n总计数据:")
    print(f"  Python 总行数: {total_python_rows}")
    print(f"  Rust 总行数:   {total_rust_rows}")
    print(f"  Python Trade:  {total_python_trade}")
    print(f"  Rust Trade:    {total_rust_trade}")
    print(f"  Python Depth:  {total_python_depth}")
    print(f"  Rust Depth:    {total_rust_depth}")

    if failed > 0:
        print(f"\n{ColorPrint.error('失败的股票:')}")
        for result in results:
            if not result.success:
                print(f"  - {result.stock_code} ({len(result.errors)} 个错误)")

    print(f"\n{'='*80}")

    if success == total:
        print(ColorPrint.success("✓ 所有验证通过！"))
    else:
        print(ColorPrint.error(f"✗ {failed}/{total} 个验证失败"))

    print(f"{'='*80}")


def main():
    """主程序"""
    import io

    # Windows 控制台编码修复
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print(f"\n{'='*80}")
    print(ColorPrint.bold("Rust 解码器输出验证工具"))
    print(f"{'='*80}")

    # 路径配置
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / 'data'

    python_output_dir = data_dir / 'decoded_quotes'
    rust_output_dir = data_dir / 'decoded_quotes'  # Rust 也输出到同一目录

    # 解析命令行参数
    if len(sys.argv) < 2:
        print(ColorPrint.error("\n错误: 缺少日期参数"))
        print("\n使用方法:")
        print("  python verify_rust_output.py <日期> [股票代码]")
        print("\n示例:")
        print("  python verify_rust_output.py 20251119")
        print("  python verify_rust_output.py 20251119 2330")
        sys.exit(1)

    date_str = sys.argv[1]
    stock_filter = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"\n配置:")
    print(f"  日期: {date_str}")
    print(f"  股票过滤: {stock_filter if stock_filter else '无 (全部)'}")
    print(f"  Python 输出: {python_output_dir}")
    print(f"  Rust 输出:   {rust_output_dir}")

    # 执行验证
    results = verify_date(date_str, python_output_dir, rust_output_dir, stock_filter)

    # 打印总结
    print_summary(results)


if __name__ == "__main__":
    main()
