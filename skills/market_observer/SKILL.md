# Market Observer Skill

市场观察员技能 - 盘前分析、盘后总结、板块轮动、情绪指数

## 概述

Market Observer Skill 是投资分析系统的市场监测模块，包含四大核心功能：
1. **盘前分析** (PreMarketAnalyzer) - 隔夜市场、重大事件、交易准备
2. **盘后总结** (PostMarketSummarizer) - 今日复盘、盈亏统计、经验教训
3. **板块轮动** (SectorRotationAnalyzer) - 强弱板块、资金流向、轮动信号
4. **情绪指数** (SentimentMeter) - 市场情绪、VIX 解读、交易建议

## 功能清单

### 1. 盘前分析

- 隔夜全球市场回顾 (美股、欧股、商品、汇率)
- 今日重大事件提醒 (财报、经济数据、政策)
- 持仓股票盘前动态
- 关注列表事件检测
- 风险预警生成
- 今日交易重点提示

### 2. 盘后总结

- 今日组合盈亏统计
- 市场指数表现
- 持仓个股涨跌排行
- 今日交易明细汇总
- 异动股票提醒
- 明日关注重点
- 经验教训总结

### 3. 板块轮动

- 强势板块 Top 5
- 弱势板块预警
- 资金流向监控
- 轮动信号检测
- 市场风格判断
- 板块配置建议

### 4. 情绪指数

- 市场情绪评分 (0-100)
- 情绪等级判定 (极度恐惧到极度贪婪)
- 多维度指标分析
- VIX 指数解读
- 交易策略建议

## 使用方式

### Python API

```python
from skills.market_observer import MarketObserver, generate_observation_report
from skills.shared import DataProvider, SkillContext

# 方式一：使用快捷函数
report = generate_observation_report(
    user_id=1,
    request_type="pre_market",  # pre_market, post_market, sector, sentiment, full, auto
    market="HK",
)
print(report)

# 方式二：使用类接口
provider = DataProvider()
observer = MarketObserver(data_provider=provider)

context = SkillContext(
    user_id=1,
    request_type="auto",  # 根据市场时间自动选择
    markets=["HK"],
)

result = observer.execute(context)
if result.success:
    print(result.report_content)
```

### CLI 命令

```bash
# 盘前分析
python main.py skill run observer --market HK --type pre_market

# 盘后总结
python main.py skill run observer --market HK --type post_market

# 板块轮动
python main.py skill run observer --market HK --type sector

# 情绪指数
python main.py skill run observer --market HK --type sentiment

# 完整观察
python main.py skill run observer --market HK --type full

# 自动检测（根据市场时间）
python main.py skill run observer --market HK
```

## 数据结构

### MarketObserverResult

```python
@dataclass
class MarketObserverResult:
    """市场观察结果"""
    observation_date: date           # 观察日期
    market: str                      # 市场代码
    observation_type: str            # 观察类型
    pre_market_report: PreMarketReport   # 盘前报告
    post_market_report: PostMarketReport # 盘后报告
    sector_report: SectorAnalysisReport  # 板块报告
    sentiment_result: SentimentResult    # 情绪结果
    user_id: int                     # 用户ID
```

### GlobalMarketSnapshot

```python
@dataclass
class GlobalMarketSnapshot:
    """全球市场快照"""
    # 美股
    sp500_change: float      # 标普500涨跌%
    nasdaq_change: float     # 纳斯达克涨跌%
    dow_change: float        # 道琼斯涨跌%

    # 商品
    gold_change: float       # 黄金涨跌%
    oil_change: float        # 原油涨跌%

    # 汇率
    usd_cnh_change: float    # 美元兑人民币涨跌%

    # 其他
    a50_change: float        # A50期货涨跌%
    hsi_change: float        # 恒指涨跌%
```

### SentimentLevel 情绪等级

