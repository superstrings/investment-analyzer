# 提交工作命令

完成当前工作并提交到 git，更新进度日志。

## 执行步骤

1. **检查代码状态**
   ```bash
   python -m pytest tests/ -v --tb=short
   python -m black --check .
   ```

2. **查看所有变更** (重要: 不要遗漏文件!)
   ```bash
   git status
   git ls-files --others --exclude-standard
   git diff --stat
   ```

   **特别检查**:
   - `db/migrations/*.sql` - 迁移脚本
   - 新增的测试文件 `test_*.py`
   - 配置文件变更

3. **更新 TASKS.md** (如果任务状态变化)
   - 更新任务的 `status` 为 `completed`
   - 更新 `progress` 为 100
   - 更新 `completed_items` 列表

4. **更新 TASKS_DONE.md** (如果有任务完成)
   - 在对应 Phase 的表格中添加一行:
   ```markdown
   | T00X | 任务名称 | YYYY-MM-DD | 主要产出文件 |
   ```

5. **更新 claude-progress.txt** - 追加本次工作摘要

6. **提交变更**
   ```bash
   git add .
   git commit -m "描述性消息"
   ```

7. **汇报** - 向用户报告提交结果

## 注意事项

- 如果测试失败，先修复再提交
- commit message 要清晰描述做了什么
- **必须检查未跟踪文件**，避免遗漏新增文件
- 不要忘记更新 TASKS_DONE.md
