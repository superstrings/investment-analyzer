-- Investment Analyzer Database Schema
-- Version: 1.0.0
-- Date: 2025-12-14
--
-- This script creates all tables for the Investment Analyzer system.
-- Compatible with PostgreSQL 15+
--
-- Usage:
--   psql -d investment_db -f init_schema.sql
--
-- Or via Python:
--   python scripts/init_db.py

-- ============================================================================
-- Drop existing tables (in reverse dependency order)
-- ============================================================================
DROP TABLE IF EXISTS sync_logs CASCADE;
DROP TABLE IF EXISTS watchlist CASCADE;
DROP TABLE IF EXISTS klines CASCADE;
DROP TABLE IF EXISTS account_snapshots CASCADE;
DROP TABLE IF EXISTS trades CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================================================
-- users - 用户表
-- ============================================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100),
    opend_host VARCHAR(100) NOT NULL DEFAULT '127.0.0.1',
    opend_port INTEGER NOT NULL DEFAULT 11111,
    trade_password_enc VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE users IS '用户表 - 对应富途平台账号';
COMMENT ON COLUMN users.username IS '用户名，唯一标识';
COMMENT ON COLUMN users.opend_host IS 'FutuOpenD 主机地址';
COMMENT ON COLUMN users.opend_port IS 'FutuOpenD 端口号';
COMMENT ON COLUMN users.trade_password_enc IS '加密存储的交易密码';

-- ============================================================================
-- accounts - 交易账户表
-- ============================================================================
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    futu_acc_id BIGINT NOT NULL,
    account_name VARCHAR(100),
    account_type VARCHAR(20) NOT NULL,
    market VARCHAR(10) NOT NULL,
    currency VARCHAR(10) DEFAULT 'HKD',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, futu_acc_id)
);

CREATE INDEX idx_accounts_user ON accounts(user_id);

COMMENT ON TABLE accounts IS '交易账户表 - 一个用户可有多个账户';
COMMENT ON COLUMN accounts.futu_acc_id IS '富途返回的账户ID';
COMMENT ON COLUMN accounts.account_type IS '账户类型: REAL/SIMULATE';
COMMENT ON COLUMN accounts.market IS '市场: HK/US/A';

-- ============================================================================
-- positions - 持仓快照表
-- ============================================================================
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    market VARCHAR(10) NOT NULL,
    code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    qty DECIMAL(18,4) NOT NULL,
    can_sell_qty DECIMAL(18,4),
    cost_price DECIMAL(18,6),
    market_price DECIMAL(18,6),
    market_val DECIMAL(18,2),
    pl_val DECIMAL(18,2),
    pl_ratio DECIMAL(10,4),
    position_side VARCHAR(10) DEFAULT 'LONG',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(account_id, snapshot_date, market, code)
);

CREATE INDEX idx_positions_account_date ON positions(account_id, snapshot_date DESC);
CREATE INDEX idx_positions_code ON positions(market, code);

COMMENT ON TABLE positions IS '持仓快照表 - 每日记录';
COMMENT ON COLUMN positions.pl_val IS '盈亏金额';
COMMENT ON COLUMN positions.pl_ratio IS '盈亏比例';
COMMENT ON COLUMN positions.position_side IS '持仓方向: LONG/SHORT';

-- ============================================================================
-- trades - 成交记录表
-- ============================================================================
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    deal_id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50),
    trade_time TIMESTAMP NOT NULL,
    market VARCHAR(10) NOT NULL,
    code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    trd_side VARCHAR(10) NOT NULL,
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
COMMENT ON COLUMN trades.deal_id IS '富途成交ID';
COMMENT ON COLUMN trades.trd_side IS '交易方向: BUY/SELL';

-- ============================================================================
-- account_snapshots - 账户资金快照表
-- ============================================================================
CREATE TABLE account_snapshots (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
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

-- ============================================================================
-- klines - K线数据表 (全局共享)
-- ============================================================================
CREATE TABLE klines (
    id SERIAL PRIMARY KEY,
    market VARCHAR(10) NOT NULL,
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

COMMENT ON TABLE klines IS 'K线数据表 - 全局共享，无用户关联';
COMMENT ON COLUMN klines.market IS '市场: HK/US/A';
COMMENT ON COLUMN klines.ma5 IS '5日均线 (预计算)';
COMMENT ON COLUMN klines.obv IS 'OBV能量潮 (预计算)';

-- ============================================================================
-- watchlist - 关注列表表
-- ============================================================================
CREATE TABLE watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    market VARCHAR(10) NOT NULL,
    code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    group_name VARCHAR(50),
    notes TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, market, code)
);

CREATE INDEX idx_watchlist_user ON watchlist(user_id, is_active);

COMMENT ON TABLE watchlist IS '关注列表表';
COMMENT ON COLUMN watchlist.group_name IS '分组名称';

-- ============================================================================
-- sync_logs - 数据同步日志表
-- ============================================================================
CREATE TABLE sync_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    sync_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    records_count INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sync_logs_user_time ON sync_logs(user_id, created_at DESC);

COMMENT ON TABLE sync_logs IS '数据同步日志表';
COMMENT ON COLUMN sync_logs.sync_type IS '同步类型: POSITIONS/TRADES/KLINES/ALL';
COMMENT ON COLUMN sync_logs.status IS '状态: SUCCESS/FAILED/PARTIAL';

-- ============================================================================
-- Create update timestamp trigger function
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables with updated_at column
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_accounts_updated_at
    BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_klines_updated_at
    BEFORE UPDATE ON klines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_watchlist_updated_at
    BEFORE UPDATE ON watchlist
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Grant permissions (adjust as needed)
-- ============================================================================
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO investment_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO investment_user;

-- ============================================================================
-- Verification
-- ============================================================================
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE'
    AND table_name IN ('users', 'accounts', 'positions', 'trades',
                       'account_snapshots', 'klines', 'watchlist', 'sync_logs');

    IF table_count = 8 THEN
        RAISE NOTICE 'Schema initialization successful: % tables created', table_count;
    ELSE
        RAISE WARNING 'Expected 8 tables, found %', table_count;
    END IF;
END $$;
