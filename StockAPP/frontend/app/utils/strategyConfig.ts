export type StrategyType = 'etf_rotation';

export type StrategyCategory = 'compound';

export interface Strategy {
  id: StrategyType;
  name: string;
  icon: string;
  category: StrategyCategory;
  type: '动量策略' | '趋势跟踪' | '均值回归' | '震荡套利' | '多因子选股' | '组合策略';
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
  type: 'number' | 'slider' | 'select' | 'boolean';
  default: number | string | boolean;
  min?: number;
  max?: number;
  step?: number;
  options?: { value: string; label: string }[];
  description: string;
}

const strategies: Strategy[] = [
  {
    id: 'etf_rotation',
    name: 'ETF轮动策略',
    icon: '🔄',
    category: 'compound',
    type: '动量策略',
    color: '#1f77b4',
    description: '基于动量因子的ETF轮动策略（完整版）。通过加权线性回归计算各ETF的斜率和R²值来评估动量质量，支持MA、RSI、MACD、成交量、布林带等多重过滤条件，具备近期大跌排除机制和ATR跟踪止损功能。',
    logic: [
      '1. 计算每个ETF的加权线性回归斜率（近期权重更高）',
      '2. 斜率代表动量方向，正值表示上涨趋势，负值表示下跌趋势',
      '3. 计算R²值评估趋势的稳定性和可靠性',
      '4. 多重过滤：短期动量、MA、RSI、MACD、成交量、布林带',
      '5. 近期大跌排除：近3日有单日跌幅超阈值则排除',
      '6. 综合得分 = 年化收益率 × R²，兼顾收益和稳定性',
      '7. 选择得分最高的ETF持有，定期调仓',
      '8. ATR跟踪止损 + 固定比例止损双重保护',
      '9. 防御ETF豁免部分过滤和止损条件',
      '10. 当所有ETF动量均为负时，切换至货币基金避险',
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
        description: '用于计算动量的历史天数',
      },
      {
        key: 'holdings_num',
        label: '持仓数量',
        type: 'slider',
        default: 1,
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
      {
        key: 'use_short_momentum',
        label: '短期动量过滤',
        type: 'boolean',
        default: true,
        description: '启用短期动量过滤',
      },
      {
        key: 'use_ma_filter',
        label: 'MA均线过滤',
        type: 'boolean',
        default: false,
        description: '启用MA均线过滤',
      },
      {
        key: 'use_rsi_filter',
        label: 'RSI过滤',
        type: 'boolean',
        default: false,
        description: '启用RSI过滤',
      },
      {
        key: 'use_atr_stop',
        label: 'ATR动态止损',
        type: 'boolean',
        default: true,
        description: '启用ATR动态止损',
      },
      {
        key: 'atr_trailing_stop',
        label: 'ATR跟踪止损',
        type: 'boolean',
        default: false,
        description: '使用ATR跟踪止损（否则为固定止损）',
      },
    ],
    适用场景: '适合趋势明显、波动较大的市场环境，能够有效捕捉板块轮动机会',
    风险提示: '震荡市场可能频繁换仓增加交易成本，趋势反转时可能产生较大回撤',
  },
];

export { strategies };

export const strategiesByCategory = {
  compound: strategies,
  simple: [] as Strategy[],
};

export interface ETF {
  code: string;
  name: string;
  type: '商品' | '海外' | '宽基' | '行业' | '货币' | '债券';
  selected: boolean;
}

export const etfPool: ETF[] = [
  { code: '518880', name: '黄金ETF', type: '商品', selected: true },
  { code: '159980', name: '有色ETF', type: '商品', selected: false },
  { code: '159985', name: '豆粕ETF', type: '商品', selected: false },
  { code: '501018', name: '南方原油LOF', type: '商品', selected: false },
  { code: '513100', name: '纳指ETF', type: '海外', selected: true },
  { code: '513500', name: '标普500ETF', type: '海外', selected: false },
  { code: '513520', name: '日经ETF', type: '海外', selected: false },
  { code: '513030', name: '德国ETF', type: '海外', selected: false },
  { code: '513080', name: '法国ETF', type: '海外', selected: false },
  { code: '159920', name: '恒生ETF', type: '海外', selected: false },
  { code: '510300', name: '沪深300ETF', type: '宽基', selected: true },
  { code: '510500', name: '中证500ETF', type: '宽基', selected: true },
  { code: '510050', name: '上证50ETF', type: '宽基', selected: false },
  { code: '510210', name: '上证指数ETF', type: '宽基', selected: false },
  { code: '159915', name: '创业板ETF', type: '宽基', selected: true },
  { code: '588080', name: '科创板50ETF', type: '宽基', selected: false },
  { code: '159995', name: '芯片ETF', type: '行业', selected: false },
  { code: '513050', name: '中概互联ETF', type: '行业', selected: false },
  { code: '159852', name: '半导体ETF', type: '行业', selected: false },
  { code: '159845', name: '新能源ETF', type: '行业', selected: false },
  { code: '515030', name: '新能源车ETF', type: '行业', selected: false },
  { code: '159806', name: '光伏ETF', type: '行业', selected: false },
  { code: '159928', name: '消费ETF', type: '行业', selected: false },
  { code: '512670', name: '国防军工ETF', type: '行业', selected: false },
  { code: '511010', name: '国债ETF', type: '债券', selected: false },
  { code: '511880', name: '银华日利', type: '货币', selected: true },
];

export interface BacktestConfig {
  strategy: StrategyType;
  startDate: string;
  endDate: string;
  initialCapital: number;
  benchmark: string;
  commission?: number;
  stampDuty?: number;
  slippage?: number;
  parameters: Record<string, any>;
  etfCodes: string[];
}

export const defaultBacktestConfig: Partial<BacktestConfig> = {
  startDate: '2015-01-01',
  endDate: new Date().toISOString().split('T')[0],
  initialCapital: 100000,
  benchmark: '510300',
  commission: 0.0003,
  stampDuty: 0.001,
  slippage: 0.001,
};
