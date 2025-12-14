# 数据库设计文档

> Investment Analyzer - PostgreSQL 数据库设计

## 1. 数据库概览

- **数据库**: PostgreSQL 17
- **ORM**: SQLAlchemy 2.0
- **数据库名**: investment_db

## 2. ER 图

```
┌──────────┐     ┌──────────────┐     ┌────────────┐
│  users   │────<│   accounts   │────<│  positions │
└──────────┘     └──────────────┘     └────────────┘
     │                  │
     │                  ├────<┌──────────────────────┐
     │                  │     │       trades         │
     │                  │     └──────────────────────┘
     │                  │
     │                  └────<┌──────────────────────┐
     │                        │  account_snapshots   │
     │                        └──────────────────────┘
     │
     └────<┌──────────────┐
           │  watchlist   │
           └──────────────┘

┌──────────────┐     ┌──────────────┐
│    klines    │     │  sync_logs   │
└──────────────┘     └──────────────┘
```

## 3. 表结构详情

### 3.1 users (用户表)

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 用户ID |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
```

### 3.2 accounts (账户表)

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 账户ID |
| user_id | INTEGER | FK(users.id) | 用户ID |
| account_id | VARCHAR(50) | NOT NULL | 富途账户ID |
| account_type | VARCHAR(20) | | 账户类型 |
| market | VARCHAR(10) | | 市场 (HK/US) |
| currency | VARCHAR(10) | | 币种 |
| security_firm | VARCHAR(50) | | 券商 |
| created_at | TIMESTAMP | | 创建时间 |

```sql
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    account_id VARCHAR(50) NOT NULL,
    account_type VARCHAR(20),
    market VARCHAR(10),
    currency VARCHAR(10),
    security_firm VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_accounts_user ON accounts(user_id);
```

### 3.3 positions (持仓表)

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 持仓ID |
| account_id | INTEGER | FK(accounts.id) | 账户ID |
| code | VARCHAR(20) | NOT NULL | 股票代码 |
| market | VARCHAR(10) | | 市场 |
| stock_name | VARCHAR(100) | | 股票名称 |
| qty | DECIMAL(18,4) | | 持仓数量 |
| can_sell_qty | DECIMAL(18,4) | | 可卖数量 |
| cost_price | DECIMAL(18,4) | | 成本价 |
| market_price | DECIMAL(18,4) | | 市场价 |
| market_val | DECIMAL(18,4) | | 市值 |
| pl_val | DECIMAL(18,4) | | 盈亏金额 |
| pl_ratio | DECIMAL(10,4) | | 盈亏比例 |
| position_side | VARCHAR(10) | | 多空方向 |
| currency | VARCHAR(10) | | 币种 |
| updated_at | TIMESTAMP | | 更新时间 |

```sql
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    code VARCHAR(20) NOT NULL,
    market VARCHAR(10),
    stock_name VARCHAR(100),
    qty DECIMAL(18,4),
    can_sell_qty DECIMAL(18,4),
    cost_price DECIMAL(18,4),
    market_price DECIMAL(18,4),
    market_val DECIMAL(18,4),
    pl_val DECIMAL(18,4),
    pl_ratio DECIMAL(10,4),
    position_side VARCHAR(10),
    currency VARCHAR(10),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_positions_account ON positions(account_id);
