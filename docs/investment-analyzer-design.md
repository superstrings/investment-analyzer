# 投资分析自动化系统 - 需求文档与设计方案

> 版本: v1.0  
> 日期: 2025-12-14  
> 作者: Dyson & Claude

---

## 一、项目概述

### 1.1 背景

目前通过手动方式进行投资分析：手工截图K线图、手动整理持仓CSV、在Claude对话中用Prompt生成分析报告。这种方式效率较低，希望构建一套自动化系统来替代手工流程。

### 1.2 目标

构建一套本地化的投资分析自动化系统，实现：
- 自动从富途牛牛获取持仓、成交、账户数据
- 自动获取港股/美股/A股K线数据
- 自动生成K线图（替代手动截图）
- 结合Claude Code进行技术分析和报告生成
- 支持多用户、多账户场景

### 1.3 系统边界

**包含：**
- 数据采集（富途API + 免费行情源）
- 数据存储（PostgreSQL）
- K线图生成
- 技术指标计算（OBV、VCP、均线等）
- Claude Code Skills定义
- 分析报告输出

**不包含（第一阶段）：**
- 实时行情推送
- 自动化交易执行
- Web界面
- 移动端应用

---

## 二、功能需求

### 2.1 用户管理

| 需求ID | 需求描述 | 优先级 |
|--------|---------|--------|
| U-01 | 支持多用户（多个富途平台账号） | P1 |
| U-02 | 每个用户可配置独立的FutuOpenD连接（host:port） | P1 |
| U-03 | 用户交易密码加密存储 | P1 |
| U-04 | 用户数据隔离（用户A无法查看用户B的持仓） | P1 |

### 2.2 账户管理

| 需求ID | 需求描述 | 优先级 |
|--------|---------|--------|
| A-01 | 支持同一用户下多个交易账户（港股/美股/模拟盘） | P1 |
| A-02 | 自动从富途API获取账户列表 | P1 |
| A-03 | 支持真实账户和模拟账户区分 | P2 |

### 2.3 数据采集

| 需求ID | 需求描述 | 数据源 | 优先级 |
|--------|---------|--------|--------|
| D-01 | 获取账户持仓信息 | 富途OpenAPI | P1 |
| D-02 | 获取账户资金信息 | 富途OpenAPI | P1 |
| D-03 | 获取今日成交记录 | 富途OpenAPI | P1 |
| D-04 | 获取历史成交记录 | 富途OpenAPI | P1 |
| D-05 | 获取港股日K线数据 | akshare | P1 |
| D-06 | 获取美股日K线数据 | akshare | P1 |
| D-07 | 获取A股日K线数据 | akshare | P2 |
| D-08 | 数据本地缓存，避免重复拉取 | PostgreSQL | P1 |

### 2.4 关注列表

| 需求ID | 需求描述 | 优先级 |
|--------|---------|--------|
| W-01 | 每个用户维护独立的关注列表 | P1 |
| W-02 | 支持导入现有CSV关注列表 | P1 |
| W-03 | 关注列表支持分组/标签 | P3 |

### 2.5 技术分析

| 需求ID | 需求描述 | 优先级 |
|--------|---------|--------|
| T-01 | 计算移动平均线（MA5/10/20/60/120） | P1 |
| T-02 | 计算OBV（能量潮）指标 | P1 |
| T-03 | 识别VCP（波动收缩形态） | P1 |
| T-04 | 计算MACD指标 | P2 |
| T-05 | 计算RSI指标 | P2 |
| T-06 | 计算布林带 | P2 |

### 2.6 图表生成

| 需求ID | 需求描述 | 优先级 |
|--------|---------|--------|
| C-01 | 生成日K线蜡烛图 | P1 |
| C-02 | K线图叠加均线 | P1 |
| C-03 | K线图叠加成交量 | P1 |
| C-04 | 支持自定义时间范围 | P1 |
| C-05 | 图表输出为PNG格式 | P1 |
| C-06 | 批量生成多只股票图表 | P1 |

