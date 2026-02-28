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

# Default user
DEFAULT_USERNAME = "dyson"

MARKET_NAMES = {"HK": "港股", "US": "美股", "A": "A股"}


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
            from services.dingtalk_service import create_dingtalk_service

            dingtalk = create_dingtalk_service()
            lines = [f"## 数据同步完成 ({date.today()})\n"]
            for name, result in results.items():
                icon = "✅" if result.success else "❌"
                lines.append(f"- {icon} {name}: {result.records_synced}条")
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
            timeout=600,  # 10 min timeout for analysis
            cwd=str(PROJECT_DIR),
        )

        if result.returncode != 0:
            logger.error(f"Claude CLI error: {result.stderr}")
            return f"分析出错: {result.stderr}"

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


def run_post_market(market: str):
    """Post-market analysis via Claude CLI + MCP tools."""
    market_name = MARKET_NAMES.get(market, market)
    logger.info(f"Starting post-market analysis for {market_name}...")

    prompt = f"""
{market_name}盘后分析 ({date.today()}):

1. 用 sync_data 同步最新 {market_name} 数据
2. 用 get_positions 获取 {market} 市场持仓
3. 对每只持仓用 run_technical_analysis 做技术分析
4. 基于 V12 七层决策框架生成信号:
   - 卖出信号: 破止损、技术形态恶化
   - 持有信号: 符合持有条件
   - 关注信号: 关注列表中有买点的标的
5. 用 save_signal 存储每个信号
6. 用 save_analysis_result 存储分析结果
7. 生成明日操作计划，用 create_plan 存储
8. 最后用 send_dingtalk_message 推送分析摘要 (markdown 格式)，包含:
   - 持仓盈亏概览
   - 重要信号
   - 明日操作计划
"""

    output = run_claude_prompt(prompt)
    logger.info(f"Post-market analysis done for {market_name}")


def run_pre_market(market: str):
    """Pre-market briefing via Claude CLI + MCP tools."""
    market_name = MARKET_NAMES.get(market, market)
    logger.info(f"Starting pre-market briefing for {market_name}...")

    prompt = f"""
{market_name}盘前检查 ({date.today()}):

1. 用 get_signals 查看 {market} 市场活跃信号
2. 用 get_plans 查看今日操作计划
3. 用 get_positions 检查 {market} 市场持仓风险
4. 用 get_klines 检查关键持仓的最新 K 线走势
5. 生成盘前简报
6. 用 send_dingtalk_message 推送盘前提醒 (markdown 格式)，包含:
   - 今日操作计划 (按优先级排列)
   - 持仓风险提醒
   - 关键价位提示
"""

    output = run_claude_prompt(prompt)
    logger.info(f"Pre-market briefing done for {market_name}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/cron_workflow.py <phase> [market]")
        print("  phase: sync | pre_market | post_market")
        print("  market: HK | US | A")
        sys.exit(1)

    phase = sys.argv[1]
    market = sys.argv[2] if len(sys.argv) > 2 else None

    # Ensure logs directory exists
    (PROJECT_DIR / "logs").mkdir(exist_ok=True)

    if phase == "sync":
        run_sync()
    elif phase == "post_market":
        if not market:
            print("Error: market required for post_market (HK/US/A)")
            sys.exit(1)
        run_post_market(market)
    elif phase == "pre_market":
        if not market:
            print("Error: market required for pre_market (HK/US/A)")
            sys.exit(1)
        run_pre_market(market)
    else:
        print(f"Unknown phase: {phase}")
        sys.exit(1)


if __name__ == "__main__":
    main()
