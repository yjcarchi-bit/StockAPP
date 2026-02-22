# StockAPP 架构设计文档 v2.0

> 版本: 2.0  
> 日期: 2024-02  
> 技术栈: React + TypeScript + FastAPI + Python  
> 状态: 开发中

---

## 一、项目概述

### 1.1 背景

StockAPP v1.0 使用 Streamlit 构建，虽然开发快速，但存在以下问题：
- UI 灵活性受限，难以实现复杂交互
- 性能较差，用户体验一般
- 样式定制困难

v2.0 采用 **React + FastAPI** 架构，保留 Python 回测引擎，使用现代化前端技术栈。

### 1.2 目标

- 提供专业级的用户体验
- 保持后端代码复用
- 支持灵活的 UI 定制
- 便于后续扩展和维护

---

## 二、项目结构

```
StockAPP/
├── backend/                          # Python FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI 入口
│   │   ├── config.py                 # 配置
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── backtest.py           # 回测 API
│   │   │   ├── data.py               # 数据 API
│   │   │   └── strategies.py         # 策略 API
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── backtest_engine.py    # 回测引擎（复用现有代码）
│   │   │   ├── data_source.py        # 数据源（复用现有代码）
│   │   │   └── optimizer.py          # 参数优化（复用现有代码）
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── requests.py           # 请求模型
│   │       └── responses.py          # 响应模型
│   ├── requirements.txt
│   └── run.py                         # 启动脚本
│
├── frontend/                          # React 前端
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/
│   │   │   │   ├── backtest/         # 回测组件
│   │   │   │   │   ├── BacktestParams.tsx
│   │   │   │   │   ├── BacktestResults.tsx
│   │   │   │   │   ├── ETFSelector.tsx
│   │   │   │   │   ├── StrategyIntroPanel.tsx
│   │   │   │   │   └── StrategyParams.tsx
│   │   │   │   ├── charts/           # 图表组件
│   │   │   │   │   ├── EquityCurveChart.tsx
│   │   │   │   │   ├── MonthlyHeatmap.tsx
│   │   │   │   │   ├── MetricsTable.tsx
│   │   │   │   │   └── TradeList.tsx
│   │   │   │   └── ui/               # 基础 UI 组件 (shadcn/ui)
│   │   │   ├── pages/                # 页面
│   │   │   │   ├── Home.tsx
│   │   │   │   ├── StrategyBacktest.tsx
│   │   │   │   ├── StrategyCompare.tsx
│   │   │   │   ├── ParameterOptimization.tsx
│   │   │   │   ├── DataManagement.tsx
│   │   │   │   └── SettingsPage.tsx
│   │   │   ├── hooks/                # 自定义 Hooks
│   │   │   │   ├── useBacktest.ts
│   │   │   │   ├── useStrategies.ts
│   │   │   │   └── useETFData.ts
│   │   │   ├── lib/                  # 工具函数
│   │   │   │   ├── api.ts            # API 客户端
│   │   │   │   ├── utils.ts          # 工具函数
│   │   │   │   └── constants.ts      # 常量
│   │   │   └── App.tsx               # 应用入口
│   │   ├── styles/                   # 样式
│   │   │   ├── index.css
│   │   │   ├── tailwind.css
│   │   │   └── theme.css
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── index.html
│
├── shared/                           # 共享类型
│   └── types.ts                      # TypeScript 类型定义
│
├── docs/                             # 文档
│   ├── ARCHITECTURE.md               # 架构文档（本文件）
│   └── DESIGN_DOCUMENT.md            # UI 设计文档
│
├── scripts/                          # 脚本
│   ├── start-dev.sh                  # 开发启动
│   ├── start-dev.bat                 # Windows 开发启动
│   └── build.sh                      # 构建脚本
│
├── README.md
└── docker-compose.yml                # Docker 配置（可选）
```

---

## 三、API 设计

### 3.1 回测 API

```
POST /api/backtest/run
请求体:
{
  "strategy": "dual_ma",
  "strategy_params": {
    "fast_period": 10,
    "slow_period": 30,
    "ma_type": "EMA"
  },
  "backtest_params": {
    "start_date": "2022-01-01",
    "end_date": "2024-01-01",
    "initial_capital": 100000,
    "commission_rate": 0.0003,
    "stamp_duty": 0.001
  },
  "etf_codes": ["510300", "510500"]
}

响应:
{
  "result_id": "uuid",
  "metrics": {
    "total_return": 25.6,
    "annual_return": 12.3,
    "max_drawdown": -8.5,
    "sharpe_ratio": 1.45,
    ...
  },
  "equity_curve": [...],
  "trades": [...],
  "monthly_returns": [...]
}
```

### 3.2 数据 API

```
GET /api/data/etf/list
响应:
{
  "etfs": [
    {"code": "510300", "name": "沪深300ETF", "type": "宽基"},
    ...
  ]
}

GET /api/data/etf/:code?start_date=2022-01-01&end_date=2024-01-01
响应:
{
  "code": "510300",
  "data": [
    {"date": "2022-01-04", "open": 4.5, "high": 4.6, "low": 4.4, "close": 4.55, "volume": 1000000},
    ...
  ]
}
```

