"""
Analysis results API routes.

Provides:
- GET /api/analysis — paginated list with market/code filters
- POST /api/stock/{market}/{code}/analyze — trigger Claude analysis
- GET /api/stock/{market}/{code}/analysis — latest analysis for a stock
"""

import asyncio
import json
import logging
import re
from datetime import date

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from db.database import get_session
from db.models import User
from services.analysis_service import create_analysis_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analysis"])


def _resolve_user_id(username: str) -> int | None:
    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        return user.id if user else None


@router.get("/api/analysis")
async def api_analysis_results(
    username: str = Depends(get_current_user),
    market: str = "",
    code: str = "",
    offset: int = 0,
    limit: int = 20,
):
    """Get paginated analysis results with optional market/code filter."""
    user_id = _resolve_user_id(username)
    if not user_id:
        return {"error": "User not found"}

    svc = create_analysis_service()
    results, total = svc.get_results_paginated(
        user_id,
        market=market or None,
        code=code or None,
        offset=offset,
        limit=limit,
    )
    stats = svc.get_stats(user_id)

    data = []
    for r in results:
        summary = _make_summary(r.result_json)
        data.append(
            {
                "id": r.id,
                "code": f"{r.market}.{r.code}",
                "name": r.stock_name or "",
                "type": r.analysis_type,
                "overall_score": float(r.overall_score) if r.overall_score else None,
                "obv_score": float(r.obv_score) if r.obv_score else None,
                "vcp_score": float(r.vcp_score) if r.vcp_score else None,
                "rating": r.rating,
                "price": float(r.current_price) if r.current_price else None,
                "support": float(r.support_price) if r.support_price else None,
                "resistance": float(r.resistance_price) if r.resistance_price else None,
                "analysis_date": r.analysis_date.isoformat(),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "summary": summary,
                "result_json": r.result_json or "",
            }
        )

    return {
        "results": data,
        "total": total,
        "offset": offset,
        "limit": limit,
        "stats": stats,
    }


@router.post("/api/stock/{market}/{code}/analyze")
async def api_trigger_analysis(
    market: str,
    code: str,
    username: str = Depends(get_current_user),
):
    """Trigger V12 analysis for a stock via Claude CLI (background task)."""
    user_id = _resolve_user_id(username)
    if not user_id:
        return {"error": "User not found"}

    asyncio.create_task(_run_analysis(market, code, user_id))
    return {"status": "started", "code": f"{market}.{code}"}


@router.get("/api/stock/{market}/{code}/analysis")
async def api_stock_latest_analysis(
    market: str,
    code: str,
    username: str = Depends(get_current_user),
):
    """Get the latest analysis result for a stock."""
    user_id = _resolve_user_id(username)
    if not user_id:
        return {"error": "User not found"}

    svc = create_analysis_service()
    # Try exact market first, then fallback for A-share (SH/SZ vs A)
    r = svc.get_latest_result(user_id, market, code)
    if not r and market in ("SH", "SZ"):
        r = svc.get_latest_result(user_id, "A", code)
    elif not r and market == "A":
        for m in ("SH", "SZ"):
            r = svc.get_latest_result(user_id, m, code)
            if r:
                break

    if not r:
        return {"result": None}

    return {
        "result": {
            "id": r.id,
            "code": f"{r.market}.{r.code}",
            "name": r.stock_name or "",
            "type": r.analysis_type,
            "overall_score": float(r.overall_score) if r.overall_score else None,
            "obv_score": float(r.obv_score) if r.obv_score else None,
            "vcp_score": float(r.vcp_score) if r.vcp_score else None,
            "rating": r.rating,
            "price": float(r.current_price) if r.current_price else None,
            "support": float(r.support_price) if r.support_price else None,
            "resistance": float(r.resistance_price) if r.resistance_price else None,
            "analysis_date": r.analysis_date.isoformat(),
            "result_json": r.result_json or "",
        }
    }


async def _run_analysis(market: str, code: str, user_id: int):
    """Background task: run Claude analysis and save result to DB."""
    from api.claude_runner import run_claude
    from config.prompts import V12_FRAMEWORK_PROMPT

    full_code = f"{market}.{code}"

    prompt = (
        f"分析 {full_code}:\n\n"
        f"{V12_FRAMEWORK_PROMPT}\n\n"
        f"请执行:\n"
        f"1. 用 run_technical_analysis 做技术分析\n"
        f"2. 按框架: 估值筛选 → 技术评分 → 信号判定\n"
        f"3. 用 save_signal 存储信号\n"
        f"4. 如技术≥7且估值通过, 评估期权机会, 有则 save_signal(signal_category=\"option\")\n"
        f"5. 用 save_analysis_result 存储分析结果 (包含 overall_score, obv_score, vcp_score, rating, result_json 完整分析文本)\n"
        f"6. 简洁总结: 估值、评分X/12、信号、操作建议"
    )

    async def on_complete(result: str):
        _fallback_save_result(market, code, user_id, result)

    await run_claude(prompt, callback=on_complete)