### 2.7 报告生成

| 需求ID | 需求描述 | 优先级 |
|--------|---------|--------|
| R-01 | 生成单账户持仓分析报告 | P1 |
| R-02 | 生成多账户汇总报告 | P2 |
| R-03 | 生成技术分析报告（含图表） | P1 |
| R-04 | 报告输出为Markdown格式 | P1 |
| R-05 | 支持报告模板自定义 | P3 |

### 2.8 数据同步

| 需求ID | 需求描述 | 优先级 |
|--------|---------|--------|
| S-01 | 手动触发数据同步 | P1 |
| S-02 | 定时自动同步（如每日收盘后） | P2 |
| S-03 | 同步日志记录 | P2 |

---

## 三、技术架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户层                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   用户 1     │  │   用户 2     │  │   用户 N     │          │
│  │ FutuOpenD    │  │ FutuOpenD    │  │ FutuOpenD    │          │
│  │ :11111      │  │ :11112      │  │ :111XX      │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼─────────────────┼─────────────────┼──────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据采集层                                  │
│  ┌─────────────────────────┐  ┌─────────────────────────┐      │
│  │    Futu Fetcher         │  │    Kline Fetcher        │      │
│  │  • 持仓/成交/账户        │  │  • akshare (港/美/A股)   │      │
│  │  • 需解锁交易密码        │  │  • 免费、无需认证        │      │
│  └───────────┬─────────────┘  └───────────┬─────────────┘      │
└──────────────┼────────────────────────────┼────────────────────┘
               │                            │
               ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据存储层                                  │
│                    ┌─────────────┐                              │
│                    │ PostgreSQL  │                              │
│                    │  • users    │                              │
│                    │  • accounts │                              │
│                    │  • positions│                              │
│                    │  • trades   │                              │
│                    │  • klines   │                              │
│                    │  • watchlist│                              │
│                    └──────┬──────┘                              │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      分析处理层                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ 技术指标计算 │  │  图表生成   │  │  报告生成   │             │
│  │ OBV/VCP/MA  │  │ mplfinance  │  │  Markdown   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Code 层                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Skills                                │   │
│  │  • portfolio_analyzer  - 持仓分析技能                    │   │
│  │  • technical_analyzer  - 技术分析技能                    │   │
│  │  • report_generator    - 报告生成技能                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 技术选型

| 组件 | 技术选择 | 说明 |
|------|---------|------|
| 运行环境 | Mac Mini M4 Pro | 本地部署 |
| 编程语言 | Python 3.11+ | 主要开发语言 |
| 数据库 | PostgreSQL 15+ | 数据持久化 |
| 富途接口 | futu-api | 官方Python SDK |
| 行情数据 | akshare | 免费行情源 |
| 图表库 | mplfinance | K线图生成 |
| ORM | SQLAlchemy | 数据库操作 |
| AI助手 | Claude Code | 分析与报告生成 |
| 网络代理 | 命令行代理 | 访问外部API（如需） |

### 3.3 部署架构

```
Mac Mini M4 Pro
├── Homebrew Services
│   ├── postgresql@15 (port: 5432)
│   └── FutuOpenD × N (ports: 11111, 11112, ...)
│
├── Python Environment
│   ├── venv / conda
│   └── 依赖包
│
├── 项目目录
│   └── ~/investment-analyzer/
│
└── Claude Code
    └── Skills 目录
```

---

## 四、数据库设计

