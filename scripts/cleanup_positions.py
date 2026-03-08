#!/usr/bin/env python3
"""
清理持仓数据: 对齐 DB 与 Futu 实际持仓。

处理逻辑:
1. 从 Futu 获取当前真实持仓
2. DB 中不在 Futu 的持仓 → qty 设为 0
3. 同一 (account_id, code) 有多条记录 → 只保留最新 snapshot_date 的
4. 输出清理报告
"""

import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import and_, select

from db.database import get_session
from db.models import Account, Position
from fetchers import FutuFetcher


def main(dry_run: bool = True):
    print(f"{'[DRY RUN] ' if dry_run else ''}持仓数据清理")
    print("=" * 60)

    # Step 1: Get actual positions from Futu
    print("\n1. 从 Futu 获取当前真实持仓...")
    fetcher = FutuFetcher()
    fetcher.connect()

    futu_positions = {}  # {(account_id, code): PositionInfo}

    with get_session() as session:
        accounts = session.execute(select(Account).where(Account.is_active == True)).scalars().all()

        for account in accounts:
            if not account.futu_acc_id:
                continue
            result = fetcher.get_positions(acc_id=account.futu_acc_id)
            if result.success:
                for p in result.data:
                    if p.qty > 0:
                        futu_positions[(account.id, p.code)] = p
                print(f"   Account {account.account_name} ({account.futu_acc_id}): {len([p for p in result.data if p.qty > 0])} 持仓")
            else:
                print(f"   Account {account.account_name}: 获取失败 - {result.error_message}")

    fetcher.disconnect()

    futu_codes = {code for (_, code) in futu_positions.keys()}
    print(f"\n   Futu 实际持仓 codes: {sorted(futu_codes)}")

    # Step 2: Analyze DB positions
    print("\n2. 分析 DB 持仓数据...")
    with get_session() as session:
        all_positions = session.execute(
            select(Position).order_by(Position.account_id, Position.code, Position.snapshot_date)
        ).scalars().all()

        # Group by (account_id, code)
        groups = defaultdict(list)
        for p in all_positions:
            groups[(p.account_id, p.code)].append(p)

        stale_to_zero = []  # Positions to set qty=0
        duplicates_to_delete = []  # Duplicate snapshots to remove
        kept = []

        for (acc_id, code), positions in groups.items():
            in_futu = (acc_id, code) in futu_positions

            # Sort by snapshot_date desc (latest first)
            positions.sort(key=lambda p: p.snapshot_date or date.min, reverse=True)
            latest = positions[0]

            if in_futu:
                # Keep latest, mark older duplicates for deletion
                kept.append(latest)
                for dup in positions[1:]:
                    duplicates_to_delete.append(dup)
            else:
                # Not in Futu: set all to qty=0
                for p in positions:
                    if p.qty > 0:
                        stale_to_zero.append(p)
                    else:
                        duplicates_to_delete.append(p)

        # Report
        print(f"\n   DB 总记录数: {len(all_positions)}")
        print(f"   唯一 (account, code) 组合: {len(groups)}")
        print(f"   保留 (Futu 存在): {len(kept)}")
        print(f"   需设 qty=0 (已卖出): {len(stale_to_zero)}")
        print(f"   需删除 (重复快照): {len(duplicates_to_delete)}")

        if stale_to_zero:
            print(f"\n3. 已卖出持仓 (将 qty→0):")
            for p in stale_to_zero:
                print(f"   id={p.id:3d} | acc={p.account_id} | {p.code:25s} | {p.stock_name:20s} | qty={p.qty} | snap={p.snapshot_date}")

        if duplicates_to_delete:
            print(f"\n4. 重复快照 (将删除):")
            for p in duplicates_to_delete:
                print(f"   id={p.id:3d} | acc={p.account_id} | {p.code:25s} | snap={p.snapshot_date} | qty={p.qty}")

        if not dry_run:
            print(f"\n5. 执行清理...")

            # Set stale positions to qty=0
            for p in stale_to_zero:
                p.qty = 0
                p.can_sell_qty = 0
                p.market_val = 0
                p.pl_val = 0
            print(f"   已将 {len(stale_to_zero)} 条记录 qty 设为 0")

            # Delete duplicates
            for p in duplicates_to_delete:
                session.delete(p)
            print(f"   已删除 {len(duplicates_to_delete)} 条重复记录")

            session.commit()
            print(f"\n   ✅ 清理完成!")

            # Verify
            remaining = session.execute(
                select(Position).where(Position.qty > 0)
            ).scalars().all()
            print(f"\n6. 验证: DB 中 qty>0 的持仓 {len(remaining)} 条:")
            for p in remaining:
                print(f"   {p.code:25s} | {p.stock_name:20s} | qty={p.qty} | snap={p.snapshot_date}")
        else:
            print(f"\n[DRY RUN] 未执行任何修改。使用 --apply 参数执行清理。")


if __name__ == "__main__":
    dry_run = "--apply" not in sys.argv
    main(dry_run=dry_run)
