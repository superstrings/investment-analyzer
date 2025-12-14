# 运行测试命令

运行项目测试套件。

## 参数
$ARGUMENTS - 测试范围 (可选，如 tests/test_fetchers.py)

## 执行步骤

### 1. 确定测试范围

根据 $ARGUMENTS 参数:
- 空参数: 运行全部测试
- 指定文件: 运行指定测试文件
- 指定模块: 运行指定模块测试

### 2. 运行测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 运行指定文件
python -m pytest tests/test_fetchers.py -v

# 运行带覆盖率
python -m pytest tests/ -v --cov=. --cov-report=term-missing

# 快速测试 (跳过慢测试)
python -m pytest tests/ -v -m "not slow"
```

### 3. 分析结果

查看测试输出，识别失败的测试和原因。

## 测试分类

| 类别 | 路径 | 说明 |
|------|------|------|
| 单元测试 | `tests/unit/` | 单个函数/类测试 |
| 集成测试 | `tests/integration/` | 模块间集成测试 |
| 功能测试 | `tests/functional/` | 端到端功能测试 |

## pytest 标记

- `@pytest.mark.slow` - 慢速测试
- `@pytest.mark.integration` - 需要外部服务
- `@pytest.mark.skip` - 跳过的测试

## 输出格式

```
## 测试结果

### 范围: [scope]

### 统计
- 通过: [X]
- 失败: [X]
- 跳过: [X]
- 错误: [X]

### 覆盖率
- 总覆盖率: [X]%

### 失败详情 (如有)
- test_name: [原因]

### 建议
- [suggestion]
```
