# StockAPP 架构整改 TODO（后端驱动版）

## 目标
- 前端只负责 UI 和交互，回测/对比/优化全部走后端 API
- 后端回测与优化接口返回真实结果并通过模型校验
- 数据管理页面使用真实数据更新接口，不再展示静态样例

## P0（阻塞项，先做）
- [x] 修复 backend 回测服务未完成实现（_format_result）
- [x] 修复 backend 参数优化服务未完成实现（optimize 返回）
- [x] 修复策略实例化方式（禁止 strategy_class(**params)，改 set_params）
- [x] 修复 StrategyInfo.params 模型类型不匹配（Dict -> List）

## P1（主链路改造）
- [x] 新增前端统一 API 客户端（VITE_API_BASE + fallback）
- [x] 策略回测页改为调用 /api/backtest/run
- [x] 策略对比页改为调用 /api/backtest/compare
- [x] 参数优化页改为调用 /api/backtest/optimize
- [x] 前端增加后端结果 -> UI 模型适配层

## P2（体验与一致性）
- [x] 数据管理页接入 /api/data-update/* 与 /api/data/*
- [x] 清理前端硬编码 API 地址
- [x] README 与实际策略数、能力保持一致
- [x] 清理无用本地回测路径（或标记 legacy）

## 验收标准
- [ ] 回测、对比、优化三页均返回非空真实结果（待联调）
- [ ] /docs 模型与前端调用一致，无 params 类型校验错误（待服务启动验收）
- [x] 全仓库无硬编码 http://localhost:8000/api（统一环境变量入口）
- [ ] Docker/Nginx 场景下前端通过 /api 正常代理后端（待容器联调）

## 更新日志
| 日期 | 变更 | 状态 |
|------|------|------|
| 2026-03-01 | 创建架构整改 TODO（替换旧内容） | 进行中 |
| 2026-03-01 | 完成 P0/P1/P2 主体改造，进入联调验收 | 进行中 |
