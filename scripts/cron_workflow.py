#!/usr/bin/env python3
"""
Cron workflow script for automated analysis.

Usage:
    python scripts/cron_workflow.py sync
    python scripts/cron_workflow.py pre_market HK
    python scripts/cron_workflow.py post_market HK
    python scripts/cron_workflow.py pre_market US
    python scripts/cron_workflow.py post_market US
    python scripts/cron_workflow.py pre_market A
    python scripts/cron_workflow.py post_market A
    python scripts/cron_workflow.py pre_market JP
    python scripts/cron_workflow.py post_market JP

Crontab example (UTC+8):
    0 8 * * 1-5   cd $PROJECT && .venv/bin/python scripts/cron_workflow.py sync
    30 8 * * 1-5  cd $PROJECT && .venv/bin/python scripts/cron_workflow.py pre_market HK
    30 16 * * 1-5 cd $PROJECT && .venv/bin/python scripts/cron_workflow.py post_market HK
    0 9 * * 1-5   cd $PROJECT && .venv/bin/python scripts/cron_workflow.py pre_market A
    30 15 * * 1-5 cd $PROJECT && .venv/bin/python scripts/cron_workflow.py post_market A
    0 20 * * 1-5  cd $PROJECT && .venv/bin/python scripts/cron_workflow.py pre_market US
    0 5 * * 2-6   cd $PROJECT && .venv/bin/python scripts/cron_workflow.py post_market US
"""

import logging
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

# Add project root to path
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_DIR / "logs" / "cron.log"),
    ],
)
logger = logging.getLogger(__name__)

from config import settings  # noqa: E402
from config.prompts import V12_FRAMEWORK_PROMPT  # noqa: E402

# Default user
DEFAULT_USERNAME = "dyson"

MARKET_NAMES = {"HK": "港股", "US": "美股", "A": "A股", "JP": "日股"}


def get_user_id(username: str = DEFAULT_USERNAME) -> int:
    """Get user ID from database."""
    from db.database import get_session
    from db.models import User

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            raise ValueError(f"User '{username}' not found")
        return user.id


def run_sync():
    """Direct Python sync (no LLM needed)."""
    logger.info("Starting data sync...")

    try:
        from services.sync_service import create_sync_service

        user_id = get_user_id()
        svc = create_sync_service()
        results = svc.sync_all(user_id, kline_days=30)

        for name, result in results.items():
            status = "OK" if result.success else "FAIL"
            logger.info(f"  {name}: {status} ({result.records_synced} records)")

        # Notify via DingTalk
        try:
            from config import settings
            from services.dingtalk_service import create_dingtalk_service

            dingtalk = create_dingtalk_service()
            lines = [f"## 数据同步完成 ({date.today()})\n"]
            for name, result in results.items():
                icon = "✅" if result.success else "❌"
                lines.append(f"- {icon} {name}: {result.records_synced}条")
            if settings.web.base_url:
                lines.append(f"\n[查看持仓]({settings.web.base_url}/portfolio) | [查看信号]({settings.web.base_url}/signals)")
            dingtalk.send_markdown(
                "数据同步",
                "\n".join(lines),
                user_id=user_id,
                message_type="report",
            )
        except Exception as e:
            logger.warning(f"DingTalk notification failed: {e}")

        logger.info("Sync completed")

    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        sys.exit(1)


def run_claude_prompt(prompt: str) -> str:
    """Run a claude CLI prompt and return the output."""
    logger.info("Running Claude CLI analysis...")

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=900,  # 15 min timeout for analysis (WebSearch + technical analysis)
            cwd=str(PROJECT_DIR),
            env=settings.proxy.get_subprocess_env(),
        )

        if result.returncode != 0:
            logger.error(f"Claude CLI error (rc={result.returncode})")
            logger.error(f"  stderr: {result.stderr[:500] if result.stderr else '(empty)'}")
            logger.error(f"  stdout: {result.stdout[:500] if result.stdout else '(empty)'}")
            return f"分析出错: {result.stderr or result.stdout or 'unknown error'}"

        output = result.stdout.strip()
        logger.info(f"Claude analysis completed ({len(output)} chars)")
        return output

    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out")
        return "分析超时"
    except FileNotFoundError:
        logger.error("Claude CLI not found")
        return "Claude CLI 未安装"
    except Exception as e:
        logger.error(f"Claude CLI failed: {e}")
        return f"分析失败: {e}"


