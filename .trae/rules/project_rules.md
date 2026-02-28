# StockAPP 项目规则

## 1. 框架版本

**后端 (Python 3.9+):** FastAPI 0.109.0, pydantic 2.5.3, pandas >= 2.0.0, efinance >= 0.5.5

**前端 (Node.js 18+):** React 18.3.1, Vite 6.3.5, Tailwind CSS 4.1.12, MUI 7.3.5, Recharts 2.15.2

---

## 2. 测试框架

**后端:** `pytest --cov=app` 运行测试和覆盖率

**前端:** `vitest run --coverage` 运行测试和覆盖率

**覆盖率要求:** 后端 API 80%+, 前端组件 60%+, Hooks 80%+

---

## 3. 代码质量

**后端:** ruff (lint), mypy (类型检查)

**前端:** ESLint, Prettier, TypeScript 严格模式

---

## 4. 策略变更规则

修改 `StockAPP/strategies/` 时，必须同步更新：

| 文件 | 更新内容 |
|------|----------|
| `strategies/__init__.py` | 导入导出策略类 |
| `backend/app/routers/strategies.py` | `strategy_map`, `type_map`, `icon_map`, `STRATEGY_NAMES` |
| `backend/app/services/backtest_engine.py` | `STRATEGY_MAP` 策略映射 |
| `backend/app/services/optimizer.py` | `STRATEGY_MAP` 策略映射 |
| `frontend/app/utils/strategyConfig.ts` | `StrategyType`, `strategies` 数组 |
| `frontend/app/utils/backtestRunner.ts` | 

**策略必须属性:** `display_name`, `description`, `category`, `params_info`, `logic`, `suitable`, `risk`
