# StockAPP 量化回测平台 v2.0

> A股量化策略回测平台 - React + FastAPI 架构

## 功能特性

- 支持 7 种内置策略
- 多种策略回测、对比和参数优化
- 实时数据更新和 WebSocket 推送
- Docker 容器化部署支持

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Tailwind CSS + shadcn/ui + Recharts |
| 后端 | Python 3.9+ + FastAPI + Uvicorn |
| 数据源 | efinance (东方财富) |
| 构建工具 | Vite 6 |
| 容器化 | Docker + Docker Compose + Nginx |

## 快速启动

### 方式一：本地开发启动（推荐）

**macOS:**
```bash
双击运行: StockAPP/启动应用_macOS.command
```

**Windows:**
```bash
双击运行: StockAPP/启动应用_Windows.bat
```

### 方式二：Docker 部署

**macOS:**
```bash
双击运行: StockAPP/启动Docker环境_macOS.command
```

**Windows:**
```bash
双击运行: StockAPP/启动Docker环境_Windows.bat
```

## 访问地址

| 服务 | 本地开发 | Docker 部署 |
|------|----------|-------------|
| 前端界面 | http://localhost:5173 | http://localhost |
| 后端 API | http://localhost:8000 | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs | http://localhost/docs |

## 内置策略

| 策略 | 类型 | 说明 |
|------|------|------|
| ETF轮动策略 | 复合策略 | 基于动量因子的ETF轮动 |
| 大市值低回撤 | 复合策略 | 六因子打分+RSRS择时+回撤锁定 |
| 双均线策略 | 趋势跟踪 | 快慢均线交叉 |
| RSI策略 | 均值回归 | 超买超卖反转 |
| MACD策略 | 趋势跟踪 | MACD金叉死叉 |
| 布林带策略 | 均值回归 | 价格波动带 |
| 网格交易策略 | 震荡套利 | 区间网格交易 |

## 环境要求

### 本地开发
- Python 3.9+
- Node.js 18+

### Docker 部署
- Docker Desktop

## 项目结构

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
│   ├── 启动应用_macOS.command        # macOS 本地启动
│   ├── 启动应用_Windows.bat          # Windows 本地启动
│   ├── 启动Docker环境_macOS.command  # macOS Docker 启动
│   └── 启动Docker环境_Windows.bat    # Windows Docker 启动
│
├── StockAPP_UI_REF/                 # UI 参考代码
├── StrategyManage/                  # 策略开发目录
└── README.md                        # 项目说明
```

详细结构请参考 [StockAPP/docs/PROJECT_STRUCTURE.md](StockAPP/docs/PROJECT_STRUCTURE.md)

## 文档

- [架构设计文档](StockAPP/ARCHITECTURE.md)
- [项目结构说明](StockAPP/docs/PROJECT_STRUCTURE.md)
- [UI 设计文档](StockAPP/docs/DESIGN_DOCUMENT.md)
- [Docker 测试文档](StockAPP/docker/DOCKER_TEST.md)

## 版本历史

| 版本 | 说明 |
|------|------|
| v1.0 | Streamlit 单体应用 |
| v2.0 | React + FastAPI 分离架构 |
