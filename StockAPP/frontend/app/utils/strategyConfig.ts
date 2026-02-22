export type StrategyType = 'etf_rotation' | 'large_cap_low_drawdown' | 'dual_ma' | 'rsi' | 'macd' | 'bollinger' | 'grid';

export type StrategyCategory = 'simple' | 'compound';

export interface Strategy {
  id: StrategyType;
  name: string;
  icon: string;
  category: StrategyCategory;
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
  type: 'number' | 'slider' | 'select' | 'boolean';
  default: number | string | boolean;
  min?: number;
  max?: number;
  step?: number;
  options?: { value: string; label: string }[];
  description: string;
}

const compoundStrategies: Strategy[] = [
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
  {
    id: 'large_cap_low_drawdown',
    name: '大市值低回撤策略',
    icon: '🛡️',
    category: 'compound',
    type: '动量策略',
    color: '#2ca02c',
    description: '基于六因子打分系统的股票策略，从沪深300成分股中筛选优质标的。结合RSRS择时指标和回撤锁定机制，实现低回撤稳健收益。六因子包括：5日动量、20日动量、趋势强度、量比、波动率、市值因子。',
    logic: [
      '1. 六因子打分系统筛选沪深300优质股票',
      '2. RSRS择时指标判断市场趋势强度',
      '3. 沪深300站上20日线+MACD金叉+RSRS>0.7时解锁',
      '4. 回撤超10%触发锁定，清仓避险',
      '5. 分批解锁：首次解锁允许30%仓位',
      '6. 冷却期：解锁后10天内不触发强锁定',
      '7. 完全解锁：回撤降至5%以下',
      '8. 牛市加仓至95%，熊市减仓至60%',
      '9. 个股止盈35%，止损5%',
    ],
    parameters: [
      {
        key: 'max_positions',
        label: '最大持仓数量',
        type: 'slider',
        default: 3,
        min: 1,
        max: 5,
        step: 1,
        description: '最大持仓股票数量',
      },
      {
        key: 'stop_loss_ratio',
        label: '个股止损比例',
        type: 'slider',
        default: 0.05,
        min: 0.03,
        max: 0.10,
        step: 0.01,
        description: '个股止损阈值',
      },
      {
        key: 'take_profit_ratio',
        label: '个股止盈比例',
        type: 'slider',
        default: 0.35,
        min: 0.15,
        max: 0.50,
        step: 0.05,
        description: '个股止盈阈值',
      },
      {
        key: 'drawdown_lock_threshold',
        label: '回撤锁定阈值',
        type: 'slider',
        default: 0.10,
        min: 0.05,
        max: 0.15,
        step: 0.01,
        description: '触发锁定的回撤阈值',
      },
      {
        key: 'use_rsrs_timing',
        label: 'RSRS择时指标',
        type: 'boolean',
        default: true,
        description: '启用RSRS择时指标',
      },
      {
        key: 'use_partial_unlock',
        label: '分批解锁机制',
        type: 'boolean',
        default: true,
        description: '启用分批解锁机制',
      },
      {
        key: 'rsrs_buy_threshold',
        label: 'RSRS买入阈值',
        type: 'slider',
        default: 0.7,
        min: 0.5,
        max: 1.0,
        step: 0.1,
        description: 'RSRS标准分买入阈值',
      },
    ],
    适用场景: '适合趋势明显的市场环境，追求稳健收益、低回撤的投资者',
    风险提示: '震荡市场可能频繁换仓增加交易成本，极端行情下可能产生较大回撤',
  },
];

