"""
运行完整验证流程

流程:
1. 使用 Python 解码器生成基准输出
2. 使用 Rust 解码器生成输出
3. 比较两者的输出结果

使用方法:
    python run_verification.py <日期> [股票代码]
    python run_verification.py 20251119
    python run_verification.py 20251119 2330
"""

import subprocess
import sys
import os
from pathlib import Path
import shutil


def print_section(title: str):
    """打印分节标题"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def run_python_decoder(date_str: str, data_dir: Path) -> bool:
    """
    运行 Python 解码器生成基准输出

    Args:
        date_str: 日期字符串 (YYYYMMDD)
        data_dir: 数据目录

    Returns:
        是否成功
    """
    print_section(f"步骤 1: 运行 Python 解码器 (日期: {date_str})")

    # 修改 test_decode.py 以使用指定日期
    script_dir = Path(__file__).parent
    test_decode_path = script_dir / 'test_decode.py'

    if not test_decode_path.exists():
        print(f"错误: 找不到 test_decode.py")
        return False

    # 读取文件
    with open(test_decode_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换测试日期
    import re
    modified_content = re.sub(
        r"test_date = '\d{8}'",
        f"test_date = '{date_str}'",
        content
    )

    # 写入临时文件
    temp_file = script_dir / 'temp_decode.py'
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(modified_content)

    try:
        # 运行 Python 解码器
        print("执行 Python 解码器...")
        result = subprocess.run(
            [sys.executable, str(temp_file)],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        print(result.stdout)

        if result.returncode != 0:
            print(f"Python 解码器执行失败:")
            print(result.stderr)
            return False

        print("✓ Python 解码器执行成功")
        return True

    finally:
        # 清理临时文件
        if temp_file.exists():
            temp_file.unlink()


def run_rust_decoder(date_str: str, stock_filter: str = None) -> bool:
    """
    运行 Rust 解码器

    Args:
        date_str: 日期字符串 (YYYYMMDD)
        stock_filter: 可选的股票代码过滤

    Returns:
        是否成功
    """
    print_section(f"步骤 2: 运行 Rust 解码器 (日期: {date_str})")

    script_dir = Path(__file__).parent
    rust_dir = script_dir / 'rust_decoder'

    if not rust_dir.exists():
        print(f"错误: 找不到 rust_decoder 目录")
        return False

    # 构建命令
    cmd = ['cargo', 'run', '--release', '--', date_str]
    if stock_filter:
        cmd.append(stock_filter)

    print(f"执行命令: {' '.join(cmd)}")
    print(f"工作目录: {rust_dir}")

    try:
        # 运行 Rust 解码器
        result = subprocess.run(
            cmd,
            cwd=rust_dir,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        print(result.stdout)

        if result.returncode != 0:
            print(f"Rust 解码器执行失败:")
            print(result.stderr)
            return False

        print("✓ Rust 解码器执行成功")
        return True

    except FileNotFoundError:
        print("错误: 找不到 cargo 命令，请确保已安装 Rust")
        return False


def run_verification(date_str: str, stock_filter: str = None) -> bool:
    """
    运行验证脚本

    Args:
        date_str: 日期字符串 (YYYYMMDD)
        stock_filter: 可选的股票代码过滤

    Returns:
        是否成功
    """
    print_section(f"步骤 3: 验证输出一致性")

    script_dir = Path(__file__).parent
    verify_script = script_dir / 'verify_rust_output.py'

    if not verify_script.exists():
        print(f"错误: 找不到 verify_rust_output.py")
        return False

    # 构建命令
    cmd = [sys.executable, str(verify_script), date_str]
    if stock_filter:
        cmd.append(stock_filter)

    print(f"执行命令: {' '.join(cmd)}")

    try:
        # 运行验证脚本
        result = subprocess.run(
            cmd,
            capture_output=False,  # 直接显示输出
            text=True
        )

        return result.returncode == 0

    except Exception as e:
        print(f"验证脚本执行失败: {e}")
        return False


def main():
    """主程序"""
    import io

    # Windows 控制台编码修复
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print(f"\n{'='*80}")
    print(f"  Rust 解码器完整验证流程")
    print(f"{'='*80}")

    # 解析命令行参数
    if len(sys.argv) < 2:
        print("\n错误: 缺少日期参数")
        print("\n使用方法:")
        print("  python run_verification.py <日期> [股票代码]")
        print("\n示例:")
        print("  python run_verification.py 20251119")
        print("  python run_verification.py 20251119 2330")
        sys.exit(1)

    date_str = sys.argv[1]
    stock_filter = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"\n配置:")
    print(f"  日期: {date_str}")
    print(f"  股票过滤: {stock_filter if stock_filter else '无 (全部)'}")

    # 数据目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / 'data'

    # 步骤 1: Python 解码器
    if not run_python_decoder(date_str, data_dir):
        print("\n✗ 验证流程失败: Python 解码器执行失败")
        sys.exit(1)

    # 步骤 2: Rust 解码器
    if not run_rust_decoder(date_str, stock_filter):
        print("\n✗ 验证流程失败: Rust 解码器执行失败")
        sys.exit(1)

    # 步骤 3: 验证
    if not run_verification(date_str, stock_filter):
        print("\n✗ 验证流程失败: 输出不一致")
        sys.exit(1)

    # 完成
    print(f"\n{'='*80}")
    print("✓ 验证流程完成！")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
