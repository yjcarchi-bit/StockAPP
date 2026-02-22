# StockAPP 项目结构说明

> 最后更新: 2026-02-23

---

## 一、目录结构总览

```
StockAPP/
├── StockAPP/                        # 主应用目录
│   ├── backend/                     # Python FastAPI 后端
│   ├── frontend/                    # React TypeScript 前端
│   ├── core/                        # 核心回测引擎
│   ├── config/                      # 配置模块
│   ├── strategies/                  # 策略实现
│   ├── data/                        # 数据缓存
│   ├── docker/                      # Docker 相关文件
│   ├── docs/                        # 文档
│   │
│   ├── 启动应用_macOS.command        # macOS 本地启动脚本
│   ├── 启动应用_Windows.bat          # Windows 本地启动脚本
│   ├── 启动Docker环境_macOS.command  # macOS Docker 启动脚本
│   └── 启动Docker环境_Windows.bat    # Windows Docker 启动脚本
│
├── StockAPP_UI_REF/                 # UI 参考代码 (开发参考)
├── StrategyManage/                  # 策略开发目录 (独立策略项目)
└── README.md                        # 项目说明
```

---

## 二、主应用目录 (StockAPP/)

### 2.1 后端 (backend/)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   ├── requests.py      # 请求模型
│   │   └── responses.py     # 响应模型
│   ├── routers/             # API 路由
│   │   ├── __init__.py
│   │   ├── backtest.py      # 回测 API
│   │   ├── data.py          # 数据 API
│   │   ├── data_update.py   # 数据更新 API
│   │   ├── strategies.py    # 策略 API
│   │   └── websocket.py     # WebSocket 实时数据
│   └── services/            # 业务服务
│       ├── __init__.py
│       ├── backtest_engine.py
│       ├── data_source.py
│       └── optimizer.py
├── requirements.txt         # Python 依赖
└── run.py                   # 启动脚本
```

### 2.2 前端 (frontend/)

```
frontend/
├── app/
│   ├── App.tsx              # 应用入口
│   ├── components/          # 组件
│   │   ├── backtest/        # 回测相关组件
│   │   ├── charts/          # 图表组件
│   │   ├── pages/           # 页面组件
│   │   ├── ui/              # 基础 UI 组件 (shadcn/ui)
│   │   └── figma/           # Figma 相关组件
│   ├── contexts/            # React Context
│   ├── hooks/               # 自定义 Hooks
│   └── utils/               # 工具函数
├── dist/                    # 构建产物
├── styles/                  # 样式文件
├── index.html               # HTML 入口
├── main.tsx                 # React 入口
├── package.json             # npm 配置
├── vite.config.ts           # Vite 配置
└── .env.production          # 生产环境变量
```

### 2.3 核心模块 (core/)

```
core/
├── __init__.py
├── backtest_engine.py       # 回测引擎
├── data_source.py           # 数据源
├── data_update_service.py   # 数据更新服务
├── indicators.py            # 技术指标
├── optimizer.py             # 参数优化
├── order.py                 # 订单管理
├── portfolio.py             # 组合管理
├── realtime_data.py         # 实时数据
├── scheduler.py             # 定时任务
├── strategy_base.py         # 策略基类
└── strategy_signal_service.py  # 策略信号服务
```

### 2.4 策略模块 (strategies/)

```
strategies/
├── __init__.py
├── dual_ma.py               # 双均线策略
├── rsi_strategy.py          # RSI 策略
├── macd_strategy.py         # MACD 策略
├── bollinger_strategy.py    # 布林带策略
├── grid_strategy.py         # 网格交易策略
├── etf_rotation.py          # ETF 轮动策略
└── large_cap_low_drawdown.py # 大市值低回撤策略
```

### 2.5 Docker 目录 (docker/)

```
docker/
├── docker-compose.yml       # Docker 编排
├── Dockerfile.backend       # 后端镜像
├── Dockerfile.frontend      # 前端镜像
├── nginx.conf               # Nginx 配置
├── .dockerignore            # Docker 忽略文件
└── DOCKER_TEST.md           # Docker 测试文档
```

---

## 三、启动方式

### 3.1 本地开发

**macOS:**
```bash
双击运行: StockAPP/启动应用_macOS.command
```

**Windows:**
```bash
双击运行: StockAPP/启动应用_Windows.bat
```

### 3.2 Docker 部署

**macOS:**
```bash
双击运行: StockAPP/启动Docker环境_macOS.command
```

**Windows:**
```bash
双击运行: StockAPP/启动Docker环境_Windows.bat
```

---

## 四、访问地址

| 服务 | 本地开发 | Docker 部署 |
|------|----------|-------------|
| 前端界面 | http://localhost:5173 | http://localhost |
| 后端 API | http://localhost:8000 | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs | http://localhost/docs |

---

## 五、技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Tailwind CSS + shadcn/ui + Recharts |
| 后端 | Python 3.9+ + FastAPI + Uvicorn |
| 数据源 | efinance (东方财富) |
| 构建工具 | Vite 6 |
| 容器化 | Docker + Docker Compose + Nginx |

---

## 六、内置策略

| 策略 | 类型 | 说明 |
|------|------|------|
| ETF轮动策略 | 复合策略 | 基于动量因子的ETF轮动 |
| 大市值低回撤 | 复合策略 | 六因子打分+RSRS择时+回撤锁定 |
| 双均线策略 | 趋势跟踪 | 快慢均线交叉 |
| RSI策略 | 均值回归 | 超买超卖反转 |
| MACD策略 | 趋势跟踪 | MACD金叉死叉 |
| 布林带策略 | 均值回归 | 价格波动带 |
| 网格交易策略 | 震荡套利 | 区间网格交易 |
