#!/usr/bin/env python3
"""
Investment Analyzer MCP Server.

Exposes portfolio data, technical analysis, and operations as MCP tools
for Claude CLI to use.

Usage:
    # Run directly (stdio mode)
    python mcp_server.py

    # Configure in Claude CLI settings
    # ~/.claude/settings.json or .claude/settings.json
"""

import json
import logging
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from db.database import get_session
from db.models import (
    Account,
    AccountSnapshot,
    Kline,
    Position,
    Trade,
    User,
    WatchlistItem,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("investment-analyzer")


# =============================================================================
# Helper functions
# =============================================================================


def _get_user_id(username: str = "dyson") -> Optional[int]:
    """Resolve username to user_id."""
    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        return user.id if user else None


def _decimal_to_float(obj: Any) -> Any:
    """Convert Decimals to floats for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, list):
        return [_decimal_to_float(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    return obj


# =============================================================================
# Data Query Tools (read-only)
# =============================================================================


@mcp.tool()
def get_positions(
    username: str = "dyson",
    market: str = "",
) -> str:
    """获取当前持仓 + 盈亏 + 市值。

    Args:
        username: 用户名 (默认 dyson)
        market: 过滤市场 (HK/US/A)，留空返回全部
    """
    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    with get_session() as session:
        account_ids = [
            acc.id for acc in session.query(Account).filter_by(user_id=user_id).all()
        ]
        if not account_ids:
            return "无交易账户"

        # Get latest snapshot date per account
        from sqlalchemy import func

        latest_dates = (
            session.query(
                Position.account_id,
                func.max(Position.snapshot_date).label("max_date"),
            )
            .filter(Position.account_id.in_(account_ids))
            .group_by(Position.account_id)
            .subquery()
        )

        query = session.query(Position).join(
            latest_dates,
            (Position.account_id == latest_dates.c.account_id)
            & (Position.snapshot_date == latest_dates.c.max_date),
        )
        if market:
            query = query.filter(Position.market == market)

        positions = query.all()

        if not positions:
            return "无持仓数据"

        result = []
        total_market_val = Decimal("0")
        total_pl = Decimal("0")
        for p in positions:
            result.append(
                {
                    "code": f"{p.market}.{p.code}",
                    "name": p.stock_name or "",
                    "qty": p.qty,
                    "cost_price": p.cost_price,
                    "market_price": p.market_price,
                    "market_val": p.market_val,
                    "pl_val": p.pl_val,
                    "pl_ratio": f"{float(p.pl_ratio or 0) * 100:.2f}%",
                    "side": p.position_side,
                }
            )
            total_market_val += p.market_val or Decimal("0")
            total_pl += p.pl_val or Decimal("0")

        summary = {
            "total_positions": len(result),
            "total_market_val": total_market_val,
            "total_pl": total_pl,
            "positions": result,
        }
        return json.dumps(_decimal_to_float(summary), ensure_ascii=False, indent=2)


@mcp.tool()
def get_portfolio_summary(username: str = "dyson") -> str:
    """获取投资组合概览：总资产/市值/现金/杠杆率。

    Args:
        username: 用户名
    """
    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    with get_session() as session:
        accounts = session.query(Account).filter_by(user_id=user_id).all()
        if not accounts:
            return "无账户数据"

        portfolio = {}
        for acc in accounts:
            # Latest snapshot
            snapshot = (
                session.query(AccountSnapshot)
                .filter_by(account_id=acc.id)
                .order_by(AccountSnapshot.snapshot_date.desc())
                .first()
            )
            if snapshot:
                leverage = Decimal("0")
                if snapshot.total_assets and snapshot.total_assets > 0:
                    leverage = (
                        snapshot.market_val or Decimal("0")
                    ) / snapshot.total_assets

                portfolio[f"{acc.market}({acc.account_type})"] = {
                    "total_assets": snapshot.total_assets,
                    "cash": snapshot.cash,
                    "market_val": snapshot.market_val,
                    "buying_power": snapshot.buying_power,
                    "leverage": f"{float(leverage):.2f}",
                    "currency": snapshot.currency or acc.currency,
                    "date": snapshot.snapshot_date,
                }

        return json.dumps(_decimal_to_float(portfolio), ensure_ascii=False, indent=2)


@mcp.tool()
def get_klines(
    code: str,
    days: int = 120,
) -> str:
    """获取K线数据 (OHLCV + 均线 + OBV)。

    Args:
        code: 股票代码，如 HK.00700, US.NVDA, SZ.000858
        days: 获取天数 (默认120)
    """
    parts = code.split(".", 1)
    if len(parts) != 2:
        return "代码格式错误，需要 市场.代码，如 HK.00700"

    market, stock_code = parts[0], parts[1]
    db_market = "A" if market in ("SH", "SZ") else market

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    with get_session() as session:
        klines = (
            session.query(Kline)
            .filter_by(market=db_market, code=stock_code)
            .filter(Kline.trade_date >= start_date)
            .filter(Kline.trade_date <= end_date)
            .order_by(Kline.trade_date.asc())
            .all()
        )

        if not klines:
            return f"无 {code} K线数据（{start_date} ~ {end_date}）"

        data = []
        for k in klines:
            data.append(
                {
                    "date": k.trade_date,
                    "open": k.open,
                    "high": k.high,
                    "low": k.low,
                    "close": k.close,
                    "volume": k.volume,
                    "amount": k.amount,
                    "change_pct": k.change_pct,
                    "turnover": k.turnover_rate,
                    "ma5": k.ma5,
                    "ma10": k.ma10,
                    "ma20": k.ma20,
                    "ma60": k.ma60,
                    "obv": k.obv,
                }
            )

        summary = {
            "code": code,
            "records": len(data),
            "date_range": f"{data[0]['date']} ~ {data[-1]['date']}",
            "latest_close": data[-1]["close"],
            "klines": data,
        }
        return json.dumps(_decimal_to_float(summary), ensure_ascii=False, indent=2)


@mcp.tool()
def get_watchlist(username: str = "dyson") -> str:
    """获取关注列表。

    Args:
        username: 用户名
    """
    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    with get_session() as session:
        items = (
            session.query(WatchlistItem)
            .filter_by(user_id=user_id, is_active=True)
            .order_by(WatchlistItem.group_name, WatchlistItem.sort_order)
            .all()
        )

        groups = {}
        for item in items:
            group = item.group_name or "未分组"
            if group not in groups:
                groups[group] = []
            groups[group].append(
                {
                    "code": f"{item.market}.{item.code}",
                    "name": item.stock_name or "",
                    "notes": item.notes or "",
                }
            )

        return json.dumps(groups, ensure_ascii=False, indent=2)


@mcp.tool()
def get_trades(
    username: str = "dyson",
    days: int = 30,
    market: str = "",
) -> str:
    """获取交易记录。

    Args:
        username: 用户名
        days: 查询天数 (默认30)
        market: 过滤市场 (HK/US/A)
    """
    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    start = datetime.now() - timedelta(days=days)
    with get_session() as session:
        account_ids = [
            acc.id for acc in session.query(Account).filter_by(user_id=user_id).all()
        ]
        if not account_ids:
            return "无交易账户"

        query = session.query(Trade).filter(
            Trade.account_id.in_(account_ids),
            Trade.trade_time >= start,
        )
        if market:
            query = query.filter(Trade.market == market)
        query = query.order_by(Trade.trade_time.desc())

        trades = query.all()
        if not trades:
            return f"最近{days}天无交易记录"

        result = []
        for t in trades:
            result.append(
                {
                    "time": t.trade_time,
                    "code": f"{t.market}.{t.code}",
                    "name": t.stock_name or "",
                    "side": t.trd_side,
                    "qty": t.qty,
                    "price": t.price,
                    "amount": t.amount,
                    "fee": t.fee,
                }
            )

        return json.dumps(
            {"total": len(result), "trades": _decimal_to_float(result)},
            ensure_ascii=False,
            indent=2,
        )


@mcp.tool()
def get_signals(
    username: str = "dyson",
    market: str = "",
    signal_type: str = "",
) -> str:
    """获取活跃的交易信号。

    Args:
        username: 用户名
        market: 过滤市场 (HK/US/A)
        signal_type: 过滤类型 (BUY/SELL/HOLD/WATCH)
    """
    from services.signal_service import create_signal_service

    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    svc = create_signal_service()
    signals = svc.get_active_signals(
        user_id, market=market or None, signal_type=signal_type or None
    )

    if not signals:
        return "无活跃信号"

    result = []
    for s in signals:
        result.append(
            {
                "id": s.id,
                "code": f"{s.market}.{s.code}",
                "name": s.stock_name or "",
                "type": s.signal_type,
                "source": s.signal_source,
                "score": s.score,
                "confidence": s.confidence,
                "strength": s.strength,
                "trigger_price": s.trigger_price,
                "target_price": s.target_price,
                "stop_loss": s.stop_loss_price,
                "reason": s.reason or "",
                "created": s.created_at,
            }
        )

    return json.dumps(_decimal_to_float(result), ensure_ascii=False, indent=2)


@mcp.tool()
def get_plans(
    username: str = "dyson",
    date_str: str = "",
) -> str:
    """获取操作计划。

    Args:
        username: 用户名
        date_str: 日期 (YYYY-MM-DD)，留空为今天
    """
    from services.plan_service import create_plan_service

    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    target_date = (
        datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    )

    svc = create_plan_service()
    plans = svc.get_plans_by_date(user_id, target_date)

    if not plans:
        return f"{target_date} 无操作计划"

    result = []
    for p in plans:
        result.append(
            {
                "id": p.id,
                "code": f"{p.market}.{p.code}",
                "name": p.stock_name or "",
                "action": p.action_type,
                "priority": p.priority,
                "entry_price": p.entry_price,
                "stop_loss": p.stop_loss_price,
                "target_1": p.target_price_1,
                "target_2": p.target_price_2,
                "position_size": p.position_size or "",
                "reason": p.reason or "",
                "status": p.status,
            }
        )

    return json.dumps(_decimal_to_float(result), ensure_ascii=False, indent=2)


@mcp.tool()
def get_analysis_history(
    code: str,
    username: str = "dyson",
    days: int = 30,
) -> str:
    """获取个股历史分析结果。

    Args:
        code: 股票代码，如 HK.00700
        username: 用户名
        days: 查询天数
    """
    from services.analysis_service import create_analysis_service

    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    parts = code.split(".", 1)
    if len(parts) != 2:
        return "代码格式错误"

    market, stock_code = parts
    db_market = "A" if market in ("SH", "SZ") else market

    svc = create_analysis_service()
    results = svc.get_results_history(user_id, db_market, stock_code, days)

    if not results:
        return f"无 {code} 分析历史"

    data = []
    for r in results:
        data.append(
            {
                "date": r.analysis_date,
                "type": r.analysis_type,
                "overall_score": r.overall_score,
                "obv_score": r.obv_score,
                "vcp_score": r.vcp_score,
                "rating": r.rating,
                "price": r.current_price,
                "support": r.support_price,
                "resistance": r.resistance_price,
            }
        )

    return json.dumps(_decimal_to_float(data), ensure_ascii=False, indent=2)


@mcp.tool()
def get_position_history(
    code: str,
    username: str = "dyson",
    days: int = 60,
) -> str:
    """获取个股持仓变化历史。

    Args:
        code: 股票代码，如 HK.00700
        username: 用户名
        days: 查询天数
    """
    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    parts = code.split(".", 1)
    if len(parts) != 2:
        return "代码格式错误"

    market, stock_code = parts
    db_market = "A" if market in ("SH", "SZ") else market
    start_date = date.today() - timedelta(days=days)

    with get_session() as session:
        account_ids = [
            acc.id for acc in session.query(Account).filter_by(user_id=user_id).all()
        ]
        if not account_ids:
            return "无账户"

        positions = (
            session.query(Position)
            .filter(
                Position.account_id.in_(account_ids),
                Position.market == db_market,
                Position.code == stock_code,
                Position.snapshot_date >= start_date,
            )
            .order_by(Position.snapshot_date.asc())
            .all()
        )

        if not positions:
            return f"无 {code} 持仓历史"

        data = []
        for p in positions:
            data.append(
                {
                    "date": p.snapshot_date,
                    "qty": p.qty,
                    "cost_price": p.cost_price,
                    "market_price": p.market_price,
                    "market_val": p.market_val,
                    "pl_val": p.pl_val,
                    "pl_ratio": p.pl_ratio,
                }
            )

        return json.dumps(_decimal_to_float(data), ensure_ascii=False, indent=2)


@mcp.tool()
def get_account_history(
    username: str = "dyson",
    days: int = 90,
) -> str:
    """获取账户价值走势。

    Args:
        username: 用户名
        days: 查询天数
    """
    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    start_date = date.today() - timedelta(days=days)

    with get_session() as session:
        accounts = session.query(Account).filter_by(user_id=user_id).all()
        if not accounts:
            return "无账户"

        result = {}
        for acc in accounts:
            snapshots = (
                session.query(AccountSnapshot)
                .filter(
                    AccountSnapshot.account_id == acc.id,
                    AccountSnapshot.snapshot_date >= start_date,
                )
                .order_by(AccountSnapshot.snapshot_date.asc())
                .all()
            )
            if snapshots:
                result[f"{acc.market}({acc.account_type})"] = [
                    {
                        "date": s.snapshot_date,
                        "total_assets": s.total_assets,
                        "cash": s.cash,
                        "market_val": s.market_val,
                    }
                    for s in snapshots
                ]

        return json.dumps(_decimal_to_float(result), ensure_ascii=False, indent=2)


# =============================================================================
# Technical Analysis Tools
# =============================================================================


@mcp.tool()
def run_technical_analysis(
    code: str,
    username: str = "dyson",
    days: int = 120,
) -> str:
    """对个股运行完整技术分析 (OBV/VCP/MACD/RSI/布林带/支撑阻力)。

    Args:
        code: 股票代码，如 HK.00700
        username: 用户名
        days: K线天数 (默认120)
    """
    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    parts = code.split(".", 1)
    if len(parts) != 2:
        return "代码格式错误"

    market, stock_code = parts

    try:
        from skills.analyst import StockAnalyzer

        analyzer = StockAnalyzer()
        db_market = "A" if market in ("SH", "SZ") else market
        result = analyzer.analyze_from_db(db_market, stock_code, days=days)

        if not result:
            return f"无法分析 {code}（数据不足？）"

        analysis = {
            "code": code,
            "stock_name": result.stock_name or "",
            "analysis_date": date.today().isoformat(),
            "technical_score": {
                "final_score": (
                    result.technical_score.final_score
                    if result.technical_score
                    else None
                ),
                "rating": (
                    result.technical_score.rating.value
                    if result.technical_score
                    else None
                ),
                "signal_strength": (
                    result.technical_score.signal_strength.value
                    if result.technical_score
                    else None
                ),
                "obv_score": (
                    result.technical_score.obv_score if result.technical_score else None
                ),
                "vcp_score": (
                    result.technical_score.vcp_score if result.technical_score else None
                ),
            },
            "current_price": result.current_price,
            "support_levels": (
                result.support_levels if hasattr(result, "support_levels") else []
            ),
            "resistance_levels": (
                result.resistance_levels if hasattr(result, "resistance_levels") else []
            ),
            "obv_analysis": (
                {
                    "trend": (
                        result.obv_result.trend.value if result.obv_result else None
                    ),
                    "divergence": (
                        result.obv_result.divergence_type.value
                        if result.obv_result and result.obv_result.divergence_type
                        else None
                    ),
                    "score": result.obv_result.score if result.obv_result else None,
                }
                if result.obv_result
                else None
            ),
            "vcp_analysis": (
                {
                    "stage": (
                        result.vcp_result.stage.value if result.vcp_result else None
                    ),
                    "score": result.vcp_result.score if result.vcp_result else None,
                    "contractions": (
                        result.vcp_result.contraction_count
                        if result.vcp_result
                        else None
                    ),
                }
                if result.vcp_result
                else None
            ),
        }

        return json.dumps(_decimal_to_float(analysis), ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Technical analysis failed for {code}: {e}")
        return f"分析失败: {e}"


@mcp.tool()
def generate_chart(
    code: str,
    days: int = 120,
    style: str = "dark",
) -> str:
    """生成K线图，返回文件路径。

    Args:
        code: 股票代码，如 HK.00700
        days: K线天数
        style: 图表风格 (dark/light)
    """
    try:
        from services.chart_service import BatchChartConfig, create_chart_service

        svc = create_chart_service()
        config = BatchChartConfig(days=days, style=style)
        result = svc.generate_charts_for_codes([code], config=config)

        if result.success and result.generated_files:
            return json.dumps(
                {
                    "success": True,
                    "file": str(result.generated_files[0]),
                    "code": code,
                }
            )
        else:
            return json.dumps(
                {
                    "success": False,
                    "error": result.error_message or "生成失败",
                }
            )

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# =============================================================================
# Write Operations
# =============================================================================


@mcp.tool()
def sync_data(
    username: str = "dyson",
    sync_type: str = "all",
    kline_days: int = 30,
) -> str:
    """触发数据同步 (Futu持仓/交易 + K线)。

    Args:
        username: 用户名
        sync_type: 同步类型 (all/positions/trades/klines)
        kline_days: K线同步天数
    """
    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    try:
        from services.sync_service import create_sync_service

        svc = create_sync_service()

        if sync_type == "all":
            results = svc.sync_all(user_id, kline_days=kline_days)
            summary = {
                k: {
                    "success": v.success,
                    "synced": v.records_synced,
                    "skipped": v.records_skipped,
                    "error": v.error_message or None,
                }
                for k, v in results.items()
            }
            return json.dumps(summary, ensure_ascii=False, indent=2)
        elif sync_type == "positions":
            result = svc.sync_positions(user_id)
        elif sync_type == "trades":
            result = svc.sync_trades(user_id)
        elif sync_type == "klines":
            result = svc.sync_position_klines(user_id, days=kline_days)
        else:
            return f"未知同步类型: {sync_type}"

        return json.dumps(
            {
                "success": result.success,
                "synced": result.records_synced,
                "error": result.error_message or None,
            }
        )

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def save_signal(
    code: str,
    signal_type: str,
    signal_source: str,
    username: str = "dyson",
    stock_name: str = "",
    score: float = None,
    confidence: float = None,
    strength: str = "",
    trigger_price: float = None,
    target_price: float = None,
    stop_loss_price: float = None,
    reason: str = "",
    metadata_json: str = "",
) -> str:
    """存储交易信号。

    Args:
        code: 股票代码，如 HK.00700
        signal_type: 信号类型 (BUY/SELL/HOLD/WATCH)
        signal_source: 信号来源 (post_market/pre_market/llm)
        username: 用户名
        stock_name: 股票名称
        score: 综合评分 (0-100)
        confidence: 置信度 (0-100)
        strength: 信号强度 (strong/moderate/weak)
        trigger_price: 触发价
        target_price: 目标价
        stop_loss_price: 止损价
        reason: 信号理由
        metadata_json: 附加 JSON 数据
    """
    from services.signal_service import create_signal_service

    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    parts = code.split(".", 1)
    if len(parts) != 2:
        return "代码格式错误"

    market, stock_code = parts
    db_market = "A" if market in ("SH", "SZ") else market

    svc = create_signal_service()
    signal = svc.create_signal(
        user_id=user_id,
        market=db_market,
        code=stock_code,
        signal_type=signal_type,
        signal_source=signal_source,
        stock_name=stock_name or None,
        score=Decimal(str(score)) if score is not None else None,
        confidence=Decimal(str(confidence)) if confidence is not None else None,
        strength=strength or None,
        trigger_price=(
            Decimal(str(trigger_price)) if trigger_price is not None else None
        ),
        target_price=Decimal(str(target_price)) if target_price is not None else None,
        stop_loss_price=(
            Decimal(str(stop_loss_price)) if stop_loss_price is not None else None
        ),
        reason=reason or None,
        metadata_json=metadata_json or None,
    )

    return json.dumps(
        {
            "success": True,
            "signal_id": signal.id,
            "code": code,
            "type": signal.signal_type,
        }
    )


@mcp.tool()
def save_analysis_result(
    code: str,
    analysis_type: str,
    username: str = "dyson",
    stock_name: str = "",
    overall_score: float = None,
    obv_score: float = None,
    vcp_score: float = None,
    rating: str = "",
    current_price: float = None,
    support_price: float = None,
    resistance_price: float = None,
    result_json: str = "",
) -> str:
    """存储分析结果 (UPSERT)。

    Args:
        code: 股票代码
        analysis_type: 分析类型 (deep/technical/llm)
        username: 用户名
        stock_name: 股票名称
        overall_score: 综合评分
        obv_score: OBV评分
        vcp_score: VCP评分
        rating: 评级 (STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL)
        current_price: 当前价格
        support_price: 支撑位
        resistance_price: 阻力位
        result_json: 完整分析结果 JSON
    """
    from services.analysis_service import create_analysis_service

    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    parts = code.split(".", 1)
    if len(parts) != 2:
        return "代码格式错误"

    market, stock_code = parts
    db_market = "A" if market in ("SH", "SZ") else market

    svc = create_analysis_service()
    result = svc.save_result(
        user_id=user_id,
        market=db_market,
        code=stock_code,
        analysis_type=analysis_type,
        stock_name=stock_name or None,
        overall_score=(
            Decimal(str(overall_score)) if overall_score is not None else None
        ),
        obv_score=Decimal(str(obv_score)) if obv_score is not None else None,
        vcp_score=Decimal(str(vcp_score)) if vcp_score is not None else None,
        rating=rating or None,
        current_price=(
            Decimal(str(current_price)) if current_price is not None else None
        ),
        support_price=(
            Decimal(str(support_price)) if support_price is not None else None
        ),
        resistance_price=(
            Decimal(str(resistance_price)) if resistance_price is not None else None
        ),
        result_json=result_json or None,
    )

    return json.dumps(
        {
            "success": True,
            "id": result.id if result else None,
            "code": code,
            "date": date.today().isoformat(),
        }
    )


@mcp.tool()
def create_plan(
    code: str,
    action_type: str,
    username: str = "dyson",
    stock_name: str = "",
    priority: str = "consider",
    entry_price: float = None,
    stop_loss_price: float = None,
    target_price_1: float = None,
    target_price_2: float = None,
    position_size: str = "",
    reason: str = "",
    signal_id: int = None,
    plan_date: str = "",
) -> str:
    """创建操作计划。

    Args:
        code: 股票代码
        action_type: 操作类型 (buy/sell/add/reduce/watch)
        username: 用户名
        stock_name: 股票名称
        priority: 优先级 (must_do/should_do/consider)
        entry_price: 入场价
        stop_loss_price: 止损价
        target_price_1: 目标价1
        target_price_2: 目标价2
        position_size: 仓位大小说明
        reason: 操作理由
        signal_id: 关联的信号ID
        plan_date: 计划日期 (YYYY-MM-DD)
    """
    from services.plan_service import create_plan_service

    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    parts = code.split(".", 1)
    if len(parts) != 2:
        return "代码格式错误"

    market, stock_code = parts
    db_market = "A" if market in ("SH", "SZ") else market

    target_date = (
        datetime.strptime(plan_date, "%Y-%m-%d").date() if plan_date else date.today()
    )

    svc = create_plan_service()
    plan = svc.create_plan(
        user_id=user_id,
        market=db_market,
        code=stock_code,
        action_type=action_type,
        plan_date=target_date,
        stock_name=stock_name or None,
        priority=priority,
        entry_price=Decimal(str(entry_price)) if entry_price is not None else None,
        stop_loss_price=(
            Decimal(str(stop_loss_price)) if stop_loss_price is not None else None
        ),
        target_price_1=(
            Decimal(str(target_price_1)) if target_price_1 is not None else None
        ),
        target_price_2=(
            Decimal(str(target_price_2)) if target_price_2 is not None else None
        ),
        position_size=position_size or None,
        reason=reason or None,
        signal_id=signal_id,
    )

    return json.dumps(
        {
            "success": True,
            "plan_id": plan.id,
            "code": code,
            "action": action_type,
            "date": target_date.isoformat(),
        }
    )


@mcp.tool()
def update_plan_status(
    plan_id: int,
    action: str,
    price: float = None,
    notes: str = "",
) -> str:
    """更新操作计划状态。

    Args:
        plan_id: 计划ID
        action: 操作 (execute/cancel)
        price: 执行价格 (仅 execute 时使用)
        notes: 备注
    """
    from services.plan_service import create_plan_service

    svc = create_plan_service()

    if action == "execute":
        plan = svc.mark_executed(
            plan_id,
            price=Decimal(str(price)) if price is not None else None,
            notes=notes or None,
        )
    elif action == "cancel":
        plan = svc.cancel_plan(plan_id, reason=notes or None)
    else:
        return f"未知操作: {action}，支持 execute/cancel"

    if not plan:
        return f"计划 #{plan_id} 不存在"

    return json.dumps(
        {
            "success": True,
            "plan_id": plan.id,
            "status": plan.status,
        }
    )


@mcp.tool()
def record_signal_feedback(
    signal_id: int,
    action_taken: str,
    username: str = "dyson",
    entry_price: float = None,
    exit_price: float = None,
    outcome: str = "",
    pl_amount: float = None,
    pl_ratio: float = None,
    notes: str = "",
) -> str:
    """记录信号反馈 (用于跟踪信号准确率)。

    Args:
        signal_id: 信号ID
        action_taken: 执行动作 (followed/ignored/partial)
        username: 用户名
        entry_price: 入场价
        exit_price: 出场价
        outcome: 结果 (profit/loss/breakeven/pending)
        pl_amount: 盈亏金额
        pl_ratio: 盈亏比例
        notes: 备注
    """
    from services.signal_service import create_signal_service

    user_id = _get_user_id(username)
    if not user_id:
        return f"用户 {username} 不存在"

    svc = create_signal_service()
    feedback = svc.mark_acted_on(
        signal_id=signal_id,
        user_id=user_id,
        action_taken=action_taken,
        entry_price=Decimal(str(entry_price)) if entry_price is not None else None,
        exit_price=Decimal(str(exit_price)) if exit_price is not None else None,
        outcome=outcome or None,
        pl_amount=Decimal(str(pl_amount)) if pl_amount is not None else None,
        pl_ratio=Decimal(str(pl_ratio)) if pl_ratio is not None else None,
        notes=notes or None,
    )

    return json.dumps(
        {
            "success": True,
            "feedback_id": feedback.id,
            "signal_id": signal_id,
        }
    )


@mcp.tool()
def send_dingtalk_message(
    content: str,
    title: str = "",
    format: str = "text",
    username: str = "dyson",
    message_type: str = "report",
) -> str:
    """发送钉钉消息。

    Args:
        content: 消息内容
        title: 标题 (仅 markdown 格式需要)
        format: 消息格式 (text/markdown)
        username: 用户名 (用于日志)
        message_type: 消息类型 (signal/alert/report/command)
    """
    from services.dingtalk_service import create_dingtalk_service

    user_id = _get_user_id(username)
    svc = create_dingtalk_service()

    if format == "markdown":
        success = svc.send_markdown(
            title=title or "通知",
            text=content,
            user_id=user_id,
            message_type=message_type,
        )
    else:
        success = svc.send_text(
            content=content,
            user_id=user_id,
            message_type=message_type,
        )

    return json.dumps({"success": success})


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    mcp.run()
