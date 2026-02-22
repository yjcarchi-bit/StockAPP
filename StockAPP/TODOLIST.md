# 大市值低回撤策略 - 进度条与选股详情功能实现

## 概述
大市值低回撤策略是自动选股策略，不需要用户手动选择ETF/股票池。需要实现详细的进度显示和每日选股信息展示。

---

## 任务列表

### P0 - 基础功能 (必须实现)

- [x] **任务1**: 隐藏ETF选择器，显示自动选股提示
  - 文件: `frontend/app/components/pages/StrategyBacktest.tsx`
  - 内容: 当选择"大市值低回撤策略"时，隐藏ETFSelector，显示"自动从沪深300成分股中选股"提示
  - 状态: ✅ 已完成

- [x] **任务2**: 基础进度条 + 当日日期显示
  - 文件: `frontend/app/components/pages/StrategyBacktest.tsx`
  - 内容: 增强现有进度条，显示当前处理日期和进度百分比
  - 状态: ✅ 已完成

### P1 - 核心功能 (重要)

- [x] **任务3**: 定义数据结构
  - 文件: `frontend/app/utils/backtestRunner.ts`
  - 内容: 定义 `DailySelectionResult`, `StockScoreDetail`, `BacktestProgressUpdate` 接口
  - 状态: ✅ 已完成

- [x] **任务4**: 修改回测函数支持进度回调
  - 文件: `frontend/app/utils/backtestRunner.ts`
  - 内容: `runBacktestAsync` 添加 `onProgress` 回调参数
  - 状态: ✅ 已完成

- [x] **任务5**: 创建详细进度组件
  - 文件: `frontend/app/components/backtest/BacktestProgress.tsx` (新建)
  - 内容: 显示当日选股结果、候选股票列表、调仓决策
  - 状态: ✅ 已完成

- [x] **任务6**: 候选股票列表 + 打分排名
  - 文件: `frontend/app/components/backtest/BacktestProgress.tsx`
  - 内容: 表格展示股票代码、名称、总分、排名、选中状态
  - 状态: ✅ 已完成

- [x] **任务7**: 调仓决策显示
  - 文件: `frontend/app/components/backtest/BacktestProgress.tsx`
  - 内容: 显示当日买入/卖出决策及原因
  - 状态: ✅ 已完成

### P2 - 增强功能 (可选)

- [x] **任务8**: 六因子详情弹窗
  - 文件: `frontend/app/components/backtest/BacktestProgress.tsx`
  - 内容: 点击股票行展开六因子得分详情
  - 状态: ✅ 已完成 (已在BacktestProgress中实现展开功能)

- [x] **任务9**: 雷达图可视化
  - 文件: `frontend/app/components/backtest/ScoreRadarChart.tsx` (新建)
  - 内容: 使用recharts绘制六因子雷达图
  - 状态: ✅ 已完成

- [x] **任务12**: 导出报告功能
  - 文件: `frontend/app/components/pages/StrategyBacktest.tsx`
  - 内容: 实现导出TXT报告功能
  - 状态: ✅ 已完成

### P3 - 高级功能 (后续扩展)

- [ ] **任务10**: 历史选股记录浏览
  - 内容: 允许用户查看历史某一天的选股结果
  - 状态: 待实现

- [ ] **任务11**: SSE流式进度推送
  - 文件: `backend/app/routers/backtest.py`
  - 内容: 使用Server-Sent Events实现实时进度推送
  - 状态: 待实现

---

## 数据结构定义

```typescript
// 每日选股结果
interface DailySelectionResult {
  date: string;
  marketStatus: 'normal' | 'drawdown_lock' | 'partial_unlock';
  candidates: StockScoreDetail[];
  selectedStocks: string[];
  trades: TradeDecision[];
  portfolioValue: number;
  drawdown: number;
  cashRatio: number;
}

// 股票打分详情
interface StockScoreDetail {
  code: string;
  name: string;
  scores: {
    momentum5: number;
    momentum20: number;
    trendStrength: number;
    volumeRatio: number;
    volatility: number;
    marketCap: number;
  };
  totalScore: number;
  rank: number;
  isSelected: boolean;
}

// 调仓决策
interface TradeDecision {
  action: 'buy' | 'sell' | 'hold';
  code: string;
  name: string;
  reason: string;
}

// 进度更新回调
interface BacktestProgressUpdate {
  currentIndex: number;
  totalDays: number;
  currentDate: string;
  percent: number;
  dailyResult: DailySelectionResult | null;
}
```

---

## 实现顺序

1. **第一阶段** (P0): 基础UI调整
   - 任务1 → 任务2

2. **第二阶段** (P1): 核心功能
   - 任务3 → 任务4 → 任务5 → 任务6 → 任务7

3. **第三阶段** (P2): 增强体验
   - 任务8 → 任务9

4. **第四阶段** (P3): 高级功能
   - 任务10 → 任务11

---

## 更新日志

| 日期 | 任务 | 状态 |
|------|------|------|
| - | - | - |
