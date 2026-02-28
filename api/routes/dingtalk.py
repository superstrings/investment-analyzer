"""
DingTalk webhook handler.

Receives messages from DingTalk group robot and processes commands.
Simple queries are handled directly; complex analysis is delegated to Claude CLI.
"""

import asyncio
import json
import logging
from datetime import date

from fastapi import APIRouter, Request

from api.claude_runner import run_claude
from config import settings
from config.prompts import V12_FRAMEWORK_PROMPT
from db.database import get_session
from db.models import User
from services.dingtalk_service import create_dingtalk_service
from services.plan_service import create_plan_service
from services.signal_service import create_signal_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["dingtalk"])


def _get_default_user_id() -> int | None:
    """Get default user ID."""
    with get_session() as session:
        user = session.query(User).filter_by(username=settings.web.default_user).first()
        return user.id if user else None


def _format_positions_summary(user_id: int) -> str:
    """Format positions as markdown for DingTalk."""
    from skills.shared.data_provider import DataProvider

    dp = DataProvider(cache_ttl_seconds=0)
    positions = dp.get_positions(user_id)

    if not positions:
        return "暂无持仓数据"

    lines = ["## 持仓概览\n"]
    total_val = sum(p.market_val for p in positions)
    total_pl = sum(p.pl_val for p in positions)

    for p in positions:
        emoji = "📈" if p.pl_val >= 0 else "📉"
        raw_ratio = float(p.pl_ratio or 0)
        # Futu (HK/US/JP) stores pl_ratio as percentage; A-share as decimal
        pct = raw_ratio if p.market in ("HK", "US", "JP") else raw_ratio * 100
        ratio_str = f"{pct:+.2f}%"
        lines.append(
            f"- {emoji} **{p.full_code}** {p.stock_name}: "
            f"¥{float(p.market_val):,.0f} ({ratio_str})"
        )

    lines.append(f"\n**总市值**: ¥{float(total_val):,.0f}")
    lines.append(f"**总盈亏**: ¥{float(total_pl):+,.0f}")

    return "\n".join(lines)


def _format_signals_summary(user_id: int) -> str:
    """Format active signals as markdown."""
    svc = create_signal_service()
    signals = svc.get_active_signals(user_id)

    if not signals:
        return "暂无活跃信号"

    lines = ["## 今日信号\n"]
    type_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡", "WATCH": "👀"}

    for s in signals[:10]:  # Limit to 10
        emoji = type_emoji.get(s.signal_type, "📊")
        score_str = f" ({float(s.score):.0f}分)" if s.score else ""
        lines.append(
            f"- {emoji} **{s.signal_type}** {s.market}.{s.code} "
            f"{s.stock_name or ''}{score_str}"
        )
        if s.reason:
            lines.append(f"  {s.reason[:80]}")

    return "\n".join(lines)


def _format_plans_summary(user_id: int) -> str:
    """Format today's plans as markdown."""
    svc = create_plan_service()
    plans = svc.get_plans_by_date(user_id, date.today())

    if not plans:
        return "今日暂无操作计划"

    lines = ["## 操作计划\n"]
    priority_emoji = {
        "must_do": "🔴",
        "should_do": "🟡",
        "consider": "🟢",
    }

    for p in plans:
        emoji = priority_emoji.get(p.priority, "📋")
        status_str = f" [{p.status}]" if p.status != "pending" else ""
        lines.append(
            f"- {emoji} **{p.action_type.upper()}** {p.market}.{p.code} "
            f"{p.stock_name or ''}{status_str}"
        )
        if p.entry_price:
            parts = [f"入场:{float(p.entry_price):.2f}"]
            if p.stop_loss_price:
                parts.append(f"止损:{float(p.stop_loss_price):.2f}")
            if p.target_price_1:
                parts.append(f"目标:{float(p.target_price_1):.2f}")
            lines.append(f"  {' | '.join(parts)}")

    return "\n".join(lines)


