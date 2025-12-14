# 生成K线图命令

生成指定股票的K线图。

## 参数
$ARGUMENTS - 股票代码 (如 HK.00700, US.NVDA)

## 执行步骤

### 1. 解析参数

从 $ARGUMENTS 获取:
- 股票代码
- 可选: 天数 (默认 120)
- 可选: 指标 (ma, obv, macd)

### 2. 生成图表

```bash
# 基础K线图
python main.py chart --code HK.00700 --days 120

# 带技术指标
python main.py chart --code HK.00700 --days 120 --indicators ma,obv

# 批量生成关注列表
python main.py chart --watchlist --user dyson
```

### 3. 输出结果

图表保存到 `charts/output/` 目录。

## 图表选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--days` | K线天数 | 120 |
| `--indicators` | 技术指标 | ma |
| `--style` | 图表样式 | yahoo |

## 支持的指标

- `ma` - 移动平均线 (MA5/10/20/60)
- `obv` - 能量潮
- `macd` - MACD
- `rsi` - RSI
- `bb` - 布林带

## 输出格式

```
## K线图生成完成

### 股票: [code] [name]
### 时间范围: [start] - [end]
### 指标: [indicators]

### 输出文件
charts/output/[code]_[date].png

### 技术概要
- MA排列: [多头/空头/震荡]
- OBV趋势: [向上/向下/横盘]
```