### 3.3 策略 API

```
GET /api/strategies
响应:
{
  "strategies": [
    {
      "name": "dual_ma",
      "display_name": "双均线策略",
      "type": "趋势跟踪",
      "description": "...",
      "params": [
        {"name": "fast_period", "type": "int", "default": 10, "min": 5, "max": 30},
        ...
      ]
    },
    ...
  ]
}

GET /api/strategies/:name
响应:
{
  "name": "dual_ma",
  "display_name": "双均线策略",
  "type": "趋势跟踪",
  "icon": "📈",
  "description": "...",
  "logic": [...],
  "suitable": "...",
  "risk": "...",
  "params": {...}
}
```

---

## 四、数据流设计

### 4.1 回测流程

```
用户操作                    前端                    后端                    数据源
   │                        │                        │                        │
   ├─ 选择策略              │                        │                        │
   ├─ 配置参数              │                        │                        │
   ├─ 点击"开始回测" ──────►│                        │                        │
   │                        ├─ POST /api/backtest/run ────────►│                        │
   │                        │                        ├─ 获取 ETF 数据 ───────►│
   │                        │                        │◄─────── 返回数据 ───────┤
   │                        │                        ├─ 运行回测引擎          │
   │                        │◄─────── 返回结果 ──────┤                        │
   │◄─ 展示结果             │                        │                        │
```

### 4.2 状态管理

```typescript
// React Query - 服务端状态
const { data: strategies } = useQuery('strategies', fetchStrategies);
const { data: etfList } = useQuery('etfList', fetchETFList);

// Zustand - 客户端状态
const useBacktestStore = create((set) => ({
  selectedStrategy: 'dual_ma',
  strategyParams: {},
  backtestParams: {},
  results: null,
  setStrategy: (name) => set({ selectedStrategy: name }),
  setParams: (params) => set({ strategyParams: params }),
  setResults: (results) => set({ results }),
}));
```

---

## 五、组件设计

### 5.1 页面组件

| 页面 | 路由 | 说明 |
|------|------|------|
| Home | / | 首页，快速入口 |
| StrategyBacktest | /backtest | 策略回测 |
| StrategyCompare | /compare | 策略对比 |
| ParameterOptimization | /optimize | 参数优化 |
| DataManagement | /data | 数据管理 |
| SettingsPage | /settings | 设置 |

### 5.2 核心组件

| 组件 | 说明 |
|------|------|
| StrategyIntroPanel | 可收缩的策略介绍面板 |
| BacktestParams | 回测参数配置表单 |
| StrategyParams | 策略参数配置表单 |
| ETFSelector | ETF 多选组件 |
| BacktestResults | 回测结果展示 |
| EquityCurveChart | 资金曲线图表 |
| MonthlyHeatmap | 月度收益热力图 |
| TradeList | 交易记录列表 |
| MetricsTable | 指标表格 |

---

## 六、部署方案

### 6.1 开发环境

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

### 6.2 生产环境

```bash
# 后端
cd backend
pip install -r requirements.txt
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# 前端
cd frontend
npm run build
# 使用 nginx 托管静态文件
```

### 6.3 Docker 部署（可选）

```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
  
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
```

---

## 七、开发计划

### 阶段一：后端 API（2-3天）
- [ ] 创建 FastAPI 项目结构
- [ ] 迁移回测引擎
- [ ] 实现 REST API
- [ ] 添加 CORS 支持

### 阶段二：前端基础（2-3天）
- [ ] 创建 React 项目
- [ ] 配置 Tailwind CSS
- [ ] 复用 UI_REF 组件
- [ ] 实现路由

### 阶段三：功能实现（3-4天）
- [ ] 策略回测页面
- [ ] 策略对比页面
- [ ] 参数优化页面
- [ ] 数据管理页面

### 阶段四：优化完善（1-2天）
- [ ] 性能优化
- [ ] 错误处理
- [ ] 文档完善
- [ ] 部署脚本

---

## 八、版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2024-01 | Streamlit 版本（已弃用） |
| v2.0 | 2024-02 | React + FastAPI 版本（当前） |

---

## 九、技术选型理由

### 为什么选择 React + FastAPI？

| 方面 | Streamlit | React + FastAPI |
|------|-----------|-----------------|
| UI 灵活性 | 受限 | 完全自由 |
| 性能 | 较差 | 优秀 |
| 用户体验 | 一般 | 专业 |
| 可维护性 | 中等 | 优秀 |
| 扩展性 | 受限 | 优秀 |
| 学习曲线 | 低 | 中等 |

### 为什么保留 Python 后端？

- 已有完善的回测引擎代码
- efinance 库只有 Python 版本
- pandas 数据处理效率高
- FastAPI 性能优秀且易用
- 类型提示支持好

---

## 十、参考资源

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [React 文档](https://react.dev/)
- [Tailwind CSS 文档](https://tailwindcss.com/)
- [shadcn/ui 组件库](https://ui.shadcn.com/)
- [Recharts 图表库](https://recharts.org/)
- [efinance 文档](https://github.com/Micro-sheep/efinance)
