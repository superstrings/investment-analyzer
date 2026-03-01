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

import json
import logging
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
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
                lines.append(
                    f"\n[查看持仓]({settings.web.base_url}/portfolio) | [查看信号]({settings.web.base_url}/signals)"
                )
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


def run_claude_prompt(prompt: str, model: str = None) -> str:
    """Run a claude CLI prompt and return the output.

    Args:
        prompt: The prompt text to send to Claude CLI.
        model: Optional model name (e.g. "sonnet"). Defaults to CLI default.
    """
    logger.info("Running Claude CLI analysis...")

    cmd = ["claude", "-p", prompt, "--output-format", "text"]
    if model:
        cmd.extend(["--model", model])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900,  # 15 min timeout for analysis (WebSearch + technical analysis)
            cwd=str(PROJECT_DIR),
            env=settings.proxy.get_subprocess_env(),
        )

        if result.returncode != 0:
            logger.error(f"Claude CLI error (rc={result.returncode})")
            logger.error(
                f"  stderr: {result.stderr[:500] if result.stderr else '(empty)'}"
            )
            logger.error(
                f"  stdout: {result.stdout[:500] if result.stdout else '(empty)'}"
            )
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


def _should_skip_analysis(market: str, code: str) -> bool:
    """Check if a stock should be skipped (index, ETF, leveraged product).

    Skip:
    - HK indices: 800xxx (恒生指数系列)
    - HK leveraged/inverse ETFs: 07xxx (杠杆/反向产品)
    - US indices: .VIX, .SPX etc.
    - Forex/commodities: USDCNH, XAUUSD, HGmain
    """
    pure_code = code.split(".", 1)[-1] if "." in code else code

    if market == "HK":
        # Indices: 800000 (恒生指数), 800100 etc.
        if pure_code.startswith("800"):
            return True
        # Leveraged/inverse ETFs: 07xxx series
        if pure_code.startswith("07"):
            return True
    if market == "US":
        # Indices
        if pure_code.startswith("."):
            return True
        # Futures
        if pure_code.endswith("main"):
            return True
    # Forex/commodities in any market
    if pure_code in ("USDCNH", "XAUUSD"):
        return True

    return False


def _get_market_positions(user_id: int, market: str) -> list:
    """Get positions for a specific market (pure Python, no LLM)."""
    from sqlalchemy import func

    from db.database import get_session
    from db.models import Account, Position

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

            result.append(
                {
                    "code": full_code,
                    "name": p.stock_name or "",
                    "qty": float(p.qty),
                    "cost_price": float(p.cost_price or 0),
                    "market_price": float(p.market_price or 0),
                    "market_val": float(p.market_val or 0),
                    "pl_val": float(p.pl_val or 0),
                    "pl_ratio": raw_ratio,
                }
            )
        return result


def _get_market_watchlist(user_id: int, market: str) -> list:
    """Get active watchlist items for a market with latest prices from Kline."""
    from sqlalchemy import and_, func

    from db.database import get_session
    from db.models import Kline, WatchlistItem

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
        price_map = {
            k.code: (float(k.close), float(k.change_pct or 0)) for k in latest_klines
        }

        result = []
        for it in items:
            full_code = f"{it.market}.{it.code}"
            close, change_pct = price_map.get(full_code, (0.0, 0.0))
            result.append(
                {
                    "code": full_code,
                    "name": it.stock_name or "",
                    "latest_price": close,
                    "change_pct": change_pct,
                }
            )
        return result


def _save_analysis_output(
    code: str, name: str, market: str, analysis_text: str
) -> None:
    """Save analysis output to DB (AnalysisResult) and local file."""
    # DB: save to AnalysisResult
    try:
        from services.analysis_service import create_analysis_service

        svc = create_analysis_service()
        user_id = get_user_id()
        pure_code = code.split(".", 1)[-1] if "." in code else code
        svc.save_result(
            user_id=user_id,
            market=market,
            code=pure_code,
            stock_name=name,
            analysis_type="post_market",
            result_json=json.dumps({"analysis": analysis_text}, ensure_ascii=False),
        )
        logger.info(f"  → 分析结果已保存到DB: {code}")
    except Exception as e:
        logger.warning(f"  → DB保存失败 {code}: {e}")

    # File: save to logs/analysis/{date}/{market}/
    try:
        out_dir = PROJECT_DIR / "logs" / "analysis" / str(date.today()) / market
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = code.replace(".", "_") + ".md"
        (out_dir / filename).write_text(analysis_text, encoding="utf-8")
        logger.info(f"  → 分析结果已保存到文件: {out_dir / filename}")
    except Exception as e:
        logger.warning(f"  → 文件保存失败 {code}: {e}")


