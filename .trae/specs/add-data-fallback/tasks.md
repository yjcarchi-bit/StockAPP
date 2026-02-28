# Tasks

- [x] Task 1: 扩展配置选项
  - [x] SubTask 1.1: 在 `DataConfig` 中添加 `enable_fallback: bool = True` 字段

- [x] Task 2: 实现故障转移逻辑
  - [x] SubTask 2.1: 添加 `_try_efinance` 私有方法封装 efinance 调用
  - [x] SubTask 2.2: 添加 `_try_akshare_fallback` 私有方法封装 akshare 备用调用
  - [x] SubTask 2.3: 修改 `get_history` 方法实现故障转移逻辑
  - [x] SubTask 2.4: 添加故障转移日志记录

- [x] Task 3: 更新文档
  - [x] SubTask 3.1: 更新类文档说明故障转移机制

# Task Dependencies
- Task 2 依赖 Task 1（需要配置字段）
- Task 3 依赖 Task 2（需要实现完成后再更新文档）
