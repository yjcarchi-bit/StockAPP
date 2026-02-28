# StockAPP 量化回测平台 v2.0

> A股量化回测平台（React + FastAPI + Python 核心引擎）

## 当前能力

- 后端驱动的策略回测、策略对比、参数优化
- 实时行情推送（WebSocket）与数据更新管理
- 前端图表化展示：资金曲线、交易记录、月度收益、每日持仓

## 当前内置策略

| 策略 | 类型 | 说明 |
|------|------|------|
| ETF轮动策略 | 动量策略 | 基于动量因子的 ETF 轮动（含过滤与止损） |

> 说明：目前仅启用 `etf_rotation` 策略。策略对比功能要求至少 2 个策略，若仅启用 1 个策略时页面会提示不可对比。

## 技术栈

- **后端**: Python 3.9+ + FastAPI 0.109
- **前端**: React 18 + TypeScript + Vite + Tailwind CSS
- **核心引擎**: `core/`（回测引擎、指标、组合、优化器）
- **数据源**: efinance（支持缓存与故障回退）

## 项目结构

```text
StockAPP/
├── backend/                 # FastAPI 后端（API 层）
│   └── app/
│       ├── routers/         # 路由层
│       ├── services/        # 业务编排层
│       └── models/          # 请求/响应模型
├── frontend/                # React 前端
│   └── app/
│       ├── components/      # 页面与通用组件
│       └── utils/           # API 客户端、适配器、前端工具
├── core/                    # 领域核心（回测/优化/数据能力）
├── strategies/              # 策略实现
├── config/                  # 全局配置与 ETF 池
├── data/                    # 本地缓存目录
└── docker/                  # Docker 与 Nginx 配置
```

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| OpenAPI 文档 | http://localhost:8000/docs |

## 环境变量

前端默认从 `VITE_API_BASE` 读取 API 基址，默认值为 `/api`。

- 本地前后端分离开发：可在前端环境里设为 `http://<backend-host>:8000/api`
- Docker + Nginx 代理：保持 `/api` 即可

后端数据源支持从项目根目录 `.env` 读取配置（参考 `.env.example`）：

- `PROXY_AUTH_CODE`：akshare 代理补丁认证码
- `TUSHARE_TOKEN`：tushare token（历史成分股需要）
- `AKSHARE_ENABLE_PROXY`：是否启用代理（`true/false`）
- `AKSHARE_PROXY_HOST` / `AKSHARE_PROXY_TIMEOUT`：代理主机与超时

## 环境要求

- Python 3.9+
- Node.js 18+
