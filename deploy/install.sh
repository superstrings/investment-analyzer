#!/bin/bash
# Investment Analyzer 部署脚本
# 安装 launchd 服务和 crontab

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$PROJECT_DIR/.venv/bin/python"
PLIST_NAME="com.dyson.investment-analyzer"
PLIST_SRC="$PROJECT_DIR/deploy/$PLIST_NAME.plist"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

echo "Investment Analyzer 部署"
echo "========================"
echo "项目目录: $PROJECT_DIR"
echo ""

# 1. Install dependencies
echo "[1/4] 安装依赖..."
cd "$PROJECT_DIR"
$VENV -m pip install -e ".[web,mcp]" -q
echo "  依赖安装完成"

# 2. Initialize database
echo "[2/4] 初始化数据库..."
$VENV -c "from db import init_db; init_db(); print('  数据库表已创建')"

# 3. Install launchd plist (FastAPI server)
echo "[3/4] 安装 launchd 服务..."
if [ -f "$PLIST_DST" ]; then
    launchctl unload "$PLIST_DST" 2>/dev/null || true
fi
cp "$PLIST_SRC" "$PLIST_DST"
launchctl load "$PLIST_DST"
echo "  服务已安装: $PLIST_NAME"
echo "  管理: launchctl start/stop $PLIST_NAME"

# 4. Install crontab
echo "[4/4] 配置 crontab..."
CRON_MARKER="# investment-analyzer"
CRON_JOBS="
$CRON_MARKER
# 数据同步 08:00
0 8 * * 1-5 cd $PROJECT_DIR && $VENV scripts/cron_workflow.py sync >> logs/cron.log 2>&1
# 港股盘前 08:30 / 盘后 16:30
30 8 * * 1-5 cd $PROJECT_DIR && $VENV scripts/cron_workflow.py pre_market HK >> logs/cron.log 2>&1
30 16 * * 1-5 cd $PROJECT_DIR && $VENV scripts/cron_workflow.py post_market HK >> logs/cron.log 2>&1
# A股盘前 09:00 / 盘后 15:30
0 9 * * 1-5 cd $PROJECT_DIR && $VENV scripts/cron_workflow.py pre_market A >> logs/cron.log 2>&1
30 15 * * 1-5 cd $PROJECT_DIR && $VENV scripts/cron_workflow.py post_market A >> logs/cron.log 2>&1
# 美股盘前 20:00 / 盘后 05:00
0 20 * * 1-5 cd $PROJECT_DIR && $VENV scripts/cron_workflow.py pre_market US >> logs/cron.log 2>&1
0 5 * * 2-6 cd $PROJECT_DIR && $VENV scripts/cron_workflow.py post_market US >> logs/cron.log 2>&1
$CRON_MARKER-end
"

# Remove old cron jobs and add new ones
(crontab -l 2>/dev/null | sed "/$CRON_MARKER/,/$CRON_MARKER-end/d"; echo "$CRON_JOBS") | crontab -
echo "  crontab 已配置"

echo ""
echo "部署完成!"
echo "  Web 服务: http://localhost:8000"
echo "  API 文档: http://localhost:8000/docs"
echo "  日志: $PROJECT_DIR/logs/"
