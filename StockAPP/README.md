# StockAPP 量化回测平台 v2.0

> A股量化策略回测平台 - React + FastAPI 架构

## 功能特性

- 支持 7 种内置策略
- 多种策略回测、对比和参数优化
- 实时数据更新与 WebSocket 推送

## 技术栈

- **后端**: Python 3.9+ + FastAPI 0.109.0
- **前端**: React 18.3 + TypeScript + Tailwind CSS 4.1
- **数据源**: efinance

## 项目结构

```
StockAPP/
├── backend/           # FastAPI 后端
│   └── app/
│       ├── routers/   # API 路由
│       ├── services/  # 业务逻辑
│       └── models/    # 数据模型
├── frontend/          # React 前端
├── core/              # 核心回测引擎
├── config/            # 配置文件
├── strategies/        # 策略实现
│   ├── simple/        # 简单策略 (5种)
│   └── multi_factor/  # 多因子策略 (2种)
└── data/              # 数据缓存
```

## 快速启动

**后端:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**前端:**
```bash
cd frontend
npm install
npm run dev
```

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |

## 内置策略

| 策略 | 类型 | 说明 |
|------|------|------|
| ETF轮动策略 | 动量策略 | 基于动量因子的ETF轮动 |
| 大市值低回撤 | 动量策略 | 六因子打分+RSRS择时 |
| 双均线策略 | 趋势跟踪 | 快慢均线交叉 |
| RSI策略 | 均值回归 | 超买超卖反转 |
| MACD策略 | 趋势跟踪 | MACD金叉死叉 |
| 布林带策略 | 均值回归 | 价格波动带 |
| 网格交易策略 | 震荡套利 | 区间网格交易 |

## 环境要求

- Python 3.9+
- Node.js 18+
