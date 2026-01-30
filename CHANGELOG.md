# Changelog

所有重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.5.0] - 2025-01-30

### 新增

- **交易分析模块** (`skills/trade_analyzer/`)
  - 配对交易匹配算法 (FIFO)
  - 交易统计计算器 (胜率、盈亏比、持仓时间)
  - Excel 报告导出 (openpyxl)
  - Word 报告导出 (python-docx)
  - 图表生成器 (matplotlib)

- **AI 投资教练** (LLM 能力)
  - 基于 V10.10 投资框架
  - 自动分析交易数据生成建议
  - 使用 pandoc 转换 Markdown 到 Word
  - 智能嵌入报告"结论与建议"章节

- **手续费统计**
  - `TradeStatistics` 新增 `total_fees`、`stock_fees`、`option_fees` 字段
  - Word 报告"盈亏统计"章节显示手续费

- **港股期权合约乘数**
  - `config/hk_option_multipliers.py` 配置文件
  - `scripts/update_hk_option_multipliers.py` 同步脚本
  - 基于 HKEX 官方数据的 lot size 计算

- **Claude 命令**
  - `/analyze-trades` - 交易分析 + AI 投资教练
  - `/investment-coach` - 独立调用投资教练

### 变更

- 报告输出格式扩展: 新增 Word (docx)、Excel (xlsx)
- `scripts/update_docx_conclusion.py` 使用 pandoc 优化排版

### 依赖

- 新增 `python-docx` - Word 文档生成
- 新增 `openpyxl` - Excel 文档生成
- 推荐安装 `pandoc` - Markdown 转 Word

## [0.4.0] - 2025-01-15

### 新增

- 深度分析模块 (`skills/deep_analyzer/`)
- VCP 形态自动识别与评分
- 多市场批量分析支持

## [0.3.0] - 2024-12-01

### 新增

- Skills 系统 (分析师/风控/交易指导/市场观察)
- Claude Code 集成
- Slash 命令快捷操作

## [0.2.0] - 2024-11-01

### 新增

- 技术指标计算 (MA/MACD/RSI/BB/OBV)
- K线图表生成 (mplfinance)
- 报告模板 (Jinja2)

## [0.1.0] - 2024-10-01

### 新增

- 项目初始化
- 富途 API 数据采集
- PostgreSQL 数据存储
- CLI 基础框架