const simpleStrategies: Strategy[] = [
  {
    id: 'dual_ma',
    name: '双均线策略',
    icon: '📈',
    category: 'simple',
    type: '趋势跟踪',
    color: '#2ca02c',
    description: '经典的趋势跟踪策略。通过计算两条不同周期的移动平均线，利用它们的交叉来判断市场趋势的变化。当短期均线上穿长期均线时形成金叉，视为买入信号；当短期均线下穿长期均线时形成死叉，视为卖出信号。该策略简单有效，是技术分析中最基础的趋势判断方法之一。',
    logic: [
      '1. 计算快速均线（短期，如5日、10日）',
      '2. 计算慢速均线（长期，如20日、30日）',
      '3. 金叉信号：快线上穿慢线，表示短期趋势转强，买入',
      '4. 死叉信号：快线下穿慢线，表示短期趋势转弱，卖出',
      '5. 支持SMA（简单移动平均）和EMA（指数移动平均）两种类型',
      '6. EMA对近期价格赋予更高权重，反应更灵敏',
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
    适用场景: '适合有明显趋势的单边市场，能够有效捕捉中长期趋势行情',
    风险提示: '震荡市场会产生频繁的假信号，可能导致连续止损',
  },
  {
    id: 'rsi',
    name: 'RSI策略',
    icon: '📊',
    category: 'simple',
    type: '均值回归',
    color: '#ff7f0e',
    description: '基于相对强弱指标(RSI)的超买超卖策略。RSI是衡量价格变动速度和变化幅度的动量指标，取值范围0-100。当RSI低于超卖阈值时，表示价格可能过度下跌，存在反弹机会；当RSI高于超买阈值时，表示价格可能过度上涨，存在回调风险。该策略利用价格过度反应后的均值回归特性进行反向操作。',
    logic: [
      '1. 计算N日RSI指标值（默认14日）',
      '2. RSI取值范围0-100，反映价格变动的相对强度',
      '3. RSI < 超卖阈值（默认30）：表示超卖，买入信号',
      '4. RSI > 超买阈值（默认70）：表示超买，卖出信号',
      '5. 中性区间（30-70）：持有当前仓位，不操作',
      '6. 可根据市场特性调整超买超卖阈值',
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
    适用场景: '适合震荡市场，价格围绕均值波动的行情，能够有效捕捉短期超调机会',
    风险提示: '单边趋势市场中可能持续超买或超卖，导致逆势操作产生亏损',
  },
  {
    id: 'macd',
    name: 'MACD策略',
    icon: '📉',
    category: 'simple',
    type: '趋势跟踪',
    color: '#2ca02c',
    description: '基于异同移动平均线(MACD)的趋势跟踪策略。MACD是技术分析中最经典的指标之一，由快线EMA12、慢线EMA26和信号线DEA9组成。DIF线反映短期与长期均线的偏离程度，DEA线是DIF的平滑处理。当DIF上穿DEA形成金叉时，表示趋势转强；当DIF下穿DEA形成死叉时，表示趋势转弱。该策略适合捕捉中长线趋势。',
    logic: [
      '1. 计算快速EMA（默认12日）和慢速EMA（默认26日）',
      '2. DIF = 快速EMA - 慢速EMA，反映均线偏离度',
      '3. DEA = DIF的M日EMA（默认9日），即信号线',
      '4. MACD柱 = (DIF - DEA) × 2，反映动能强度',
      '5. 金叉信号：DIF上穿DEA，买入',
      '6. 死叉信号：DIF下穿DEA，卖出',
      '7. 可选柱状图确认：只在柱状图同向时交易',
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
    适用场景: '适合中长线趋势交易，能够有效过滤短期噪音，捕捉主要趋势',
    风险提示: '震荡市场信号较多，存在一定滞后性，可能错过最佳入场点',
  },
  {
    id: 'bollinger',
    name: '布林带策略',
    icon: '📏',
    category: 'simple',
    type: '均值回归',
    color: '#ff7f0e',
    description: '基于布林带指标的均值回归策略。布林带由三条轨道线组成：中轨是N日移动平均线，上轨和下轨分别是中轨加减K倍标准差。价格通常在上下轨之间波动，当价格触及下轨时表示超卖，触及上轨时表示超买。该策略假设价格会回归均值，在极端位置进行反向操作。',
    logic: [
      '1. 计算中轨：N日移动平均线（默认20日）',
      '2. 计算标准差：N日价格的标准差',
      '3. 上轨 = 中轨 + K × 标准差（默认K=2）',
      '4. 下轨 = 中轨 - K × 标准差',
      '5. 价格触及下轨：超卖信号，买入',
      '6. 价格触及上轨：超买信号，卖出',
      '7. 可选中轨平仓：价格回归中轨时平仓',
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
    适用场景: '适合震荡市场，价格在一定区间内波动，能够有效捕捉超买超卖机会',
    风险提示: '突破行情可能导致持续亏损，价格可能沿轨道运行而非回归',
  },
  {
    id: 'grid',
    name: '网格交易策略',
    icon: '🔲',
    category: 'simple',
    type: '震荡套利',
    color: '#9467bd',
    description: '在设定价格区间内划分网格，低买高卖赚取震荡收益的自动化交易策略。策略将价格区间划分为若干网格，当价格下跌穿越网格线时分批买入，当价格上涨穿越网格线时分批卖出。通过频繁的小额交易累积收益，适合波动较大但整体横盘震荡的市场环境。',
    logic: [
      '1. 设定价格区间和网格数量（如10格）',
      '2. 计算网格间距 = (上限 - 下限) / 网格数',
      '3. 在每个网格点预设买卖单',
      '4. 价格下跌穿越网格线：买入一份',
      '5. 价格上涨穿越网格线：卖出一份',
      '6. 循环操作，赚取波动收益',
      '7. 支持ATR动态调整网格范围',
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
    适用场景: '适合震荡市场，价格在一定区间内波动，能够稳定赚取波动收益',
    风险提示: '单边趋势行情可能导致踏空或套牢，需要设置止损',
  },
];

export const strategies: Strategy[] = [...compoundStrategies, ...simpleStrategies];

export const strategiesByCategory = {
  compound: compoundStrategies,
  simple: simpleStrategies,
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
