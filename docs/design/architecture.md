# 架构设计文档

> Investment Analyzer - 系统架构设计

## 1. 系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer                               │
│                        (main.py)                                │
├─────────────────────────────────────────────────────────────────┤
│                      Service Layer                              │
│           ┌──────────────┬──────────────┐                       │
│           │ SyncService  │ ChartService │                       │
│           └──────────────┴──────────────┘                       │
├─────────────────────────────────────────────────────────────────┤
│                     Business Layer                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐  │
│  │  Analysis  │  │   Charts   │  │  Reports   │  │  Fetchers │  │
│  │  Module    │  │   Module   │  │   Module   │  │   Module  │  │
│  └────────────┘  └────────────┘  └────────────┘  └───────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                       Data Layer                                │
│           ┌──────────────┬──────────────┐                       │
│           │   Database   │    Config    │                       │
│           │ (PostgreSQL) │    (YAML)    │                       │
│           └──────────────┴──────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
              ┌─────▼─────┐      ┌──────▼──────┐
              │  Futu API │      │   akshare   │
              │  (持仓)    │      │   (K线)     │
              └───────────┘      └─────────────┘
```

## 2. 模块设计

### 2.1 CLI Layer (main.py)

职责: 命令行接口，用户交互入口

```python
# 命令组结构
main
├── sync      # 数据同步
│   ├── all
│   ├── positions
│   ├── trades
│   └── klines
├── chart     # 图表生成
│   ├── single
│   ├── watchlist
│   └── positions
├── report    # 报告生成
│   ├── portfolio
│   └── technical
├── account   # 账户管理
│   ├── list
│   └── info
├── import    # 数据导入
│   ├── watchlist
│   ├── positions
│   └── trades
├── db        # 数据库操作
│   ├── check
│   ├── init
│   └── seed
└── config    # 配置管理
    ├── show
    └── users
```

### 2.2 Service Layer (services/)

职责: 业务逻辑编排，协调多模块

```python
# SyncService - 数据同步服务
class SyncService:
    def sync_positions()   # 同步持仓
    def sync_trades()      # 同步交易
    def sync_klines()      # 同步K线
    def sync_all()         # 全量同步

# ChartService - 图表服务
class ChartService:
    def generate_watchlist_charts()   # 关注列表图表
    def generate_position_charts()    # 持仓股票图表
    def generate_charts_for_codes()   # 通用批量生成
```

### 2.3 Business Layer

#### 2.3.1 Analysis Module (analysis/)

```
analysis/
├── __init__.py          # 模块导出
├── technical.py         # 技术分析器
├── portfolio.py         # 组合分析器
└── indicators/          # 技术指标
    ├── base.py          # 基类
    ├── ma.py            # 移动平均
    ├── rsi.py           # RSI
    ├── macd.py          # MACD
    ├── bollinger.py     # 布林带
    ├── obv.py           # OBV
    └── vcp.py           # VCP 形态
```

**设计模式**: 策略模式 + 工厂模式

```python
# 指标基类
class BaseIndicator(ABC):
    @abstractmethod
    def calculate(self, df: DataFrame) -> IndicatorResult: ...

# 使用示例
rsi = RSI(period=14)
result = rsi.calculate(df)
```

#### 2.3.2 Charts Module (charts/)

```
charts/
├── __init__.py
├── generator.py         # 图表生成器
└── styles.py            # 样式配置
```

**设计**: 配置驱动

```python
@dataclass
class ChartConfig:
    ma_periods: list[int]
    show_volume: bool
    figsize: tuple[int, int]

generator = ChartGenerator(style="dark")
generator.generate(df, config=config)
```

#### 2.3.3 Reports Module (reports/)

```
reports/
├── __init__.py
├── generator.py         # 报告生成器
└── templates/           # Jinja2 模板
    ├── portfolio.md.j2
    ├── technical.md.j2
    ├── daily.md.j2
    └── weekly.md.j2
```

**设计**: 模板引擎 + 策略模式

```python
class ReportGenerator:
    def generate_portfolio_report()
    def generate_technical_report()
    def generate_daily_brief()
    def generate_weekly_review()