def _is_option_code(market: str, code: str) -> bool:
    """Check if a code is an option/derivative (skip analysis).

    HK options: codes containing letters (e.g., TCH260330C650000)
    US options: SYMBOL + YYMMDD + C/P + STRIKE (e.g., NVDA260116C186000)
    """
    import re

    if market == "HK":
        return any(c.isalpha() for c in code)
    if market == "US":
        return bool(re.match(r"^[A-Z]+\d{6}[CP]\d+$", code))
    return False  # JP, A 无期权


def _get_market_positions(user_id: int, market: str) -> list:
    """Get positions for a specific market (pure Python, no LLM)."""
    from db.database import get_session
    from db.models import Account, Position
    from sqlalchemy import func

    with get_session() as session:
        account_ids = [
            a.id for a in session.query(Account).filter_by(user_id=user_id).all()
        ]
        if not account_ids:
            return []

        latest_dates = (
            session.query(
                Position.account_id,
                func.max(Position.snapshot_date).label("max_date"),
            )
            .filter(Position.account_id.in_(account_ids))
            .group_by(Position.account_id)
            .subquery()
        )

        positions = (
            session.query(Position)
            .join(
                latest_dates,
                (Position.account_id == latest_dates.c.account_id)
                & (Position.snapshot_date == latest_dates.c.max_date),
            )
            .filter(Position.market == market)
            .order_by(Position.pl_ratio.desc())
            .all()
        )

        # Detach from session, dedup by code (keep first = latest snapshot)
        seen = set()
        result = []
        for p in positions:
            full_code = f"{p.market}.{p.code}"
            if full_code in seen:
                continue
            seen.add(full_code)

            # Normalize pl_ratio: Futu HK/US/JP stores as percentage
            raw_ratio = float(p.pl_ratio or 0)
            if p.market in ("HK", "US", "JP") and abs(raw_ratio) > 0:
                raw_ratio = raw_ratio / 100

            result.append({
                "code": full_code,
                "name": p.stock_name or "",
                "qty": float(p.qty),
                "cost_price": float(p.cost_price or 0),
                "market_price": float(p.market_price or 0),
                "market_val": float(p.market_val or 0),
                "pl_val": float(p.pl_val or 0),
                "pl_ratio": raw_ratio,
            })
        return result


def _get_market_watchlist(user_id: int, market: str) -> list:
    """Get active watchlist items for a market with latest prices from Kline."""
    from db.database import get_session
    from db.models import Kline, WatchlistItem
    from sqlalchemy import and_, func

    with get_session() as session:
        items = (
            session.query(WatchlistItem)
            .filter(
                WatchlistItem.user_id == user_id,
                WatchlistItem.market == market,
                WatchlistItem.is_active == True,
            )
            .all()
        )
        if not items:
            return []

        # Batch fetch latest prices from Kline
        codes = [f"{it.market}.{it.code}" for it in items]
        latest_dates = (
            session.query(
                Kline.code,
                func.max(Kline.trade_date).label("max_date"),
            )
            .filter(Kline.code.in_(codes))
            .group_by(Kline.code)
            .subquery()
        )
        latest_klines = (
            session.query(Kline.code, Kline.close, Kline.change_pct)
            .join(
                latest_dates,
                and_(
                    Kline.code == latest_dates.c.code,
                    Kline.trade_date == latest_dates.c.max_date,
                ),
            )
            .all()
        )
        price_map = {k.code: (float(k.close), float(k.change_pct or 0)) for k in latest_klines}

        result = []
        for it in items:
            full_code = f"{it.market}.{it.code}"
            close, change_pct = price_map.get(full_code, (0.0, 0.0))
            result.append({
                "code": full_code,
                "name": it.stock_name or "",
                "latest_price": close,
                "change_pct": change_pct,
            })
        return result


