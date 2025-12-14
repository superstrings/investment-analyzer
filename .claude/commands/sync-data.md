# 数据同步命令

同步投资数据（持仓、成交、K线）。

## 参数
$ARGUMENTS - 同步类型 (positions/trades/klines/all)

## 执行步骤

### 1. 确定同步类型

根据 $ARGUMENTS 参数确定同步内容:
- `positions` - 仅同步持仓数据
- `trades` - 仅同步成交记录
- `klines` - 仅同步K线数据
- `all` - 同步所有数据

### 2. 执行同步

```bash
# 同步所有数据
python main.py sync --user dyson --type all

# 仅同步持仓
python main.py sync --user dyson --type positions

# 仅同步成交
python main.py sync --user dyson --type trades

# 同步指定股票K线
python main.py sync --user dyson --type klines --codes "HK.00700,US.NVDA"
```

### 3. 验证结果

查看同步日志，确认数据已正确写入数据库。

## 注意事项

- 同步持仓和成交需要 FutuOpenD 运行中
- K线同步使用 akshare，无需 FutuOpenD
- 首次同步可能耗时较长

## 输出格式

```
## 数据同步完成

### 同步类型: [type]
### 用户: [username]

### 同步结果
- 持仓: [X] 条记录
- 成交: [X] 条记录
- K线: [X] 只股票

### 耗时
[X] 秒
```