def _ensure_klines_synced(codes: list[str], kline_days: int = 5) -> None:
    """Quick sync klines for specific codes before analysis."""
    if not codes:
        return
    try:
        from services.sync_service import create_sync_service

        svc = create_sync_service()
        result = svc.sync_klines(codes, days=kline_days)
        if result.success:
            logger.info(f"K线同步完成: {len(codes)} 只, {result.records_synced} 条")
        else:
            logger.warning(f"K线同步部分失败: {result.error}")
    except Exception as e:
        logger.warning(f"K线同步失败: {e}")


def _get_valuation_search_hint(market: str, code: str, name: str) -> str:
    """Get market-specific valuation search keyword for WebSearch."""
    pure_code = code.split(".", 1)[-1] if "." in code else code
    if market in ("HK", "A"):
        return f'"{pure_code} 估值 forward PE" site:eastmoney.com OR site:finance.yahoo.com'
    elif market == "US":
        return f'"{pure_code} forward PE PEG" site:finance.yahoo.com'
    elif market == "JP":
        return f'"{pure_code} valuation forward PE" site:finance.yahoo.com'
    return f'"{name} forward PE PEG"'


def _analyze_single_stock(
    code: str, name: str, position_info: str, market: str = ""
) -> str:
    """Analyze a single stock via Claude CLI. Returns analysis text."""
    if not market:
        market = code.split(".")[0] if "." in code else ""
    search_hint = _get_valuation_search_hint(market, code, name)

    prompt = f"""分析持仓 {code} ({name})，{position_info}

{V12_FRAMEWORK_PROMPT}

请执行:
1. 用 WebSearch 搜索 {search_hint} 获取估值数据。**只搜索一次**，搜不到就跳过估值筛选直接技术评分
2. 用 run_technical_analysis 对 {code} 做技术分析
3. 按框架: 估值筛选→技术评分→信号判定
4. 用 save_signal 存储信号 (signal_source="post_market")
5. 如有操作建议用 create_plan 存储
6. 用 save_analysis_result 保存分析结果
7. 正股≥7分且估值通过→评估期权,有则 save_signal(signal_category="option")

输出格式(2-3行): 估值(Forward PE=xx/PB=xx) | 技术X/12 | 信号 | 关键价位 | 操作建议"""

    return run_claude_prompt(prompt)


def _analyze_watchlist_stock(
    code: str, name: str, price_info: str, market: str = ""
) -> str:
    """Analyze a watchlist stock via Claude CLI — focus on opportunity discovery."""
    if not market:
        market = code.split(".")[0] if "." in code else ""
    search_hint = _get_valuation_search_hint(market, code, name)

    prompt = f"""分析关注个股 {code} ({name})，{price_info}

{V12_FRAMEWORK_PROMPT}

请执行:
1. 用 WebSearch 搜索 {search_hint} 获取估值数据。**只搜索一次**，搜不到就跳过估值筛选直接技术评分
2. 用 run_technical_analysis 对 {code} 做技术分析
3. 按框架: 估值筛选→技术评分→信号判定，重点判断买入机会
4. 用 save_signal 存储信号 (signal_source="post_market")
5. 如有交易机会用 create_plan 创建计划(含入场价/止损/目标价)
6. 用 save_analysis_result 保存分析结果
7. ≥7分且估值通过→评估期权,有则 save_signal(signal_category="option")

输出格式(2-3行): 估值(Forward PE=xx/PB=xx) | 技术X/12 | 信号 | 关键价位 | 是否建仓"""

    return run_claude_prompt(prompt)