### 4.1 ER图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   users     │       │  accounts   │       │  positions  │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │──1:N─▶│ id (PK)     │──1:N─▶│ id (PK)     │
│ username    │       │ user_id(FK) │       │ account_id  │
│ opend_host  │       │ futu_acc_id │       │ snapshot_dt │
│ opend_port  │       │ name        │       │ market      │
│ ...         │       │ market      │       │ code        │
└─────────────┘       │ type        │       │ qty         │
      │               └─────────────┘       │ ...         │
      │                     │               └─────────────┘
      │                     │
      │                     └──1:N──▶┌─────────────┐
      │                              │   trades    │
      │                              ├─────────────┤
      │                              │ id (PK)     │
      │                              │ account_id  │
      │                              │ trade_date  │
      │                              │ ...         │
      │                              └─────────────┘
      │
      └──1:N──▶┌─────────────┐       ┌─────────────┐
               │  watchlist  │       │   klines    │
               ├─────────────┤       ├─────────────┤
               │ id (PK)     │       │ id (PK)     │
               │ user_id(FK) │       │ market      │
               │ market      │       │ code        │
               │ code        │       │ trade_date  │
               │ ...         │       │ OHLCV       │
               └─────────────┘       │ ...         │
                                     └─────────────┘
                                     (全局共享，无用户关联)
```

### 4.2 表结构定义

#### 4.2.1 users - 用户表

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100),
    opend_host VARCHAR(100) NOT NULL DEFAULT '127.0.0.1',
    opend_port INTEGER NOT NULL DEFAULT 11111,
    trade_password_enc VARCHAR(255),          -- 加密存储
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE users IS '用户表 - 对应富途平台账号';
```

#### 4.2.2 accounts - 交易账户表

```sql
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    futu_acc_id BIGINT NOT NULL,              -- 富途返回的acc_id
    account_name VARCHAR(100),                -- 自定义名称
    account_type VARCHAR(20) NOT NULL,        -- REAL/SIMULATE
    market VARCHAR(10) NOT NULL,              -- HK/US/A
    currency VARCHAR(10) DEFAULT 'HKD',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, futu_acc_id)
);

CREATE INDEX idx_accounts_user ON accounts(user_id);
COMMENT ON TABLE accounts IS '交易账户表 - 一个用户可有多个账户';
```

#### 4.2.3 positions - 持仓表

```sql
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    snapshot_date DATE NOT NULL,
    market VARCHAR(10) NOT NULL,
    code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    qty DECIMAL(18,4) NOT NULL,
    can_sell_qty DECIMAL(18,4),
    cost_price DECIMAL(18,6),
    market_price DECIMAL(18,6),
    market_val DECIMAL(18,2),
    pl_val DECIMAL(18,2),                     -- 盈亏金额
    pl_ratio DECIMAL(10,4),                   -- 盈亏比例
    position_side VARCHAR(10) DEFAULT 'LONG', -- LONG/SHORT
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(account_id, snapshot_date, market, code)
);

CREATE INDEX idx_positions_account_date ON positions(account_id, snapshot_date DESC);
CREATE INDEX idx_positions_code ON positions(market, code);
COMMENT ON TABLE positions IS '持仓快照表 - 每日记录';
```

#### 4.2.4 trades - 成交记录表

```sql
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    deal_id VARCHAR(50) NOT NULL,             -- 富途成交ID
    order_id VARCHAR(50),
    trade_time TIMESTAMP NOT NULL,
    market VARCHAR(10) NOT NULL,
    code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    trd_side VARCHAR(10) NOT NULL,            -- BUY/SELL
    qty DECIMAL(18,4) NOT NULL,
    price DECIMAL(18,6) NOT NULL,
    amount DECIMAL(18,2),
    fee DECIMAL(18,4),
    currency VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(account_id, deal_id)
);

CREATE INDEX idx_trades_account_time ON trades(account_id, trade_time DESC);
CREATE INDEX idx_trades_code ON trades(market, code);
COMMENT ON TABLE trades IS '成交记录表';
```

#### 4.2.5 account_snapshots - 账户快照表

```sql
CREATE TABLE account_snapshots (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    snapshot_date DATE NOT NULL,
    total_assets DECIMAL(18,2),
    cash DECIMAL(18,2),
    market_val DECIMAL(18,2),
    frozen_cash DECIMAL(18,2),
    buying_power DECIMAL(18,2),
    max_power_short DECIMAL(18,2),
    currency VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(account_id, snapshot_date)
);

CREATE INDEX idx_account_snapshots_date ON account_snapshots(account_id, snapshot_date DESC);
COMMENT ON TABLE account_snapshots IS '账户资金快照表';
```

