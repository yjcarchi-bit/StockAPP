// 策略类型定义
export type StrategyType = 'etf_rotation' | 'dual_ma' | 'rsi' | 'macd' | 'bollinger' | 'grid';

export interface Strategy {
  id: StrategyType;
  name: string;
  icon: string;
  type: '动量策略' | '趋势跟踪' | '均值回归' | '震荡套利';
  color: string;
  description: string;
  logic: string[];
  parameters: StrategyParameter[];
  适用场景: string;
  风险提示: string;
}

export interface StrategyParameter {
  key: string;
  label: string;
  type: 'number' | 'slider' | 'select';
  default: number | string;
  min?: number;
  max?: number;
  step?: number;
  options?: { value: string; label: string }[];
  description: string;
}

// 6种策略配置
export const strategies: Strategy[] = [
  {
    id: 'etf_rotation',
    name: 'ETF轮动策略',
    icon: '🔄',
    type: '动量策略',
    color: '#1f77b4',
    description: '基于动量因子的ETF轮动策略，选择动量最强的ETF进行持仓',
    logic: [
      '1. 计算各ETF的价格斜率（线性回归）',
      '2. 计算拟合优度R²评估趋势稳定性',
      '3. 综合评分 = 斜率 × R²',
      '4. 持有得分最高的N只ETF',
      '5. 触发止损则切换至货币基金',
    ],
    parameters: [
      {
        key: 'lookback_days',
        label: '回看天数',
        type: 'slider',
        default: 25,
        min: 10,
        max: 60,
        step: 5,
        description: '计算动量的历史天数',
      },
      {
        key: 'holdings_num',
        label: '持仓数量',
        type: 'slider',
        default: 2,
        min: 1,
        max: 5,
        step: 1,
        description: '同时持有的ETF数量',
      },
      {
        key: 'stop_loss',
        label: '止损比例',
        type: 'slider',
        default: 0.05,
        min: 0.03,
        max: 0.15,
        step: 0.01,
        description: '触发止损的跌幅阈值',
      },
    ],
    适用场景: '适合趋势明显、波动较大的市场环境',
    风险提示: '震荡市场可能频繁换仓，增加交易成本',
  },
  {
    id: 'dual_ma',
    name: '双均线策略',
    icon: '📈',
    type: '趋势跟踪',
    color: '#2ca02c',
    description: '经典的趋势跟踪策略，通过快慢均线交叉判断买卖时机',
    logic: [
      '1. 计算快速均线（短周期）',
      '2. 计算慢速均线（长周期）',
      '3. 金叉（快线上穿慢线）：买入',
      '4. 死叉（快线下穿慢线）：卖出',
      '5. 支持SMA、EMA等均线类型',
    ],
    parameters: [
      {
        key: 'fast_period',
        label: '快线周期',
        type: 'slider',
        default: 10,
        min: 5,
        max: 30,
        step: 5,
        description: '快速均线的计算周期',
      },
      {
        key: 'slow_period',
        label: '慢线周期',
        type: 'slider',
        default: 30,
        min: 20,
        max: 60,
        step: 10,
        description: '慢速均线的计算周期',
      },
      {
        key: 'ma_type',
        label: '均线类型',
        type: 'select',
        default: 'SMA',
        options: [
          { value: 'SMA', label: '简单移动平均' },
          { value: 'EMA', label: '指数移动平均' },
        ],
        description: '均线的计算方法',
      },
    ],
    适用场景: '适合有明显趋势的单边市场',
    风险提示: '震荡市场会产生频繁的假信号',
  },
  {
    id: 'rsi',
    name: 'RSI策略',
    icon: '📊',
    type: '均值回归',
    color: '#ff7f0e',
    description: '相对强弱指标策略，基于超买超卖区域进行反向操作',
    logic: [
      '1. 计算N日RSI指标',
      '2. RSI < 超卖阈值：买入信号',
      '3. RSI > 超买阈值：卖出信号',
      '4. 中性区间：持有当前仓位',
    ],
    parameters: [
      {
        key: 'rsi_period',
        label: 'RSI周期',
        type: 'slider',
        default: 14,
        min: 6,
        max: 30,
        step: 2,
        description: 'RSI指标的计算周期',
      },
      {
        key: 'oversold',
        label: '超卖阈值',
        type: 'slider',
        default: 30,
        min: 20,
        max: 40,
        step: 5,
        description: 'RSI低于此值视为超卖',
      },
      {
        key: 'overbought',
        label: '超买阈值',
        type: 'slider',
        default: 70,
        min: 60,
        max: 80,
        step: 5,
        description: 'RSI高于此值视为超买',
      },
    ],
    适用场景: '适合震荡市场，价格围绕均值波动',
    风险提示: '单边趋势市场可能持续超买/超卖',
  },
  {
    id: 'macd',
    name: 'MACD策略',
    icon: '📉',
    type: '趋势跟踪',
    color: '#2ca02c',
    description: '异同移动平均线策略，通过DIF和DEA的交叉捕捉趋势',
    logic: [
      '1. 计算快速EMA和慢速EMA',
      '2. DIF = 快速EMA - 慢速EMA',
      '3. DEA = DIF的M日EMA（信号线）',
      '4. DIF上穿DEA：买入',
      '5. DIF下穿DEA：卖出',
    ],
    parameters: [
      {
        key: 'fast_period',
        label: '快线周期',
        type: 'slider',
        default: 12,
        min: 6,
        max: 20,
        step: 2,
        description: '快速EMA周期',
      },
      {
        key: 'slow_period',
        label: '慢线周期',
        type: 'slider',
        default: 26,
        min: 20,
        max: 40,
        step: 2,
        description: '慢速EMA周期',
      },
      {
        key: 'signal_period',
        label: '信号线周期',
        type: 'slider',
        default: 9,
        min: 5,
        max: 15,
        step: 1,
        description: 'DEA信号线周期',
      },
    ],
    适用场景: '适合中长线趋势交易',
    风险提示: '信号有一定滞后性',
  },
  {
    id: 'bollinger',
    name: '布林带策略',
    icon: '📏',
    type: '均值回归',
    color: '#ff7f0e',
    description: '布林带通道策略，价格触及上下轨时进行反向操作',
    logic: [
      '1. 计算N日移动平均线（中轨）',
      '2. 计算N日标准差',
      '3. 上轨 = 中轨 + K×标准差',
      '4. 下轨 = 中轨 - K×标准差',
      '5. 价格触及下轨：买入',
      '6. 价格触及上轨：卖出',
    ],
    parameters: [
      {
        key: 'period',
        label: '周期',
        type: 'slider',
        default: 20,
        min: 10,
        max: 40,
        step: 5,
        description: '布林带的计算周期',
      },
      {
        key: 'std_dev',
        label: '标准差倍数',
        type: 'slider',
        default: 2,
        min: 1,
        max: 3,
        step: 0.5,
        description: '通道宽度的倍数',
      },
    ],
    适用场景: '适合震荡市场，价格在通道内波动',
    风险提示: '突破行情可能导致持续亏损',
  },
  {
    id: 'grid',
    name: '网格交易策略',
    icon: '🔲',
    type: '震荡套利',
    color: '#9467bd',
    description: '在价格区间内设置网格，低买高卖赚取波动收益',
    logic: [
      '1. 在价格区间内划分N个网格',
      '2. 每下跌一个网格：买入',
      '3. 每上涨一个网格：卖出',
      '4. 循环操作，赚取波动收益',
    ],
    parameters: [
      {
        key: 'grid_num',
        label: '网格数量',
        type: 'slider',
        default: 10,
        min: 5,
        max: 20,
        step: 1,
        description: '划分的网格数量',
      },
      {
        key: 'price_range',
        label: '价格区间',
        type: 'slider',
        default: 0.2,
        min: 0.1,
        max: 0.5,
        step: 0.05,
        description: '相对当前价格的波动范围',
      },
    ],
    适用场景: '适合震荡市场，价格在一定区间内波动',
    风险提示: '单边行情可能导致踏空或套牢',
  },
];

