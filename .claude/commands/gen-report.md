# 生成报告命令

生成投资分析报告。

## 参数
$ARGUMENTS - 报告类型 (portfolio/technical/daily)

## 执行步骤

### 1. 确定报告类型

根据 $ARGUMENTS 参数:
- `portfolio` - 持仓分析报告
- `technical` - 技术分析报告
- `daily` - 每日简报

### 2. 生成报告

```bash
# 持仓分析报告
python main.py report --user dyson --type portfolio

# 技术分析报告 (指定股票)
python main.py report --user dyson --type technical --codes "HK.00700,US.NVDA"

# 每日简报
python main.py report --user dyson --type daily
```

### 3. 输出结果

报告保存到 `reports/output/` 目录，Markdown 格式。

## 报告类型说明

### Portfolio (持仓分析)
- 持仓明细表
- 仓位配比分析
- 盈亏排名
- 风险评分

### Technical (技术分析)
- K线图 (嵌入)
- 技术指标评分
- 支撑/阻力位
- 操作建议

### Daily (每日简报)
- 市场概况
- 持仓变动
- 重点关注
- 今日建议

## 输出格式

```
## 报告生成完成

### 报告类型: [type]
### 用户: [username]
### 生成时间: [datetime]

### 输出文件
reports/output/[type]_[date].md

### 报告摘要
[关键发现总结]
```