#### 4.2.6 klines - K线数据表

```sql
CREATE TABLE klines (
    id SERIAL PRIMARY KEY,
    market VARCHAR(10) NOT NULL,              -- HK/US/A
    code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open DECIMAL(18,6) NOT NULL,
    high DECIMAL(18,6) NOT NULL,
    low DECIMAL(18,6) NOT NULL,
    close DECIMAL(18,6) NOT NULL,
    volume BIGINT,
    amount DECIMAL(18,2),
    turnover_rate DECIMAL(10,4),
    change_pct DECIMAL(10,4),
    -- 可选：预计算的技术指标
    ma5 DECIMAL(18,6),
    ma10 DECIMAL(18,6),
    ma20 DECIMAL(18,6),
    ma60 DECIMAL(18,6),
    obv BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(market, code, trade_date)
);

CREATE INDEX idx_klines_code_date ON klines(market, code, trade_date DESC);
COMMENT ON TABLE klines IS 'K线数据表 - 全局共享';
```

#### 4.2.7 watchlist - 关注列表表

```sql
CREATE TABLE watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    market VARCHAR(10) NOT NULL,
    code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    group_name VARCHAR(50),                   -- 分组名称
    notes TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, market, code)
);

CREATE INDEX idx_watchlist_user ON watchlist(user_id, is_active);
COMMENT ON TABLE watchlist IS '关注列表表';
```

#### 4.2.8 sync_logs - 同步日志表

```sql
CREATE TABLE sync_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    sync_type VARCHAR(50) NOT NULL,           -- POSITIONS/TRADES/KLINES/...
    status VARCHAR(20) NOT NULL,              -- SUCCESS/FAILED/PARTIAL
    records_count INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sync_logs_user_time ON sync_logs(user_id, created_at DESC);
COMMENT ON TABLE sync_logs IS '数据同步日志表';
```

---

## 五、模块设计

### 5.1 项目目录结构

```
investment-analyzer/
│
├── config/
│   ├── __init__.py
│   ├── settings.py              # 全局配置
│   └── users.yaml               # 用户配置文件
│
├── db/
│   ├── __init__.py
│   ├── database.py              # 数据库连接管理
│   ├── models.py                # SQLAlchemy ORM模型
│   └── migrations/              # 数据库迁移脚本
│       └── init_schema.sql
│
├── fetchers/
│   ├── __init__.py
│   ├── base.py                  # Fetcher基类
│   ├── futu_fetcher.py          # 富途数据采集
│   └── kline_fetcher.py         # K线数据采集(akshare)
│
├── analysis/
│   ├── __init__.py
│   ├── technical.py             # 技术指标计算
│   ├── portfolio.py             # 组合分析
│   └── indicators/
│       ├── __init__.py
│       ├── ma.py                # 均线
│       ├── obv.py               # OBV
│       └── vcp.py               # VCP形态识别
│
├── charts/
│   ├── __init__.py
│   ├── generator.py             # 图表生成器
│   ├── styles.py                # 图表样式配置
│   └── output/                  # 图片输出目录
│
├── reports/
│   ├── __init__.py
│   ├── generator.py             # 报告生成器
│   ├── templates/               # 报告模板
│   │   ├── portfolio.md.j2
│   │   └── technical.md.j2
│   └── output/                  # 报告输出目录
│
├── services/
│   ├── __init__.py
│   ├── user_service.py          # 用户管理服务
│   ├── account_service.py       # 账户管理服务
│   ├── sync_service.py          # 数据同步服务
│   └── analysis_service.py      # 分析服务
│
├── skills/                      # Claude Code Skills
│   ├── portfolio_analyzer/
│   │   └── SKILL.md
│   ├── technical_analyzer/
│   │   └── SKILL.md
│   └── report_generator/
│       └── SKILL.md
│
├── scripts/
│   ├── init_db.py               # 初始化数据库
│   ├── import_csv.py            # 导入现有CSV数据
│   └── daily_sync.py            # 每日同步脚本
│
├── tests/
│   ├── __init__.py
│   ├── test_fetchers.py
│   └── test_analysis.py
│
├── main.py                      # 主入口
├── requirements.txt             # Python依赖
├── README.md                    # 项目说明
└── .env.example                 # 环境变量示例
```

