# StockAPP

一个个人使用的简易量化交易程序，由 AI 辅助开发实现。

## 功能特性

- **策略回测** - 支持多种量化策略的历史数据回测
- **参数优化** - 策略参数自动优化
- **策略对比** - 多策略性能对比分析
- **数据管理** - ETF/股票数据获取与更新
- **可视化报告** - 资金曲线、月度收益热力图、交易记录等

## 技术栈

### 后端
- **FastAPI** - 高性能 Python Web 框架
- **Pandas** - 数据处理与分析
- **efinance** - 金融数据获取
- **APScheduler** - 定时任务调度

### 前端
- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Tailwind CSS** - 样式框架
- **shadcn/ui** - UI 组件库
- **Recharts** - 图表库

## 项目结构

```
StockAPP/
├── StockAPP/
│   ├── backend/           # FastAPI 后端
│   │   ├── app/
│   │   │   ├── routers/   # API 路由
│   │   │   ├── services/  # 业务逻辑
│   │   │   └── models/    # 数据模型
│   │   └── requirements.txt
│   │
│   ├── frontend/          # React 前端
│   │   ├── app/
│   │   │   ├── components/  # UI 组件
│   │   │   ├── pages/       # 页面
│   │   │   └── hooks/       # 自定义 Hooks
│   │   └── package.json
│   │
│   ├── core/              # 核心模块
│   │   ├── backtest_engine.py   # 回测引擎
│   │   ├── data_source.py       # 数据源
│   │   ├── optimizer.py         # 参数优化
│   │   └── strategy_base.py     # 策略基类
│   │
│   ├── strategies/        # 策略实现
│   │   ├── dual_ma.py           # 双均线策略
│   │   ├── macd_strategy.py     # MACD 策略
│   │   ├── rsi_strategy.py      # RSI 策略
│   │   ├── bollinger_strategy.py # 布林带策略
│   │   ├── etf_rotation.py      # ETF 轮动策略
│   │   └── grid_strategy.py     # 网格策略
│   │
│   ├── config/            # 配置文件
│   ├── reports/           # 报告生成
│   └── utils/             # 工具函数
│
├── StrategyManage/        # 策略管理脚本
│   ├── strategy1_大市值低回撤/
│   ├── strategy2_价值选股与RSRS择时/
│   ├── strategy3_ETF增值/
│   ├── strategy4_优质小市值周轮动策略/
│   ├── strategy5_多策略封装模板/
│   └── strategy6_对探针法因子筛选多模型参数优化/
│
└── docs/                  # 文档
```

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+

### 后端启动

```bash
cd StockAPP/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端启动

```bash
cd StockAPP/frontend
npm install
npm run dev
```

### 一键启动

- **macOS**: 双击 `StockAPP/启动应用_macOS.command`
- **Windows**: 双击 `StockAPP/启动应用_Windows.bat`

## 内置策略

| 策略 | 类型 | 描述 |
|------|------|------|
| 双均线 | 趋势跟踪 | 快慢均线交叉信号 |
| MACD | 趋势跟踪 | MACD 指标金叉死叉 |
| RSI | 震荡指标 | RSI 超买超卖信号 |
| 布林带 | 震荡指标 | 价格突破布林带 |
| ETF轮动 | 轮动策略 | 多 ETF 动量轮动 |
| 网格策略 | 震荡策略 | 价格区间网格交易 |

## API 接口

### 回测
```
POST /api/backtest/run
```

### 策略列表
```
GET /api/strategies
```

### ETF 数据
```
GET /api/data/etf/list
GET /api/data/etf/:code
```

## 开发说明

本项目为个人学习与实践用途，由 AI 辅助开发。仅供学习参考，不构成投资建议。

## License

MIT
