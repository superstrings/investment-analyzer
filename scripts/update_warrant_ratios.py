"""
从 Futu API 更新港股窝轮换股比率
通过正股代码查询窝轮列表，按 strike_price 和 maturity_time 匹配
"""
import time
from datetime import date, datetime
from decimal import Decimal

from futu import OpenQuoteContext, RET_OK, SecurityType, Market

from db import get_session, DerivativeContract


def update_warrant_ratios():
    """更新港股窝轮换股比率"""

    today = date.today()

    # 1. 获取未过期的港股窝轮
    with get_session() as session:
        warrants = session.query(DerivativeContract).filter(
            DerivativeContract.market == "HK",
            DerivativeContract.contract_type == "WARRANT",
            DerivativeContract.expiry_date >= today
        ).all()

        # 构建 {(正股, strike, expiry, type): 合约} 映射
        warrant_list = []
        for w in warrants:
            warrant_list.append({
                'code': w.code,
                'strike': float(w.strike_price) if w.strike_price else 0,
                'expiry': w.expiry_date,
                'opt_type': w.option_type,
                'current_ratio': w.conversion_ratio,
                'underlying': w.underlying_code,
            })
        print(f"找到 {len(warrant_list)} 个未过期的港股窝轮")

    if not warrant_list:
        print("没有需要更新的窝轮")
        return

    # 2. 获取窝轮的正股代码
    ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

    try:
        ret, data = ctx.get_global_state()
        if ret != RET_OK:
            print(f"连接失败: {data}")
            return
        print(f"连接成功，市场状态: {data.get('market_hk', 'unknown')}")

        # 3. 获取窝轮的基本信息
        warrant_codes = [f"HK.{w['code']}" for w in warrant_list]
        ret, basicinfo = ctx.get_stock_basicinfo(
            Market.HK, SecurityType.WARRANT, code_list=warrant_codes
        )

        if ret != RET_OK:
            print(f"获取基本信息失败: {basicinfo}")
            return

        # 建立正股映射
        code_to_owner = {}
        for _, row in basicinfo.iterrows():
            code = row['code'].replace('HK.', '')
            owner = row.get('stock_owner', '')
            if owner:
                code_to_owner[code] = owner

        # 获取唯一的正股列表
        owners = list(set(code_to_owner.values()))
        print(f"涉及 {len(owners)} 个正股")

        # 4. 查询每个正股的窝轮列表
        all_warrants = []
        for owner in owners:
            print(f"\n查询 {owner} 的窝轮...")
            ret, result = ctx.get_warrant(stock_owner=owner)
            if ret != RET_OK:
                print(f"  获取失败")
                continue

            df, has_next, total = result
            print(f"  找到 {total} 个窝轮")

            for _, row in df.iterrows():
                # 解析到期日
                maturity = row.get('maturity_time', '')
                try:
                    expiry_date = datetime.strptime(maturity, '%Y-%m-%d').date() if maturity else None
                except:
                    expiry_date = None

                all_warrants.append({
                    'owner': owner,
                    'strike': float(row.get('strike_price', 0)),
                    'expiry': expiry_date,
                    'opt_type': 'CALL' if row.get('type') == 'CALL' else 'PUT',
                    'ratio': float(row.get('conversion_ratio', 0)),
                    'futu_code': row.get('stock', ''),
                    'name': row.get('name', ''),
                })

            time.sleep(0.3)

        print(f"\n共获取 {len(all_warrants)} 个窝轮信息")

        # 5. 匹配并更新
        updated = 0
        not_found = 0

        with get_session() as session:
            for w in warrant_list:
                owner = code_to_owner.get(w['code'], '')

                # 查找匹配的窝轮 (按正股、strike、expiry、type 匹配)
                matched = None
                candidates = []
                for aw in all_warrants:
                    if aw['owner'] != owner:
                        continue
                    # strike 允许 5% 误差
                    strike_diff = abs(aw['strike'] - w['strike']) / max(w['strike'], 1)
                    if strike_diff > 0.05:
                        continue
                    # expiry 允许 14 天误差
                    if aw['expiry'] and w['expiry']:
                        day_diff = abs((aw['expiry'] - w['expiry']).days)
                        if day_diff > 14:
                            continue
                    # type 必须匹配
                    if aw['opt_type'] != w['opt_type']:
                        continue
                    candidates.append((day_diff if aw['expiry'] and w['expiry'] else 999, aw))

                # 选择最接近的
                if candidates:
                    candidates.sort(key=lambda x: x[0])
                    matched = candidates[0][1]

                if matched and matched['ratio'] > 0:
                    ratio = Decimal(str(matched['ratio']))
                    contract = session.query(DerivativeContract).filter_by(
                        market="HK", code=w['code']
                    ).first()
                    if contract:
                        old_ratio = contract.conversion_ratio
                        contract.conversion_ratio = ratio
                        contract.data_source = "FUTU"
                        print(f"  {w['code']}: {old_ratio} -> {ratio} (via {matched['futu_code']})")
                        updated += 1
                else:
                    print(f"  {w['code']}: 未找到匹配 (strike={w['strike']}, expiry={w['expiry']})")
                    not_found += 1

            session.commit()

        print(f"\n完成: 更新 {updated} 个，未找到 {not_found} 个")

    finally:
        ctx.close()


if __name__ == "__main__":
    update_warrant_ratios()