### 5.2 核心模块说明

#### 5.2.1 config - 配置模块

```python
# config/settings.py 主要配置项

# 数据库配置
DATABASE_URL = "postgresql://user:pass@localhost:5432/investment_db"

# 默认FutuOpenD配置
DEFAULT_OPEND_HOST = "127.0.0.1"
DEFAULT_OPEND_PORT = 11111

# K线数据配置
DEFAULT_KLINE_DAYS = 120           # 默认获取120天K线
KLINE_CACHE_HOURS = 4              # K线缓存有效期

# 图表配置
CHART_OUTPUT_DIR = "charts/output"
CHART_DPI = 150
CHART_STYLE = "yahoo"              # mplfinance样式

# 报告配置
REPORT_OUTPUT_DIR = "reports/output"
```

#### 5.2.2 fetchers - 数据采集模块

**FutuFetcher** - 富途数据采集器
- 连接管理（支持多用户多端口）
- 获取账户列表
- 获取持仓
- 获取账户资金
- 获取今日成交
- 获取历史成交
- 解锁交易密码

**KlineFetcher** - K线数据采集器
- 获取港股K线（akshare: stock_hk_daily）
- 获取美股K线（akshare: stock_us_daily）
- 获取A股K线（akshare: stock_zh_a_hist）
- 自动识别市场并获取
- 数据格式标准化

#### 5.2.3 analysis - 分析模块

**Technical** - 技术指标
- 计算MA（5/10/20/60/120）
- 计算OBV
- 计算MACD
- 计算RSI
- 计算布林带
- VCP形态识别

**Portfolio** - 组合分析
- 仓位分析（集中度、配比）
- 盈亏分析
- 风险评估
- 账户汇总

#### 5.2.4 charts - 图表模块

**Generator** - 图表生成器
- 生成K线蜡烛图
- 叠加均线
- 叠加成交量
- 叠加技术指标
- 批量生成
- 自定义样式

#### 5.2.5 services - 服务层

**SyncService** - 数据同步服务
- 同步指定用户的持仓
- 同步指定用户的成交
- 同步关注列表的K线
- 全量同步
- 增量同步
- 同步状态记录

---

## 六、接口设计

### 6.1 内部服务接口

#### 6.1.1 用户服务

```python
class UserService:
    def get_user(self, user_id: int) -> User
    def get_user_by_name(self, username: str) -> User
    def list_users(self, active_only: bool = True) -> List[User]
    def create_user(self, username: str, opend_host: str, opend_port: int) -> User
    def update_user(self, user_id: int, **kwargs) -> User
```

#### 6.1.2 账户服务

```python
class AccountService:
    def get_accounts(self, user_id: int) -> List[Account]
    def sync_accounts_from_futu(self, user_id: int) -> List[Account]
    def get_account_summary(self, account_id: int) -> AccountSummary
    def get_all_accounts_summary(self, user_id: int) -> List[AccountSummary]
```

#### 6.1.3 同步服务

```python
class SyncService:
    def sync_positions(self, user_id: int, account_id: int = None) -> SyncResult
    def sync_trades(self, user_id: int, start_date: str = None, end_date: str = None) -> SyncResult
    def sync_klines(self, codes: List[str], days: int = 120) -> SyncResult
    def sync_all(self, user_id: int) -> SyncResult
```

#### 6.1.4 分析服务

```python
class AnalysisService:
    def analyze_portfolio(self, user_id: int, account_id: int = None) -> PortfolioAnalysis
    def analyze_stock(self, market: str, code: str, days: int = 120) -> StockAnalysis
    def generate_chart(self, market: str, code: str, **options) -> str  # 返回图片路径
    def generate_report(self, user_id: int, report_type: str) -> str    # 返回报告路径
```