def _fallback_save_result(market: str, code: str, user_id: int, text: str):
    """Fallback: parse Claude output and save to DB if MCP didn't already save."""
    svc = create_analysis_service()

    # Check if MCP already saved a result for today
    existing = svc.get_latest_result(user_id, market, code)
    if existing and existing.analysis_date == date.today():
        # MCP already saved — update result_json if it's empty
        if not existing.result_json and text:
            svc.save_result(
                user_id=user_id,
                market=market,
                code=code,
                analysis_type=existing.analysis_type,
                analysis_date=date.today(),
                stock_name=existing.stock_name,
                overall_score=existing.overall_score,
                obv_score=existing.obv_score,
                vcp_score=existing.vcp_score,
                rating=existing.rating,
                current_price=existing.current_price,
                support_price=existing.support_price,
                resistance_price=existing.resistance_price,
                result_json=text,
            )
        return

    # MCP didn't save — try to parse scores from text
    overall = _extract_score(text)
    rating = _extract_rating(text)

    svc.save_result(
        user_id=user_id,
        market=market,
        code=code,
        analysis_type="llm",
        analysis_date=date.today(),
        overall_score=overall,
        rating=rating,
        result_json=text,
    )


def _extract_score(text: str):
    """Try to extract overall score like '8/12' or '评分: 8' from text."""
    from decimal import Decimal

    m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*12", text)
    if m:
        return Decimal(m.group(1))
    m = re.search(r"评分[：:]\s*(\d+(?:\.\d+)?)", text)
    if m:
        return Decimal(m.group(1))
    return None


def _extract_rating(text: str) -> str | None:
    """Try to extract rating keyword from text."""
    for kw in ["极强加仓", "强势持有", "观望", "减仓", "止损"]:
        if kw in text:
            return kw
    return None


def _strip_markdown(text: str) -> str:
    """Strip Markdown syntax to produce clean plain text for summaries."""
    # Remove headers
    s = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers
    s = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", s)
    # Remove inline code
    s = re.sub(r"`([^`]+)`", r"\1", s)
    # Remove links [text](url) → text
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    # Remove list markers
    s = re.sub(r"^[\s]*[-*+]\s+", "", s, flags=re.MULTILINE)
    s = re.sub(r"^[\s]*\d+\.\s+", "", s, flags=re.MULTILINE)
    # Collapse multiple newlines to separator
    s = re.sub(r"\n{2,}", " | ", s)
    # Single newlines to space
    s = re.sub(r"\n", " ", s)
    # Collapse multiple spaces
    s = re.sub(r" {2,}", " ", s)
    return s.strip()


def _make_summary(result_json: str | None) -> str:
    """Extract a human-readable summary from result_json."""
    if not result_json:
        return ""
    # Error messages
    if result_json.startswith(("分析出错", "分析超时", "分析失败", "Claude CLI")):
        return result_json
    # Try JSON parse
    try:
        data = json.loads(result_json)
    except (json.JSONDecodeError, TypeError):
        return result_json[:300]
    # Extract v12 analysis fields
    v12 = data.get("v12_analysis") or data.get("v12_framework")
    if v12:
        labels = {
            "1_trend": "趋势", "2_volume_price": "量价", "3_key_levels": "关键价位",
            "4_pattern": "形态", "5_timing": "时机", "6_risk": "风险", "7_position": "仓位",
            "trend": "趋势", "volume_price": "量价", "key_levels": "关键价位",
            "pattern": "形态", "timing": "时机", "risk": "风险", "position": "仓位",
        }
        parts = []
        for k, v in v12.items():
            label = labels.get(k, k)
            parts.append(f"{label}: {v}")
        return " | ".join(parts)
    # Markdown analysis text — strip syntax and truncate
    analysis_text = data.get("analysis")
    if analysis_text and isinstance(analysis_text, str):
        clean = _strip_markdown(analysis_text)
        return clean[:300] + ("..." if len(clean) > 300 else "")
    # Generic JSON — return first-level string values
    parts = []
    for k, v in data.items():
        if isinstance(v, str):
            parts.append(v)
    return " | ".join(parts) if parts else result_json[:300]