def _analyze_single_stock(code: str, name: str, position_info: str) -> str:
    """Analyze a single stock via Claude CLI. Returns analysis text."""
    prompt = f"""分析持仓 {code} ({name})，{position_info}

{V12_FRAMEWORK_PROMPT}

请执行:
1. 用 WebSearch 搜索 "{name} forward PE PEG PB ROE 2025 2026" 获取最新估值数据 (Yahoo Finance / Google Finance / 东方财富)
2. 用 run_technical_analysis 对 {code} 做技术分析
3. 按上述框架: 先估值筛选 (用搜索到的估值数据) → 通过后技术评分 → 信号判定
4. 给出信号并用 save_signal 存储 (signal_source="post_market")
5. 如有操作建议，用 create_plan 存储
6. 如正股技术评分≥7且估值通过，评估期权机会，有则 save_signal(signal_category="option")

直接输出简洁分析 (3-5行): 估值判断(含具体数据如Forward PE=xx)、技术评分X/12、信号、关键价位、操作建议。如有期权机会额外说明。"""

    return run_claude_prompt(prompt)


def _analyze_watchlist_stock(code: str, name: str, price_info: str) -> str:
    """Analyze a watchlist stock via Claude CLI — focus on opportunity discovery."""
    prompt = f"""分析关注个股 {code} ({name})，{price_info}

{V12_FRAMEWORK_PROMPT}

请执行:
1. 用 WebSearch 搜索 "{name} forward PE PEG PB ROE 2025 2026" 获取最新估值数据 (Yahoo Finance / Google Finance / 东方财富)
2. 用 run_technical_analysis 对 {code} 做技术分析
3. 按上述框架: 先估值筛选 (用搜索到的估值数据) → 通过后技术评分 → 信号判定
4. 重点判断是否存在买入机会 (突破/回调到位/底部反转)
5. 给出信号 (BUY/SELL/HOLD/WATCH) 并用 save_signal 存储 (signal_source="post_market")
6. 如有明确交易机会，用 create_plan 创建操作计划 (含入场价、止损、目标价)
7. 如技术评分≥7且估值通过，评估期权机会，有则 save_signal(signal_category="option")

直接输出简洁分析 (3-5行): 估值判断(含具体数据如Forward PE=xx)、技术评分X/12、信号、关键价位、是否值得建仓。如有期权机会额外说明。"""

    return run_claude_prompt(prompt)