@router.post("/dingtalk/webhook")
async def dingtalk_webhook(request: Request):
    """Handle incoming DingTalk messages."""
    try:
        payload = await request.json()
    except Exception:
        return {"msgtype": "text", "text": {"content": "无法解析请求"}}

    # Extract message content
    content = payload.get("text", {}).get("content", "").strip()

    if not content:
        return {"msgtype": "text", "text": {"content": "收到空消息"}}

    logger.info(f"DingTalk message: {content}")

    user_id = _get_default_user_id()
    if not user_id:
        return {"msgtype": "text", "text": {"content": "用户未配置"}}

    dingtalk = create_dingtalk_service()

    # === Simple commands (direct DB query, fast response) ===

    if content in ("帮助", "help", "-h", "?"):
        help_text = """## 机器人命令
- **持仓** / 查持仓 / 仓位 — 查看持仓概览
- **信号** / 今日信号 — 查看活跃信号
- **计划** / 今日计划 — 查看操作计划
- **同步** — 触发数据同步
- **分析 HK.00700** — 深度分析 (V12+估值)
- **帮助** / help — 显示本帮助

其他任意文本发送给 AI 处理。"""
        dingtalk.send_markdown("帮助", help_text, user_id=user_id)
        return {"msgtype": "text", "text": {"content": "已发送帮助信息"}}

    if content in ("持仓", "查持仓", "仓位"):
        result = _format_positions_summary(user_id)
        dingtalk.send_markdown("持仓概览", result, user_id=user_id)
        return {"msgtype": "text", "text": {"content": "已发送持仓概览"}}

    if content in ("信号", "今日信号"):
        result = _format_signals_summary(user_id)
        dingtalk.send_markdown("今日信号", result, user_id=user_id)
        return {"msgtype": "text", "text": {"content": "已发送信号列表"}}

    if content in ("计划", "今日计划", "操作计划"):
        result = _format_plans_summary(user_id)
        dingtalk.send_markdown("操作计划", result, user_id=user_id)
        return {"msgtype": "text", "text": {"content": "已发送操作计划"}}

    if content == "同步":
        # Trigger sync in background
        asyncio.create_task(_run_sync_and_notify(user_id, dingtalk))
        return {"msgtype": "text", "text": {"content": "同步已触发，完成后通知"}}

    # === Analysis commands → Claude CLI (background) ===

    if content.startswith("分析"):
        code = content.replace("分析", "").strip()
        if code:
            asyncio.create_task(_run_analysis_and_notify(code, user_id, dingtalk))
            return {
                "msgtype": "text",
                "text": {"content": f"正在分析 {code}，稍后推送结果"},
            }
        else:
            return {
                "msgtype": "text",
                "text": {"content": "请指定股票代码，如: 分析 HK.00700"},
            }

    # === Fallback: send to Claude CLI ===
    asyncio.create_task(_run_claude_and_notify(content, user_id, dingtalk))
    return {"msgtype": "text", "text": {"content": "收到，处理中..."}}


async def _run_sync_and_notify(user_id: int, dingtalk):
    """Run data sync and notify via DingTalk."""
    try:
        from services.sync_service import create_sync_service

        svc = create_sync_service()

        # Run sync in a thread pool since it's blocking
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, lambda: svc.sync_all(user_id, kline_days=30)
        )

        lines = ["## 数据同步完成\n"]
        for k, v in results.items():
            status = "✅" if v.success else "❌"
            lines.append(f"- {status} {k}: {v.records_synced}条")

        dingtalk.send_markdown(
            "同步完成",
            "\n".join(lines),
            user_id=user_id,
            message_type="command",
        )
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        dingtalk.send_text(f"同步失败: {e}", user_id=user_id, message_type="command")


async def _run_analysis_and_notify(code: str, user_id: int, dingtalk):
    """Run stock analysis via Claude CLI and notify."""
    prompt = (
        f"分析 {code}:\n\n"
        f"{V12_FRAMEWORK_PROMPT}\n\n"
        f"请执行:\n"
        f"1. 用 run_technical_analysis 做技术分析\n"
        f"2. 按框架: 估值筛选 → 技术评分 → 信号判定\n"
        f"3. 用 save_signal 存储信号\n"
        f"4. 如技术≥7且估值通过, 评估期权机会, 有则 save_signal(signal_category=\"option\")\n"
        f"5. 简洁总结: 估值、评分X/12、信号、操作建议"
    )

    async def notify(result: str):
        # Truncate for DingTalk limit (20000 chars)
        if len(result) > 3000:
            result = result[:3000] + "\n...(已截断)"
        dingtalk.send_markdown(
            f"分析: {code}",
            result,
            user_id=user_id,
            message_type="report",
        )

    await run_claude(prompt, callback=notify)


async def _run_claude_and_notify(content: str, user_id: int, dingtalk):
    """Run arbitrary Claude prompt and notify."""

    async def notify(result: str):
        if len(result) > 3000:
            result = result[:3000] + "\n...(已截断)"
        dingtalk.send_markdown(
            "回复",
            result,
            user_id=user_id,
            message_type="command",
        )

    await run_claude(content, callback=notify)
