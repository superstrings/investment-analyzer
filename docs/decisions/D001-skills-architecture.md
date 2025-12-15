# Decision: Skills 体系架构设计

**日期**: 2025-12-15

## 上下文

需要为 investment-analyzer 系统设计一套完整的 skills 体系，支持自动化投资分析、风险监控、交易指导等功能。现有系统已有基础的分析能力（技术指标、形态识别、组合分析），但缺乏主动性、角色分工和时间维度的处理。

### 关键问题

1. 如何组织多个 skill（分析师、风控师、交易导师、市场观察员）？
2. 如何实现自动化工作流（盘前/盘后/月度）？
3. 如何处理不同市场的时区差异（港股/美股/A股）？
4. 如何在 CLI 和 Claude Code 两种交互方式中统一使用？

## 决策

### 决策 1: 采用角色分离的 Skill 架构

**选择**: 将功能按角色（Analyst/RiskController/TradingCoach/MarketObserver）分离，每个角色独立实现。

**理由**:
- 职责清晰，便于维护和扩展
- 符合用户历史 prompt 中的角色定义
- 便于独立测试和调用
- 支持按需组合使用

### 决策 2: 使用 BaseSkill 抽象基类

**选择**: 所有 Skill 继承统一的 BaseSkill 基类，实现标准接口。

```python
class BaseSkill(ABC):
    @abstractmethod
    def execute(self, context: SkillContext) -> SkillResult:
        pass

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        pass
```

**理由**:
- 统一的接口便于工作流编排
- 支持依赖注入和测试 mock
- 便于扩展新的 skill

### 决策 3: 工作流采用声明式配置

**选择**: 使用 YAML 配置定义工作流，而非硬编码。

```yaml
# workflow/daily.yaml
pre_market:
  - skill: market_observer
    action: pre_market_analysis
  - skill: analyst
    action: update_positions
  - skill: risk_controller
    action: check_risks
  - skill: trading_coach
    action: generate_plan
```

**理由**:
- 配置化便于调整流程
- 便于用户自定义工作流
- 支持条件执行和并行处理

### 决策 4: 数据层统一通过 DataProvider

**选择**: 创建 DataProvider 类统一封装数据获取逻辑。

**理由**:
- 解耦 skill 与数据源
- 支持缓存和批量获取优化
- 便于测试时 mock 数据
- 统一处理异常和重试

### 决策 5: 技术分析聚焦 OBV + VCP 双核心

**选择**: 精简技术指标，以 OBV (能量潮) + VCP (波动收缩形态) 为核心分析框架。

**理由**:
- **技术指标在精不在多**: 堆砌指标只会增加噪音和决策困难
- **OBV 的独特价值**: 量在价先，是资金动向的先行指标，能发现主力吸筹/出货
- **VCP 的高效性**: Mark Minervini 的经典形态，成功率高，风险收益比优秀
- **两者互补配合**:
  - VCP 找形态 (价格收缩 + 量能萎缩)
  - OBV 确认资金 (趋势 + 背离检测)
  - 突破时放量 + OBV 创新高 = 高概率买点

**评分权重**: OBV (40%) + VCP (60%)

**舍弃的指标**:
- MACD/RSI/KDJ 等: 滞后性强，信号模糊
- 布林带: 与 VCP 收缩逻辑重叠
- 均线系统: 作为辅助参考，不纳入评分

## 备选方案

### 方案 A: 单一 Skill 多功能模式

将所有功能放在一个大的 InvestmentAdvisor skill 中。

- **优点**: 实现简单，调用方便
- **缺点**: 职责混乱，难以维护，不便独立测试

### 方案 B: 函数式 Skill 模式 (未选择)

每个功能点作为独立函数，不使用类。

- **优点**: 简洁，函数式风格
- **缺点**: 难以共享状态，配置管理复杂

### 方案 C: 角色分离 + 抽象基类 (选定)

多个独立 Skill 类，共享基类和接口。

- **优点**: 职责清晰，易扩展，便于测试
- **缺点**: 代码量稍大，需要设计好基类

## 后果

### 正面影响

1. 系统架构清晰，便于理解和维护
2. 新功能可以通过新增 Skill 扩展
3. 工作流可配置化，灵活性高
4. 测试覆盖容易实现

### 负面影响

1. 初始开发量较大
2. 需要维护多个 SKILL.md 文档
3. Skill 间通信需要通过 SkillContext 传递

### 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| Skill 间依赖混乱 | 通过 DataProvider 解耦，明确依赖方向 |
| 工作流调试困难 | 添加详细日志和调试模式 |
| 性能问题 | 使用缓存，支持并行执行 |

---

*决策状态: 已通过*
*审核人: dyson*