def run_post_market(market: str):
    """Post-market analysis: analyze positions + watchlist stocks."""
    market_name = MARKET_NAMES.get(market, market)
    logger.info(f"=== {market_name}盘后分析开始 ({date.today()}) ===")

    user_id = get_user_id()

    # Step 1: Get positions + watchlist
    positions = _get_market_positions(user_id, market)
    stocks = [p for p in positions if not _is_option_code(market, p["code"].split(".", 1)[-1])]
    logger.info(f"[1/5] 获取 {market_name} 持仓: {len(positions)} 个 (股票 {len(stocks)}, 期权 {len(positions)-len(stocks)})")

    watchlist = _get_market_watchlist(user_id, market)
    # Dedup: remove watchlist items already in positions
    pos_codes = {p["code"] for p in stocks}
    watchlist_stocks = [
        w for w in watchlist
        if w["code"] not in pos_codes
        and not _is_option_code(market, w["code"].split(".", 1)[-1])
    ]
    logger.info(f"[1/5] 获取 {market_name} 关注: {len(watchlist)} 个 (去重后 {len(watchlist_stocks)})")

    if not stocks and not watchlist_stocks:
        logger.info("无股票持仓且无关注个股，跳过分析")
        return

    # Step 2: Analyze position stocks via Claude CLI
    pos_results = []
    for i, p in enumerate(stocks, 1):
        code, name = p["code"], p["name"]
        pl_pct = p["pl_ratio"] * 100
        info = f"数量{p['qty']:.0f}, 成本{p['cost_price']:.2f}, 现价{p['market_price']:.2f}, 盈亏{pl_pct:+.1f}%"
        logger.info(f"[2/5] 持仓分析 ({i}/{len(stocks)}): {code} {name} | {info}")

        output = _analyze_single_stock(code, name, info)
        pos_results.append({"code": code, "name": name, "info": info, "analysis": output})
        logger.info(f"  → 完成 ({len(output)} chars)")

    # Step 3: Analyze watchlist stocks via Claude CLI
    watch_results = []
    for i, w in enumerate(watchlist_stocks, 1):
        code, name = w["code"], w["name"]
        price_info = f"最新价{w['latest_price']:.2f}, 涨跌{w['change_pct']:+.2f}%"
        logger.info(f"[3/5] 关注分析 ({i}/{len(watchlist_stocks)}): {code} {name} | {price_info}")

        output = _analyze_watchlist_stock(code, name, price_info)
        watch_results.append({"code": code, "name": name, "info": price_info, "analysis": output})
        logger.info(f"  → 完成 ({len(output)} chars)")

    # Step 4: Build summary
    logger.info(f"[4/5] 生成汇总...")
    lines = [f"## {market_name}盘后分析 ({date.today()})\n"]

    if stocks:
        total_val = sum(p["market_val"] for p in positions)
        total_pl = sum(p["pl_val"] for p in positions)
        lines.append(f"**总市值**: ¥{total_val:,.0f} | **总盈亏**: ¥{total_pl:+,.0f}\n")

    if pos_results:
        lines.append("### 持仓分析\n")
        for r in pos_results:
            lines.append(f"#### {r['code']} {r['name']}")
            lines.append(f"> {r['info']}")
            lines.append(f"{r['analysis']}\n")

    if watch_results:
        lines.append("### 关注分析\n")
        for r in watch_results:
            lines.append(f"#### {r['code']} {r['name']}")
            lines.append(f"> {r['info']}")
            lines.append(f"{r['analysis']}\n")

    base_url = settings.web.base_url
    if base_url:
        lines.append(f"[持仓详情]({base_url}/portfolio) | [关注列表]({base_url}/watchlist) | [信号]({base_url}/signals) | [计划]({base_url}/plans)")

    summary = "\n".join(lines)

    # Step 5: Push to DingTalk
    logger.info(f"[5/5] 推送钉钉...")
    try:
        from services.dingtalk_service import create_dingtalk_service
        dingtalk = create_dingtalk_service()
        if len(summary) > 3000:
            summary = summary[:3000] + "\n...(已截断)"
        dingtalk.send_markdown(
            f"{market_name}盘后分析",
            summary,
            user_id=user_id,
            message_type="report",
        )
        logger.info("钉钉推送成功")
    except Exception as e:
        logger.warning(f"钉钉推送失败: {e}")

    logger.info(f"=== {market_name}盘后分析完成 (持仓{len(pos_results)}只, 关注{len(watch_results)}只) ===")


