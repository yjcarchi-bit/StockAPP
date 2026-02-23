# StockAPP 架构设计文档 v2.0

> 技术栈: React + TypeScript + FastAPI + Python

---

## 一、项目结构

```
StockAPP/
├── backend/                  # FastAPI 后端
│   └── app/
│       ├── main.py           # 入口
│       ├── config.py         # 配置
│       ├── routers/          # API 路由
│       │   ├── backtest.py
│       │   ├── data.py
│       │   ├── data_update.py
│       │   ├── strategies.py
│       │   └── websocket.py
│       ├── services/         # 业务逻辑
│       └── models/           # 数据模型
│
├── frontend/                 # React 前端
│   └── app/
│       ├── components/       # 组件
│       ├── pages/            # 页面
│       ├── hooks/            # Hooks
│       └── lib/              # 工具
│
├── core/                     # 核心回测引擎
│   ├── backtest_engine.py
│   ├── data_source.py
│   ├── optimizer.py
│   ├── indicators.py
│   └── strategy_base.py
│
├── strategies/               # 策略实现
│   ├── simple/               # 简单策略
│   │   ├── dual_ma.py
│   │   ├── rsi_strategy.py
│   │   ├── macd_strategy.py
│   │   ├── bollinger_strategy.py
│   │   └── grid_strategy.py
│   └── multi_factor/         # 多因子策略
│       ├── etf_rotation.py
│       └── large_cap_low_drawdown.py
│
├── config/                   # 配置
│   ├── settings.py
│   └── etf_pool.py
│
└── data/                     # 数据缓存
```

---

## 二、API 设计

### 2.1 回测 API

```
POST /api/backtest/run
GET  /api/backtest/result/{result_id}
```

### 2.2 策略 API

```
GET  /api/strategies          # 策略列表
GET  /api/strategies/{name}   # 策略详情
```

### 2.3 数据 API

```
GET  /api/data/etf/list       # ETF 列表
GET  /api/data/etf/{code}     # ETF 数据
```

### 2.4 WebSocket

```
WS   /ws/backtest             # 回测进度推送
```

---

## 三、数据流

```
前端 → API → 回测引擎 → 数据源(efinance)
                ↓
           策略执行
                ↓
           结果返回
```

---

## 四、页面路由

| 页面 | 路由 | 说明 |
|------|------|------|
| Home | / | 首页 |
| StrategyBacktest | /backtest | 策略回测 |
| StrategyCompare | /compare | 策略对比 |
| ParameterOptimization | /optimize | 参数优化 |
| DataManagement | /data | 数据管理 |

---

## 五、部署

**开发环境:**
```bash
# 后端
uvicorn app.main:app --reload --port 8000

# 前端
npm run dev
```

**生产环境:**
```bash
# 后端
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# 前端
npm run build
```