CREATE INDEX idx_positions_code ON positions(code);
```

### 3.4 trades (交易记录表)

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 交易ID |
| account_id | INTEGER | FK(accounts.id) | 账户ID |
| deal_id | VARCHAR(50) | UNIQUE | 成交ID |
| order_id | VARCHAR(50) | | 订单ID |
| code | VARCHAR(20) | | 股票代码 |
| market | VARCHAR(10) | | 市场 |
| stock_name | VARCHAR(100) | | 股票名称 |
| trd_side | VARCHAR(10) | | 交易方向 |
| deal_qty | DECIMAL(18,4) | | 成交数量 |
| deal_price | DECIMAL(18,4) | | 成交价格 |
| deal_amt | DECIMAL(18,4) | | 成交金额 |
| create_time | TIMESTAMP | | 成交时间 |
| counter_broker_id | INTEGER | | 对手券商 |
| counter_broker_name | VARCHAR(100) | | 对手名称 |

```sql
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    deal_id VARCHAR(50) UNIQUE,
    order_id VARCHAR(50),
    code VARCHAR(20),
    market VARCHAR(10),
    stock_name VARCHAR(100),
    trd_side VARCHAR(10),
    deal_qty DECIMAL(18,4),
    deal_price DECIMAL(18,4),
    deal_amt DECIMAL(18,4),
    create_time TIMESTAMP,
    counter_broker_id INTEGER,
    counter_broker_name VARCHAR(100)
);
CREATE INDEX idx_trades_account ON trades(account_id);
CREATE INDEX idx_trades_code ON trades(code);
CREATE INDEX idx_trades_time ON trades(create_time);
```

### 3.5 account_snapshots (账户快照表)

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 快照ID |
| account_id | INTEGER | FK(accounts.id) | 账户ID |
| snapshot_date | DATE | | 快照日期 |
| total_assets | DECIMAL(18,4) | | 总资产 |
| cash | DECIMAL(18,4) | | 现金 |
| market_val | DECIMAL(18,4) | | 市值 |
| frozen_cash | DECIMAL(18,4) | | 冻结资金 |
| buying_power | DECIMAL(18,4) | | 购买力 |
| max_withdraw | DECIMAL(18,4) | | 最大可取 |
| currency | VARCHAR(10) | | 币种 |

```sql
CREATE TABLE account_snapshots (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    snapshot_date DATE,
    total_assets DECIMAL(18,4),
    cash DECIMAL(18,4),
    market_val DECIMAL(18,4),
    frozen_cash DECIMAL(18,4),
    buying_power DECIMAL(18,4),
    max_withdraw DECIMAL(18,4),
    currency VARCHAR(10)
);
CREATE INDEX idx_snapshots_account_date ON account_snapshots(account_id, snapshot_date);
```

### 3.6 klines (K线数据表)

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | K线ID |
| code | VARCHAR(20) | NOT NULL | 股票代码 |
| market | VARCHAR(10) | | 市场 |
| trade_date | DATE | NOT NULL | 交易日期 |
| open | DECIMAL(18,4) | | 开盘价 |
| high | DECIMAL(18,4) | | 最高价 |
| low | DECIMAL(18,4) | | 最低价 |
| close | DECIMAL(18,4) | | 收盘价 |
| volume | BIGINT | | 成交量 |
| turnover | DECIMAL(24,4) | | 成交额 |
| change_pct | DECIMAL(10,4) | | 涨跌幅 |
| amplitude | DECIMAL(10,4) | | 振幅 |
| turnover_rate | DECIMAL(10,4) | | 换手率 |
| ma5 | DECIMAL(18,4) | | 5日均线 |
| ma10 | DECIMAL(18,4) | | 10日均线 |
| ma20 | DECIMAL(18,4) | | 20日均线 |
| ma60 | DECIMAL(18,4) | | 60日均线 |

```sql
CREATE TABLE klines (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    market VARCHAR(10),
    trade_date DATE NOT NULL,
    open DECIMAL(18,4),
    high DECIMAL(18,4),
    low DECIMAL(18,4),
    close DECIMAL(18,4),
    volume BIGINT,
    turnover DECIMAL(24,4),
    change_pct DECIMAL(10,4),
    amplitude DECIMAL(10,4),
    turnover_rate DECIMAL(10,4),
    ma5 DECIMAL(18,4),
    ma10 DECIMAL(18,4),
    ma20 DECIMAL(18,4),
    ma60 DECIMAL(18,4),
    UNIQUE(code, trade_date)
);
CREATE INDEX idx_klines_code_date ON klines(code, trade_date);
```

### 3.7 watchlist (关注列表表)

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | ID |
| user_id | INTEGER | FK(users.id) | 用户ID |
| code | VARCHAR(20) | NOT NULL | 股票代码 |
| market | VARCHAR(10) | | 市场 |
| stock_name | VARCHAR(100) | | 股票名称 |
| notes | TEXT | | 备注 |
| created_at | TIMESTAMP | | 创建时间 |

```sql
CREATE TABLE watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    code VARCHAR(20) NOT NULL,
    market VARCHAR(10),
    stock_name VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, code)
);
CREATE INDEX idx_watchlist_user ON watchlist(user_id);
```

### 3.8 sync_logs (同步日志表)

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 日志ID |
| user_id | INTEGER | FK(users.id) | 用户ID |
| sync_type | VARCHAR(50) | | 同步类型 |
| status | VARCHAR(20) | | 状态 |
| records_synced | INTEGER | | 同步记录数 |
| error_message | TEXT | | 错误信息 |
| started_at | TIMESTAMP | | 开始时间 |
| completed_at | TIMESTAMP | | 完成时间 |

```sql
CREATE TABLE sync_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    sync_type VARCHAR(50),
    status VARCHAR(20),
    records_synced INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
CREATE INDEX idx_sync_logs_user ON sync_logs(user_id);
CREATE INDEX idx_sync_logs_type ON sync_logs(sync_type);
```

## 4. SQLAlchemy 模型

### 4.1 模型定义位置

`db/models.py`

### 4.2 关系映射

```python
class User(Base):
    accounts = relationship("Account", back_populates="user")
    watchlist = relationship("Watchlist", back_populates="user")

class Account(Base):
    user = relationship("User", back_populates="accounts")
    positions = relationship("Position", back_populates="account")
    trades = relationship("Trade", back_populates="account")
    snapshots = relationship("AccountSnapshot", back_populates="account")

class Position(Base):
    account = relationship("Account", back_populates="positions")
```

## 5. 数据库操作

### 5.1 初始化

```bash
# 创建数据库
python scripts/init_db.py create-db

# 初始化表
python scripts/init_db.py init

# 填充测试数据
python scripts/init_db.py seed
```

### 5.2 连接管理

```python
from db import get_session, engine

# 使用 session
with get_session() as session:
    users = session.query(User).all()

# 使用 engine
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
```

## 6. 索引策略

| 表 | 索引 | 说明 |
|-----|------|------|
| positions | (account_id) | 按账户查询持仓 |
| positions | (code) | 按股票代码查询 |
| trades | (account_id) | 按账户查询交易 |
| trades | (code) | 按股票代码查询 |
| trades | (create_time) | 按时间范围查询 |
| klines | (code, trade_date) | K线唯一约束和查询 |
| watchlist | (user_id) | 按用户查询关注列表 |
| sync_logs | (user_id) | 按用户查询日志 |

## 7. 数据迁移

迁移脚本位于: `db/migrations/`

```bash
# 运行迁移
python scripts/init_db.py migrate
```

---

*文档版本: 1.0*
*最后更新: 2025-12-14*