def run_pre_market(market: str):
    """Pre-market briefing: analyze positions + watchlist stocks."""
    market_name = MARKET_NAMES.get(market, market)
    logger.info(f"=== {market_name}盘前检查开始 ({date.today()}) ===")

    user_id = get_user_id()

    # Fetch positions + watchlist
    positions = _get_market_positions(user_id, market)
    stocks = [p for p in positions if not _is_option_code(market, p["code"].split(".", 1)[-1])]
    logger.info(f"[1/3] {market_name} 持仓 {len(stocks)} 只股票")

    watchlist = _get_market_watchlist(user_id, market)
    pos_codes = {p["code"] for p in stocks}
    watchlist_stocks = [
        w for w in watchlist
        if w["code"] not in pos_codes
        and not _is_option_code(market, w["code"].split(".", 1)[-1])
    ]
    logger.info(f"[1/3] {market_name} 关注 {len(watchlist)} 个 (去重后 {len(watchlist_stocks)})")

    if not stocks and not watchlist_stocks:
        logger.info("无股票持仓且无关注个股，跳过盘前检查")
        return

    # Build context for Claude
    pos_summary = []
    for p in stocks:
        pl_pct = p["pl_ratio"] * 100
        pos_summary.append(f"- {p['code']} {p['name']}: 现价{p['market_price']:.2f}, 盈亏{pl_pct:+.1f}%")
    pos_text = "\n".join(pos_summary) if pos_summary else "（无持仓）"

    watch_summary = []
    for w in watchlist_stocks:
        watch_summary.append(f"- {w['code']} {w['name']}: 最新价{w['latest_price']:.2f}, 涨跌{w['change_pct']:+.2f}%")
    watch_text = "\n".join(watch_summary) if watch_summary else "（无关注）"

    base_url = settings.web.base_url
    url_hint = ""
    if base_url:
        url_hint = f"\n在末尾附上链接: [持仓]({base_url}/portfolio) | [关注]({base_url}/watchlist) | [计划]({base_url}/plans)"

    prompt = f"""{market_name}盘前检查 ({date.today()}):

当前持仓:
{pos_text}

关注个股:
{watch_text}

{V12_FRAMEWORK_PROMPT}

请执行:
1. 用 get_signals 查看 {market} 市场活跃信号 (包括 signal_category=option 的期权信号)
2. 用 get_plans 查看今日 {market} 市场操作计划
3. 对关键持仓 (盈亏较大或有信号的) 用 get_klines 检查最新走势
4. 用 WebSearch 搜索持仓和关注个股的最新估值数据 (forward PE, PEG, PB, ROE)，可搜索 "股票名 forward PE 2025 2026" 或从 Yahoo Finance / 东方财富获取
5. 按 V12 框架检查:
   - 止损触发: 股票亏损≥10% / 期权亏损≥30% → 列为 must_do
   - 估值+技术面概要 (用搜索到的数据，仅标注需要注意的)
   - 关注个股入场机会
   - 期权信号提示 (查看活跃期权信号)
6. 生成盘前简报，包含:
   - 今日操作计划 (按优先级, 止损最优先)
   - 持仓风险提醒 (止损触发/破位/超涨)
   - 关键价位提示 (支撑/阻力)
   - 关注个股机会提示
   - 期权机会提示 (如有)
7. 用 send_dingtalk_message 推送简报 (markdown 格式){url_hint}

直接输出盘前简报内容。"""

    logger.info(f"[2/3] Claude 生成盘前简报...")
    output = run_claude_prompt(prompt)
    logger.info(f"[3/3] 盘前简报完成 ({len(output)} chars)")
    logger.info(f"=== {market_name}盘前检查完成 ===")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/cron_workflow.py <phase> [market]")
        print("  phase: sync | pre_market | post_market")
        print("  market: HK | US | A | JP")
        sys.exit(1)

    phase = sys.argv[1]
    market = sys.argv[2] if len(sys.argv) > 2 else None

    # Ensure logs directory exists
    (PROJECT_DIR / "logs").mkdir(exist_ok=True)

    if phase == "sync":
        run_sync()
    elif phase == "post_market":
        if not market:
            print("Error: market required for post_market (HK/US/A/JP)")
            sys.exit(1)
        run_post_market(market)
    elif phase == "pre_market":
        if not market:
            print("Error: market required for pre_market (HK/US/A/JP)")
            sys.exit(1)
        run_pre_market(market)
    else:
        print(f"Unknown phase: {phase}")
        sys.exit(1)


if __name__ == "__main__":
    main()