| 等级 | 分数范围 | 含义 |
|------|---------|------|
| EXTREME_FEAR | 0-20 | 极度恐惧 |
| FEAR | 20-40 | 恐惧 |
| NEUTRAL | 40-60 | 中性 |
| GREED | 60-80 | 贪婪 |
| EXTREME_GREED | 80-100 | 极度贪婪 |

### MarketIndicators 市场指标

| 指标 | 权重 | 说明 |
|------|------|------|
| advance_decline | 20% | 涨跌比 |
| new_high_low | 15% | 新高新低比 |
| above_ma | 15% | 站上均线比例 |
| volume | 15% | 成交量分布 |
| vix | 20% | 波动率指数 |
| market_change | 15% | 指数涨跌 |

## VIX 指数解读

| VIX 范围 | 等级 | 含义 |
|---------|------|------|
| 0-12 | 极低 | 市场过度乐观，可能回调 |
| 12-17 | 低 | 市场平静，适合持有 |
| 17-25 | 中等 | 正常波动，保持警惕 |
| 25-35 | 高 | 市场恐慌，可能出现机会 |
| 35+ | 极高 | 极度恐慌，历史性机会 |

## 市场时间表

### 港股 (北京时间)
- 盘前: 08:30
- 开盘: 09:30
- 午休: 12:00-13:00
- 收盘: 16:00
- 盘后: 16:30

### 美股 (北京时间，夏令时)
- 盘前: 20:00
- 开盘: 21:30
- 收盘: 次日 04:00
- 盘后: 次日 05:00

### A股 (北京时间)
- 盘前: 09:00
- 开盘: 09:30
- 午休: 11:30-13:00
- 收盘: 15:00
- 盘后: 15:30

## 板块分类

### 港股板块
- 科技、金融、房地产、消费、医疗健康
- 能源、原材料、工业、公用事业、电信

### 美股板块
- Technology, Financials, Healthcare
- Consumer Discretionary, Consumer Staples
- Energy, Materials, Industrials
- Utilities, Real Estate, Communication Services

### A股板块
- 信息技术、金融、房地产、消费、医药生物
- 能源、基础化工、机械设备、公用事业、国防军工

## 轮动信号类型

| 信号强度 | 含义 | 操作建议 |
|---------|------|---------|
| strong | 强信号 | 积极响应 |
| medium | 中等信号 | 关注确认 |
| weak | 弱信号 | 观察为主 |

## 文件结构

```
skills/market_observer/
├── __init__.py              # 模块导出
├── SKILL.md                 # 本文档
├── market_observer.py       # 主控制器
├── pre_market.py            # 盘前分析
├── post_market.py           # 盘后总结
├── sector_rotation.py       # 板块轮动
└── sentiment_meter.py       # 情绪指数
```

## 与其他 Skills 集成

```
            ┌─────────────┐
            │  Analyst    │
            └──────┬──────┘
                   │ signals
                   v
┌───────────┐    ┌─────────────────┐    ┌───────────┐
│ Positions │───>│ Market Observer │<───│ External  │
└───────────┘    └──────┬──────────┘    │ Market API│
                        │               └───────────┘
                        v
               ┌─────────────────┐
               │ Pre-Market      │
               │ Post-Market     │
               │ Sector Rotation │
               │ Sentiment       │
               └─────────────────┘
```

## 交易策略映射

### 情绪指数策略

| 情绪等级 | 操作建议 |
|---------|---------|
| 极度恐惧 | 历史表明是买入良机，逐步建仓 |
| 恐惧 | 保持观望，准备逢低吸纳 |
| 中性 | 按计划执行，关注个股机会 |
| 贪婪 | 注意风险，考虑部分止盈 |
| 极度贪婪 | 风险较高，建议减仓或保持现金 |

### 板块轮动策略

1. **跟随强势板块**：配置近期强势板块龙头
2. **回避弱势板块**：减少弱势板块暴露
3. **关注轮动信号**：把握板块切换机会
4. **资金流向验证**：用资金流向确认板块趋势

---

*版本: 1.0*
*创建日期: 2025-12-15*
*作者: Python Expert Agent*