// ETF池配置
export interface ETF {
  code: string;
  name: string;
  type: '商品' | '海外' | '宽基' | '行业' | '货币';
  selected: boolean;
}

export const etfPool: ETF[] = [
  { code: '518880', name: '黄金ETF', type: '商品', selected: true },
  { code: '513100', name: '纳指ETF', type: '海外', selected: true },
  { code: '510300', name: '沪深300ETF', type: '宽基', selected: true },
  { code: '510500', name: '中证500ETF', type: '宽基', selected: true },
  { code: '159915', name: '创业板ETF', type: '宽基', selected: true },
  { code: '512010', name: '医药ETF', type: '行业', selected: false },
  { code: '512170', name: '医疗ETF', type: '行业', selected: false },
  { code: '515000', name: '科技ETF', type: '行业', selected: false },
  { code: '511880', name: '银华日利', type: '货币', selected: true },
];

// 回测配置
export interface BacktestConfig {
  strategy: StrategyType;
  startDate: string;
  endDate: string;
  initialCapital: number;
  benchmark: string;
  commission: number;
  stampDuty: number;
  slippage: number;
  parameters: Record<string, any>;
  etfCodes: string[];
}

export const defaultBacktestConfig: Partial<BacktestConfig> = {
  startDate: '2021-01-01',
  endDate: '2024-01-01',
  initialCapital: 100000,
  benchmark: '510300',
  commission: 0.0003,
  stampDuty: 0.001,
  slippage: 0.001,
};
