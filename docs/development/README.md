# 开发指南

> Investment Analyzer - 开发者文档

## 1. 开发环境设置

### 1.1 必要软件

- Python 3.12+ (推荐 asdf 管理)
- PostgreSQL 17 (Homebrew)
- Git

### 1.2 环境配置

```bash
# 克隆项目
git clone <repository>
cd investment-analyzer

# Python 版本 (asdf)
asdf install python 3.12.7
asdf local python 3.12.7

# 虚拟环境
python -m venv .venv
source .venv/bin/activate

# 依赖安装
pip install -r requirements.txt

# 环境变量
cp .env.example .env
# 编辑 .env 配置数据库和富途连接信息
```

### 1.3 数据库设置

```bash
# 启动 PostgreSQL
brew services start postgresql@17

# 创建数据库
python scripts/init_db.py create-db

# 初始化表
python scripts/init_db.py init

# 测试数据 (可选)
python scripts/init_db.py seed
```

## 2. 项目结构

```
investment-analyzer/
├── analysis/           # 分析模块
│   ├── indicators/     # 技术指标
│   ├── portfolio.py    # 组合分析
│   └── technical.py    # 技术分析器
├── charts/             # 图表生成
├── config/             # 配置管理
├── db/                 # 数据库
├── fetchers/           # 数据采集
├── reports/            # 报告生成
├── services/           # 业务服务
├── skills/             # Claude Skills
├── scripts/            # 脚本工具
├── tests/              # 测试
├── docs/               # 文档
│   ├── design/         # 设计文档
│   ├── database/       # 数据库文档
│   ├── api/            # API 文档
│   └── development/    # 开发文档
├── main.py             # CLI 入口
├── CLAUDE.md           # Claude Code 指令
├── PLANNING.md         # 项目规划
└── TASKS.md            # 任务追踪
```

## 3. 代码规范

### 3.1 格式化

```bash
# Black 格式化
python -m black .

# isort 排序导入
python -m isort .

# flake8 检查
python -m flake8 .
```

### 3.2 类型注解

所有函数和方法必须使用类型注解:

```python
def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """计算 RSI 指标。

    Args:
        prices: 价格序列
        period: RSI 周期

    Returns:
        RSI 值序列
    """
    ...
```

### 3.3 文档字符串

使用 Google 风格:

```python
def analyze_portfolio(
    positions: list[PositionData],
    account: Optional[AccountData] = None,
) -> PortfolioAnalysisResult:
    """分析投资组合。

    Args:
        positions: 持仓数据列表
        account: 账户数据 (可选)

    Returns:
        组合分析结果

    Raises:
        ValueError: 当持仓数据无效时

    Example:
        >>> positions = [PositionData(market="HK", code="00700", qty=100)]
        >>> result = analyze_portfolio(positions)
        >>> print(result.summary.total_market_value)
    """
    ...
```

## 4. 测试

### 4.1 运行测试

```bash
# 所有测试
python -m pytest tests/ -v

# 带覆盖率
python -m pytest tests/ -v --cov=.

# 特定模块
python -m pytest tests/test_portfolio.py -v

# 特定测试
python -m pytest tests/test_portfolio.py::TestPortfolioAnalyzer -v
```

### 4.2 测试结构

```python
# tests/test_module.py

import pytest
from module import SomeClass

class TestSomeClass:
    """测试 SomeClass"""

    @pytest.fixture
    def sample_data(self):
        """测试数据"""
        return {...}

    def test_method_success(self, sample_data):
        """测试正常情况"""
        result = SomeClass().method(sample_data)
        assert result.value == expected

    def test_method_error(self):
        """测试异常情况"""
        with pytest.raises(ValueError):
            SomeClass().method(invalid_data)
```

### 4.3 测试覆盖要求

- 每个模块必须有对应测试文件
- 公共 API 100% 覆盖
- 边界条件和异常情况测试

## 5. 添加新功能

### 5.1 添加新指标

1. 创建文件 `analysis/indicators/new_indicator.py`:

```python
from .base import BaseIndicator, IndicatorResult

class NewIndicator(BaseIndicator):
    """新指标类"""

    name = "NewIndicator"

    def __init__(self, param: int = 14):
        self.param = param

    def calculate(self, df: pd.DataFrame, **kwargs) -> IndicatorResult:
        # 实现计算逻辑
        values = ...
        return IndicatorResult(
            name=self.name,
            values=values,
            params={"param": self.param},
        )
```

2. 在 `analysis/indicators/__init__.py` 导出:

```python
from .new_indicator import NewIndicator
```

3. 创建测试 `tests/test_new_indicator.py`

4. 更新文档

### 5.2 添加新报告类型

1. 创建模板 `reports/templates/new_report.md.j2`

2. 在 `ReportType` 添加枚举值

3. 在 `ReportGenerator` 添加方法:

```python
def generate_new_report(self, data, config=None) -> ReportResult:
    ...
```

4. 创建测试

### 5.3 添加新命令

在 `main.py` 添加:

```python
@cli.group()
def new_command():
    """新命令组"""
    pass

@new_command.command()
@click.option("--param", required=True)
def subcommand(param):
    """子命令说明"""
    ...
```

## 6. Git 工作流

### 6.1 提交规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

类型:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `refactor`: 重构
- `test`: 测试
- `chore`: 杂项

示例:
```
feat(analysis): add new RSI divergence detection

- Implement RSIDivergence class
- Add bullish/bearish divergence detection
- Create tests for edge cases

Closes #123
```

### 6.2 分支策略

- `main`: 主分支，保持稳定
- `feature/*`: 功能分支
- `fix/*`: Bug 修复分支

## 7. Claude Code 集成

本项目使用 "自动化工厂" 开发模式，详见:

- [Claude Code 开发指南](claude-code.md)

---

*文档版本: 1.0*
*最后更新: 2025-12-14*