```

#### 2.3.4 Fetchers Module (fetchers/)

```
fetchers/
├── __init__.py
├── base.py              # 基类和数据类
├── futu_fetcher.py      # 富途 API
└── kline_fetcher.py     # K线数据 (akshare)
```

**设计**: 适配器模式

```python
class BaseFetcher(ABC):
    @abstractmethod
    def fetch(self, code: str, **kwargs) -> FetchResult: ...

class FutuFetcher(BaseFetcher):  # 富途适配器
class KlineFetcher(BaseFetcher): # akshare适配器
```

### 2.4 Data Layer

#### 2.4.1 Database (db/)

```
db/
├── __init__.py
├── database.py          # 连接管理
├── models.py            # ORM 模型
└── migrations/          # SQL 脚本
    └── init_schema.sql
```

**数据模型**:

```
users ─┬─ accounts ─┬─ positions
       │            ├─ trades
       │            └─ account_snapshots
       └─ watchlist

klines (独立表)
sync_logs (同步日志)
```

#### 2.4.2 Config (config/)

```
config/
├── __init__.py
├── settings.py          # 全局设置
├── users.py             # 用户配置加载
└── users.yaml           # 用户配置文件
```

## 3. 数据流

### 3.1 数据同步流程

```
用户请求 → CLI → SyncService → FutuFetcher → 富途API
                     ↓
              数据转换/验证
                     ↓
              Database → PostgreSQL
                     ↓
              SyncLog 记录
```

### 3.2 技术分析流程

```
用户请求 → CLI → KlineFetcher → akshare
                     ↓
              DataFrame 数据
                     ↓
         TechnicalAnalyzer/Indicator
                     ↓
              IndicatorResult
                     ↓
              报告/图表输出
```

### 3.3 报告生成流程

```
用户请求 → CLI → ReportGenerator
                     ↓
         数据获取 (DB/分析结果)
                     ↓
              Jinja2 模板渲染
                     ↓
              输出文件 (MD/JSON/HTML)
```

## 4. 关键设计决策

### 4.1 为什么选择 CLI 而非 Web?

- **简单性**: 无需部署 Web 服务器
- **安全性**: 本地运行，数据不外泄
- **集成性**: 与 Claude Code 天然集成
- **效率**: 开发成本低，迭代快

### 4.2 为什么使用 PostgreSQL?

- **功能丰富**: JSON 支持、窗口函数
- **稳定性**: 生产级数据库
- **可扩展**: 未来可添加复杂查询
- **本地化**: Homebrew 安装简单

### 4.3 为什么分离 Fetcher 模块?

- **可替换**: 可轻松切换数据源
- **可测试**: 便于 Mock 测试
- **关注分离**: 数据获取与业务逻辑分离

### 4.4 指标设计为什么用类而非函数?

- **配置灵活**: 支持不同参数
- **状态管理**: 可缓存中间计算
- **可组合**: 支持指标组合
- **可扩展**: 便于添加新指标

## 5. 扩展点

### 5.1 添加新指标

1. 创建 `analysis/indicators/new_indicator.py`
2. 继承 `BaseIndicator`
3. 实现 `calculate()` 方法
4. 在 `__init__.py` 中导出

### 5.2 添加新数据源

1. 创建 `fetchers/new_fetcher.py`
2. 继承 `BaseFetcher`
3. 实现数据获取和转换
4. 在配置中添加选项

### 5.3 添加新报告类型

1. 创建模板 `reports/templates/new.md.j2`
2. 在 `ReportGenerator` 中添加方法
3. 在 `ReportType` 枚举中添加类型

## 6. 性能考虑

### 6.1 数据库

- 连接池管理 (SQLAlchemy)
- 索引优化 (code, date 复合索引)
- 批量插入 (bulk_save_objects)

### 6.2 图表生成

- 图表样式缓存
- 批量生成并行化 (TODO)
- 按需生成，避免重复

### 6.3 数据获取

- 增量同步减少请求
- 请求失败重试
- 批量获取 K 线

---

*文档版本: 1.0*
*最后更新: 2025-12-14*