### 6.2 命令行接口

```bash
# 数据同步
python main.py sync --user dyson --type all
python main.py sync --user dyson --type positions
python main.py sync --user dyson --type klines --codes "HK.00700,US.NVDA"

# 生成图表
python main.py chart --code HK.00700 --days 120 --indicators ma,obv
python main.py chart --watchlist --user dyson

# 生成报告
python main.py report --user dyson --type portfolio
python main.py report --user dyson --type technical --codes "HK.00700"

# 账户管理
python main.py account list --user dyson
python main.py account sync --user dyson
```

---

## 七、Claude Code Skills 设计

### 7.1 portfolio_analyzer - 持仓分析技能

```markdown
# skills/portfolio_analyzer/SKILL.md

# 投资组合分析师

## 能力描述
分析用户的投资组合，评估仓位配置、风险暴露、盈亏状况。

## 数据来源
- 数据库表: positions, accounts, account_snapshots
- 调用: python main.py report --user {user} --type portfolio

## 分析维度
1. 仓位分析
   - 各市场配比（港股/美股/A股）
   - 单一股票集中度
   - 现金比例
   
2. 盈亏分析
   - 持仓盈亏排名
   - 总体盈亏
   - 盈亏贡献度

3. 风险评估
   - 集中度风险（单一持仓>20%预警）
   - 杠杆率
   - 止损检查

## 输出格式
- 持仓明细表
- 仓位配比饼图
- 风险评分（1-10）
- 操作建议
```

### 7.2 technical_analyzer - 技术分析技能

```markdown
# skills/technical_analyzer/SKILL.md

# 技术分析师

## 能力描述
对个股进行技术分析，识别买卖信号，评估趋势强度。

## 数据来源
- 数据库表: klines
- 图表: charts/output/
- 调用: python main.py chart --code {code} --indicators ma,obv,vcp

## 分析方法
1. 趋势分析
   - MA5/10/20/60 排列
   - 价格与均线位置关系
   
2. 量价分析
   - OBV 趋势
   - 量价配合度
   
3. 形态识别
   - VCP 形态
   - 突破确认

## 评分标准
- 趋势得分（0-100）
- OBV 得分（0-100）
- 形态得分（0-100）
- 综合评分

## 输出格式
- K线图（含指标）
- 技术评分
- 支撑/阻力位
- 操作建议
```

### 7.3 report_generator - 报告生成技能

```markdown
# skills/report_generator/SKILL.md

# 报告生成器

## 能力描述
整合持仓分析和技术分析，生成完整的投资分析报告。

## 报告类型
1. 每日简报
   - 持仓变动
   - 重点关注股票
   - 当日操作建议

2. 周度报告
   - 本周盈亏回顾
   - 技术面变化
   - 下周计划

3. 个股深度报告
   - 基本面概览
   - 技术面详解
   - 买卖点位建议

## 输出格式
- Markdown 文档
- 嵌入图表（K线图）
- 数据表格
```

---

## 八、开发计划

### 8.1 里程碑

| 阶段 | 内容 | 预计时间 |
|------|------|---------|
| **M1: 基础框架** | 项目结构、数据库、配置管理 | 1周 |
| **M2: 数据采集** | 富途Fetcher、K线Fetcher、数据同步 | 1周 |
| **M3: 图表生成** | K线图生成、技术指标叠加 | 1周 |
| **M4: 分析模块** | 技术指标计算、组合分析 | 1周 |
| **M5: Claude Skills** | 技能定义、集成测试 | 1周 |
| **M6: 完善优化** | 多用户测试、文档、优化 | 持续 |

### 8.2 M1 详细任务

- [ ] 创建项目目录结构
- [ ] 配置 PostgreSQL 数据库
- [ ] 编写数据库初始化脚本
- [ ] 实现 SQLAlchemy ORM 模型
- [ ] 实现配置管理（settings.py + users.yaml）
- [ ] 编写 README 和开发文档

