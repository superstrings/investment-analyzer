# 功能需求分析命令

分析新功能需求并生成设计文档。

## 参数
$ARGUMENTS - 功能描述

## 执行步骤

### 1. 调用 Requirements Analyst Agent

使用 Task 工具调用 requirements-analyst agent:

```
Task tool with subagent_type="requirements-analyst"
prompt: "请分析以下功能需求: $ARGUMENTS

请完成:
1. 理解需求背景和目标
2. 分析与现有系统的集成点
3. 识别技术约束和风险
4. 设计高层技术方案
5. 列出实现任务
"
```

### 2. 生成设计文档

在 `docs/features/` 目录下创建功能设计文档。

### 3. 更新任务列表

将新任务添加到 TASKS.md。

## 文档模板

```markdown
# F00X - [功能名称]

## 概述
[一句话描述]

## 背景
[为什么需要这个功能]

## 需求详情

### 功能需求
- FR-1: [需求1]
- FR-2: [需求2]

### 非功能需求
- NFR-1: [性能要求]
- NFR-2: [安全要求]

## 技术设计

### 架构变更
[需要修改的模块]

### 数据模型
[数据库变更]

### 接口设计
[新增/修改的接口]

## 文件位置

| 模块 | 路径 |
|------|------|
| 代码 | path/to/code |
| 测试 | path/to/tests |

## 实现任务

| 任务 | 优先级 |
|------|--------|
| Task 1 | P0 |
| Task 2 | P1 |

## 测试计划
[测试策略]
```

## 输出格式

```
## 功能分析完成

### 功能: [name]
### 文档: docs/features/F00X-[name].md

### 摘要
[功能概述]

### 实现任务 (已添加到 TASKS.md)
- T0XX: [task1]
- T0XX: [task2]

### 预计工期
[估算]
```