def _analyze_stock_task(stock: dict, market: str) -> dict:
    """Analyze a single stock (position or watchlist). Used as ThreadPoolExecutor target.

    Args:
        stock: Dict with 'code', 'name', 'info', 'type' ('position' or 'watchlist').
        market: Market code (HK/US/A/JP).

    Returns:
        Dict with analysis result added.
    """
    code, name, info = stock["code"], stock["name"], stock["info"]
    stock_type = stock["type"]

    try:
        if stock_type == "position":
            output = _analyze_single_stock(code, name, info, market=market)
        else:
            output = _analyze_watchlist_stock(code, name, info, market=market)
    except Exception as e:
        logger.error(f"分析失败 {code}: {e}")
        output = f"分析失败: {e}"

    # Persist analysis output
    _save_analysis_output(code, name, market, output)

    return {**stock, "analysis": output}


def _send_stock_dingtalk(
    dingtalk, market_name: str, result: dict, user_id: int
) -> None:
    """Send DingTalk message for a single stock analysis result."""
    try:
        stock_type_label = "持仓" if result["type"] == "position" else "关注"
        title = f"{market_name} {stock_type_label} | {result['code']} {result['name']}"
        text = f"### {result['code']} {result['name']}\n"
        text += f"> {result['info']}\n\n"
        text += result["analysis"]

        dingtalk.send_markdown_chunked(
            title,
            text,
            user_id=user_id,
            message_type="report",
        )
    except Exception as e:
        logger.warning(f"钉钉推送失败 {result['code']}: {e}")


def run_post_market(market: str, max_workers: int = 4):
    """Post-market analysis: parallel analyze positions + watchlist stocks."""
    import time as _time

    market_name = MARKET_NAMES.get(market, market)
    logger.info(f"=== {market_name}盘后分析开始 ({date.today()}) ===")
    start_time = _time.time()

    user_id = get_user_id()

    # Step 1: Get positions + watchlist (filter out options, indices, ETFs)
    positions = _get_market_positions(user_id, market)
    stocks = [
        p
        for p in positions
        if not _is_option_code(market, p["code"].split(".", 1)[-1])
        and not _should_skip_analysis(market, p["code"])
    ]
    skipped = len(positions) - len(stocks)
    logger.info(
        f"[1/4] 获取 {market_name} 持仓: {len(positions)} 个 (分析 {len(stocks)}, 跳过 {skipped})"
    )

    watchlist = _get_market_watchlist(user_id, market)
    pos_codes = {p["code"] for p in stocks}
    watchlist_stocks = [
        w
        for w in watchlist
        if w["code"] not in pos_codes
        and not _is_option_code(market, w["code"].split(".", 1)[-1])
        and not _should_skip_analysis(market, w["code"])
    ]
    logger.info(
        f"[1/4] 获取 {market_name} 关注: {len(watchlist)} 个 (去重后 {len(watchlist_stocks)})"
    )

    if not stocks and not watchlist_stocks:
        logger.info("无股票持仓且无关注个股，跳过分析")
        return

    # Step 2: Sync klines for all stocks before analysis
    all_codes = [p["code"] for p in stocks] + [w["code"] for w in watchlist_stocks]
    logger.info(f"[2/4] 同步 K 线 ({len(all_codes)} 只)...")
    _ensure_klines_synced(all_codes)

    # Step 3: Build unified task list
    tasks = []
    for p in stocks:
        pl_pct = p["pl_ratio"] * 100
        info = f"数量{p['qty']:.0f}, 成本{p['cost_price']:.2f}, 现价{p['market_price']:.2f}, 盈亏{pl_pct:+.1f}%"
        tasks.append(
            {"code": p["code"], "name": p["name"], "info": info, "type": "position"}
        )

    for w in watchlist_stocks:
        info = f"最新价{w['latest_price']:.2f}, 涨跌{w['change_pct']:+.2f}%"
        tasks.append(
            {"code": w["code"], "name": w["name"], "info": info, "type": "watchlist"}
        )

    logger.info(f"[3/4] 并行分析 {len(tasks)} 只股票 (max_workers={max_workers})...")

    # Parallel analysis with per-stock DingTalk push
    from services.dingtalk_service import create_dingtalk_service

    dingtalk = create_dingtalk_service()
    results = []
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(_analyze_stock_task, task, market): task for task in tasks
        }

        for future in as_completed(future_to_task):
            task = future_to_task[future]
            completed += 1
            try:
                result = future.result(timeout=900)
            except Exception as e:
                logger.error(f"分析异常 {task['code']}: {e}")
                result = {**task, "analysis": f"分析失败: {e}"}

            results.append(result)
            logger.info(
                f"  [{completed}/{len(tasks)}] {result['code']} {result['name']} "
                f"完成 ({len(result['analysis'])} chars)"
            )

            # Send DingTalk per stock immediately
            _send_stock_dingtalk(dingtalk, market_name, result, user_id)

    # Step 4: Send summary message
    logger.info(f"[4/4] 推送汇总...")
    pos_results = [r for r in results if r["type"] == "position"]
    watch_results = [r for r in results if r["type"] == "watchlist"]

    summary_lines = [f"## {market_name}盘后分析汇总 ({date.today()})\n"]

    if stocks:
        total_val = sum(p["market_val"] for p in positions)
        total_pl = sum(p["pl_val"] for p in positions)
        summary_lines.append(
            f"**总市值**: ¥{total_val:,.0f} | **总盈亏**: ¥{total_pl:+,.0f}\n"
        )

    if pos_results:
        summary_lines.append("### 持仓\n")
        for r in sorted(pos_results, key=lambda x: x["code"]):
            # Extract first line of analysis as brief summary
            brief = r["analysis"].split("\n")[0][:100] if r["analysis"] else "分析失败"
            summary_lines.append(f"- **{r['code']}** {r['name']}: {brief}")

    if watch_results:
        summary_lines.append("\n### 关注\n")
        for r in sorted(watch_results, key=lambda x: x["code"]):
            brief = r["analysis"].split("\n")[0][:100] if r["analysis"] else "分析失败"
            summary_lines.append(f"- **{r['code']}** {r['name']}: {brief}")

    base_url = settings.web.base_url
    if base_url:
        summary_lines.append(
            f"\n[持仓]({base_url}/portfolio) | [关注]({base_url}/watchlist) "
            f"| [信号]({base_url}/signals) | [计划]({base_url}/plans)"
        )

    elapsed = _time.time() - start_time
    summary_lines.append(f"\n*耗时 {elapsed / 60:.1f} 分钟*")

    try:
        dingtalk.send_markdown(
            f"{market_name}盘后汇总",
            "\n".join(summary_lines),
            user_id=user_id,
            message_type="report",
        )
        logger.info("汇总推送成功")
    except Exception as e:
        logger.warning(f"汇总推送失败: {e}")

    logger.info(
        f"=== {market_name}盘后分析完成 "
        f"(持仓{len(pos_results)}只, 关注{len(watch_results)}只, "
        f"耗时{elapsed / 60:.1f}分钟) ==="
    )