### 8.3 M2 详细任务

- [ ] 实现 FutuFetcher 类
  - [ ] 连接管理
  - [ ] 获取账户列表
  - [ ] 获取持仓
  - [ ] 获取成交
  - [ ] 获取账户资金
- [ ] 实现 KlineFetcher 类
  - [ ] 港股K线
  - [ ] 美股K线
  - [ ] A股K线
- [ ] 实现 SyncService
  - [ ] 同步逻辑
  - [ ] 增量更新
  - [ ] 日志记录
- [ ] 导入现有CSV数据脚本

### 8.4 M3 详细任务

- [ ] 安装配置 mplfinance
- [ ] 实现 ChartGenerator 类
  - [ ] 基础K线图
  - [ ] 叠加均线
  - [ ] 叠加成交量
- [ ] 图表样式配置
- [ ] 批量生成功能

### 8.5 M4 详细任务

- [ ] 实现技术指标计算
  - [ ] MA 均线
  - [ ] OBV
  - [ ] MACD
  - [ ] RSI
- [ ] 实现 VCP 形态识别
- [ ] 实现组合分析
  - [ ] 仓位分析
  - [ ] 风险评估

### 8.6 M5 详细任务

- [ ] 编写 portfolio_analyzer SKILL.md
- [ ] 编写 technical_analyzer SKILL.md
- [ ] 编写 report_generator SKILL.md
- [ ] Claude Code 集成测试
- [ ] 报告模板设计

---

## 九、附录

### 9.1 依赖清单

```txt
# requirements.txt

# 数据库
psycopg2-binary>=2.9.0
sqlalchemy>=2.0.0

# 富途API
futu-api>=9.0.0

# 行情数据
akshare>=1.10.0

# 数据处理
pandas>=2.0.0
numpy>=1.24.0

# 图表
mplfinance>=0.12.0
matplotlib>=3.7.0

# 技术指标
ta-lib>=0.4.0  # 可选，需要单独安装底层库

# 工具
pyyaml>=6.0
python-dotenv>=1.0.0
cryptography>=40.0.0  # 密码加密

# 报告
jinja2>=3.1.0

# 开发
pytest>=7.0.0
black>=23.0.0
```

### 9.2 环境变量

```bash
# .env.example

# 数据库
DATABASE_URL=postgresql://localhost/investment_db

# 用户交易密码（每个用户一个环境变量）
FUTU_PWD_DYSON=your_trade_password_here
FUTU_PWD_USER2=another_password_here

# 代理（如需）
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

### 9.3 富途 OpenAPI 关键接口

| 功能 | 接口 | 说明 |
|------|------|------|
| 获取账户列表 | `get_acc_list()` | 返回所有交易账户 |
| 解锁交易 | `unlock_trade(password)` | 解锁后才能查询 |
| 查询持仓 | `position_list_query()` | 返回持仓DataFrame |
| 查询账户资金 | `accinfo_query()` | 返回资金信息 |
| 查询今日成交 | `deal_list_query()` | 返回今日成交 |
| 查询历史成交 | `history_deal_list_query()` | 返回历史成交 |

### 9.4 akshare 关键接口

| 市场 | 接口 | 参数示例 |
|------|------|---------|
| 港股 | `stock_hk_daily(symbol, adjust)` | `("00700", "qfq")` |
| 美股 | `stock_us_daily(symbol, adjust)` | `("NVDA", "qfq")` |
| A股 | `stock_zh_a_hist(symbol, period, adjust)` | `("600519", "daily", "hfq")` |

### 9.5 参考资料

- 富途 OpenAPI 文档: https://openapi.futunn.com/futu-api-doc/
- akshare 文档: https://akshare.akfamily.xyz/
- mplfinance 文档: https://github.com/matplotlib/mplfinance
- Claude Code 文档: https://docs.anthropic.com/

---

*文档结束*
