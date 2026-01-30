"""
更新港股期权合约乘数

基于 HKEX 官方数据更新 derivative_contracts 表中的合约乘数
数据来源: https://www.hkex.com.hk/Products/Listed-Derivatives/Single-Stock/Stock-Options

用法:
    python scripts/update_hk_option_multipliers.py
"""
import sys
from decimal import Decimal
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.hk_option_multipliers import HK_OPTION_MULTIPLIERS
from db import DerivativeContract, get_session


def update_hk_option_multipliers():
    """更新港股期权合约乘数"""

    with get_session() as session:
        # 获取所有港股期权
        contracts = (
            session.query(DerivativeContract)
            .filter(
                DerivativeContract.market == "HK",
                DerivativeContract.contract_type == "OPTION",
            )
            .all()
        )

        print(f"港股期权合约数量: {len(contracts)}")
        print()
        print(f"{'期权代码':<22} {'前缀':<6} {'旧乘数':<10} {'新乘数':<10} {'状态':<8}")
        print("-" * 65)

        updated = 0
        unknown = 0

        for c in contracts:
            # 提取 HKATS 代码前缀
            prefix = ""
            for char in c.code:
                if char.isalpha():
                    prefix += char
                else:
                    break
            prefix = prefix.upper()

            old_multiplier = float(c.contract_multiplier)

            if prefix in HK_OPTION_MULTIPLIERS:
                new_multiplier = HK_OPTION_MULTIPLIERS[prefix]
                if old_multiplier != new_multiplier:
                    c.contract_multiplier = Decimal(str(new_multiplier))
                    c.data_source = "HKEX_OFFICIAL"
                    status = "已更新"
                    updated += 1
                else:
                    status = "无变化"
            else:
                status = "未知前缀"
                unknown += 1
                new_multiplier = old_multiplier

            print(f"{c.code:<22} {prefix:<6} {old_multiplier:<10.0f} {new_multiplier:<10.0f} {status}")

        session.commit()
        print()
        print(f"更新完成: {updated} 个已更新, {unknown} 个未知前缀")


def show_multiplier_config():
    """显示当前配置的合约乘数"""
    print("当前港股期权合约乘数配置:")
    print()
    print(f"{'HKATS代码':<10} {'合约乘数':<10}")
    print("-" * 25)
    for code, multiplier in sorted(HK_OPTION_MULTIPLIERS.items()):
        print(f"{code:<10} {multiplier:<10}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="更新港股期权合约乘数")
    parser.add_argument("--show", action="store_true", help="显示当前配置")
    args = parser.parse_args()

    if args.show:
        show_multiplier_config()
    else:
        update_hk_option_multipliers()
