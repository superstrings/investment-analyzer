# Python 开发命令

调用 Python 专家执行开发任务。

## 参数
$ARGUMENTS - 开发任务描述

## 执行步骤

### 1. 分析任务

理解 $ARGUMENTS 描述的开发任务:
- 新功能实现
- Bug 修复
- 性能优化
- 重构

### 2. 调用 Python Expert Agent

使用 Task 工具调用 python-expert agent:

```
Task tool with subagent_type="python-expert"
prompt: "实现以下功能: $ARGUMENTS

请遵循以下步骤:
1. 阅读相关代码了解现有模式
2. 编写测试用例
3. 实现功能代码
4. 运行测试确保通过
5. 使用 black 和 isort 格式化代码
"
```

### 3. 验证结果

```bash
# 运行测试
python -m pytest tests/ -v

# 检查代码风格
python -m black --check .
python -m isort --check .
```

### 4. 更新任务状态

如果任务完成，更新 TASKS.md 相关任务的进度。

## 常见开发任务

| 类型 | 示例 |
|------|------|
| 新功能 | "实现 OBV 指标计算" |
| Bug 修复 | "修复 K线数据为空的问题" |
| 优化 | "优化数据库批量写入性能" |
| 重构 | "重构 fetcher 模块使用异步" |

## 输出格式

```
## Python 开发完成

### 任务: [description]

### 完成内容
- [item1]
- [item2]

### 修改文件
- file1.py
- file2.py

### 测试结果
[X] tests passed
```
