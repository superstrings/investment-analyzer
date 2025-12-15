# Investment Analyzer 使用指南

> 完整的投资分析工具使用手册

## 目录

1. [快速开始](#快速开始)
2. [日常工作流](#日常工作流)
3. [数据同步](#数据同步)
4. [深度分析](#深度分析)
5. [Skills 系统](#skills-系统)
6. [Claude 命令](#claude-命令)
7. [CLI 命令参考](#cli-命令参考)

---

## 快速开始

### 环境准备

```bash
# 1. 激活虚拟环境
source .venv/bin/activate

# 2. 确保 FutuOpenD 已启动 (用于同步持仓/交易)
# 3. 确保 PostgreSQL 运行中
```

### 首次使用

```bash
# 初始化数据库
python scripts/init_db.py init

# 同步所有数据
python main.py sync all -u dyson

# 运行深度分析
python main.py deep-analyze -u dyson --market HK
```

---

## 日常工作流

### 盘前分析 (推荐)

```bash
# 1. 更新数据
python main.py sync all -u dyson

# 2. 深度分析所有关注股票
python main.py deep-analyze -u dyson --market HK --batch
python main.py deep-analyze -u dyson --market US --batch

# 3. 查看生成的报告
ls reports/output/
```

### 盘后复盘

```bash
# 1. 同步最新交易记录
python main.py sync trades -u dyson

# 2. 同步最新K线
python main.py sync klines -u dyson

# 3. 查看持仓状态
python main.py account info -u dyson
```

### 使用 Claude 快捷命令

在 Claude Code 中，可以使用以下命令快速操作：

```
/daily-analysis      # 执行每日分析 (盘前/盘后)
/deep-analyze HK     # 深度分析指定市场
/market-summary      # 三市场汇总报告
/sync-all            # 同步所有数据
```

---

## 数据同步

### 数据来源

| 数据类型 | 来源 | 说明 |
|---------|------|------|
| 持仓 | 富途 OpenAPI | 需要 FutuOpenD 运行 |
| 交易记录 | 富途 OpenAPI | 需要 FutuOpenD 运行 |
| 关注列表 | 富途 OpenAPI | 需要 FutuOpenD 运行 |
| K线数据 (HK/US) | 富途 OpenAPI | 需要 FutuOpenD 运行 |
| K线数据 (A股) | akshare | 无需代理 |
| 基本面 (HK) | 富途 OpenAPI | PE/PB/市值等 |
| 基本面 (US/A) | akshare | PE/市值等 |

### 同步命令

```bash
# 同步所有数据
python main.py sync all -u dyson

# 分类同步
python main.py sync positions -u dyson     # 仅持仓
python main.py sync trades -u dyson        # 仅交易
python main.py sync watchlist -u dyson     # 仅关注列表
python main.py sync klines -u dyson        # 仅K线

# 指定股票K线
python main.py sync klines -u dyson --codes "HK.00700,US.NVDA"

# A股K线 (使用 akshare)
python main.py sync klines -u dyson --codes "SZ.300308,SH.601138"
```

### 数据存储

- K线数据: 默认存储 250 天 (支持 MA60 等技术分析)
- 交易记录: 默认同步 365 天历史
- 市场代码映射: A股统一存储为 market="A"

---

## 深度分析

### 分析维度

1. **技术分析** (40%)
   - OBV 趋势: 量价配合、背离检测
   - VCP 形态: 收缩识别、阶段判断

2. **基本面分析** (30%)
   - PE/PB 估值
   - 市值规模
   - 52周价格区间

3. **行业分析** (20%)
   - 行业趋势
   - 政策影响

4. **消息分析** (10%)
   - 近期新闻
   - 市场情绪

### 评分系统

| 评分区间 | 评级 | 建议 |
|---------|------|------|
| 60+ | Buy | 可考虑买入 |
| 40-59 | Hold | 持有观望 |
| < 40 | Sell | 建议卖出 |

### 使用命令

```bash
# 单只股票深度分析
python main.py deep-analyze -u dyson -c HK.00700

# 按市场批量分析 (关注列表 + 持仓)
python main.py deep-analyze -u dyson -m HK --save
python main.py deep-analyze -u dyson -m US --save
python main.py deep-analyze -u dyson -m A --save

# 多只股票分析
python main.py deep-analyze -u dyson --codes "HK.00700,HK.00981" --save
```

### 输出报告

报告存储在 `reports/output/` 目录：

```
reports/output/
├── deep_analysis_HK_00700_2025-12-15_120000.md  # 单只股票报告
├── deep_analysis_HK_2025-12-15_120000.md        # 港股市场报告
├── deep_analysis_US_2025-12-15_120000.md        # 美股市场报告
├── deep_analysis_A_2025-12-15_120000.md         # A股市场报告
└── deep_analysis_batch_2025-12-15_120000.md     # 自定义批量报告
```

---

## Skills 系统

### 可用 Skills

| Skill | 用途 | 命令 |
|-------|------|------|
| analyst | 股票分析 (OBV + VCP) | `skill run analyst` |
| risk_controller | 风险监控 | `skill run risk` |
| trading_coach | 交易指导 | `skill run coach` |
| market_observer | 市场观察 | `skill run market` |
| deep_analyzer | 深度分析 | `deep-analyze` |

### 运行 Skill

```bash
# 查看可用 skills
python main.py skill list

# 运行 analyst skill
python main.py skill run analyst -u dyson --market HK

# 运行 risk skill
python main.py skill run risk -u dyson
```

---

## Claude 命令

在 Claude Code 对话中可使用以下快捷命令：

### 数据操作

| 命令 | 说明 |
|------|------|
| `/sync-all` | 同步所有数据 (持仓+交易+关注+K线) |
| `/sync-data [type]` | 同步指定类型数据 |

### 分析命令

| 命令 | 说明 |
|------|------|
| `/daily-analysis` | 每日分析 (盘前/盘后自动识别) |
| `/deep-analyze [market]` | 深度分析指定市场 |
| `/market-summary` | 三市场汇总分析 |
| `/analyze-portfolio` | 持仓分析 |

### 图表命令

| 命令 | 说明 |
|------|------|
| `/gen-chart [code]` | 生成单只股票K线图 |

### 开发命令

| 命令 | 说明 |
|------|------|
| `/init-session` | 初始化开发会话 |
| `/commit-work` | 提交工作并更新进度 |
| `/run-tests` | 运行测试 |

---

## CLI 命令参考

### 主命令

```bash
python main.py --help
```

### sync 命令组

```bash
python main.py sync --help

# 子命令
python main.py sync all -u USER          # 同步所有
python main.py sync positions -u USER    # 同步持仓
python main.py sync trades -u USER       # 同步交易
python main.py sync watchlist -u USER    # 同步关注
python main.py sync klines -u USER       # 同步K线
```

### deep-analyze 命令

```bash
python main.py deep-analyze --help

# 选项
-u, --user      用户名 (必需)
-c, --code      股票代码 (如 HK.00700)
--codes         股票代码列表 (逗号分隔)
-m, --market    市场代码 (HK/US/A) - 批量分析该市场所有关注股票
--no-web        不获取网络数据 (仅技术分析)
-o, --output    输出文件路径
-s, --save      自动保存到 reports/output/
```

### chart 命令组

```bash
python main.py chart --help

# 子命令
python main.py chart single --code CODE --days 120
python main.py chart positions -u USER
python main.py chart watchlist -u USER
```

### report 命令组

```bash
python main.py report --help

# 子命令
python main.py report portfolio -u USER
python main.py report technical -u USER --codes "CODE1,CODE2"
```

### export 命令组

```bash
python main.py export --help

# 子命令
python main.py export positions -u USER --format csv
python main.py export trades -u USER --format excel
python main.py export klines --codes "HK.00700" --format json
```

### account 命令组

```bash
python main.py account --help

# 子命令
python main.py account list -u USER
python main.py account info -u USER
```

---

## 常见问题

### Q: A股K线数据为空？

A: A股数据存储时使用 market="A"，查询时会自动映射 SH/SZ -> A。确保已运行 K线同步：

```bash
python main.py sync klines -u dyson --codes "SZ.300308"
```

### Q: 富途API无权限？

A: 部分数据需要相应的行情权限。基本面数据会自动降级使用 akshare。

### Q: 如何更新关注列表？

A: 在富途牛牛客户端修改后，运行同步命令：

```bash
python main.py sync watchlist -u dyson
```

---

*最后更新: 2025-12-15*