def run_pre_market(market: str):
    """Pre-market briefing: analyze positions + watchlist stocks."""
    market_name = MARKET_NAMES.get(market, market)
    logger.info(f"=== {market_name}盘前检查开始 ({date.today()}) ===")

    user_id = get_user_id()

    # Fetch positions + watchlist (filter out options, indices, ETFs)
    positions = _get_market_positions(user_id, market)
    stocks = [
        p
        for p in positions
        if not _is_option_code(market, p["code"].split(".", 1)[-1])
        and not _should_skip_analysis(market, p["code"])
    ]
    logger.info(f"[1/3] {market_name} 持仓 {len(stocks)} 只股票 (共{len(positions)}个)")

    watchlist = _get_market_watchlist(user_id, market)
    pos_codes = {p["code"] for p in stocks}
    watchlist_stocks = [
        w
        for w in watchlist
        if w["code"] not in pos_codes
        and not _is_option_code(market, w["code"].split(".", 1)[-1])
        and not _should_skip_analysis(market, w["code"])
    ]
    logger.info(
        f"[1/3] {market_name} 关注 {len(watchlist_stocks)} 只股票 (共{len(watchlist)}个)"
    )

    if not stocks and not watchlist_stocks:
        logger.info("无股票持仓且无关注个股，跳过盘前检查")
        return

    # Build context for Claude
    pos_summary = []
    for p in stocks:
        pl_pct = p["pl_ratio"] * 100
        pos_summary.append(
            f"- {p['code']} {p['name']}: 现价{p['market_price']:.2f}, 盈亏{pl_pct:+.1f}%"
        )
    pos_text = "\n".join(pos_summary) if pos_summary else "（无持仓）"

    watch_summary = []
    for w in watchlist_stocks:
        watch_summary.append(
            f"- {w['code']} {w['name']}: 最新价{w['latest_price']:.2f}, 涨跌{w['change_pct']:+.2f}%"
        )
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
