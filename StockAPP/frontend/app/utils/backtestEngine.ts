// 回测结果数据结构
export interface BacktestResult {
  // 基础指标
  totalReturn: number; // 总收益率
  annualReturn: number; // 年化收益率
  maxDrawdown: number; // 最大回撤
  sharpeRatio: number; // 夏普比率
  sortinoRatio: number; // 索提诺比率
  calmarRatio: number; // 卡玛比率
  winRate: number; // 胜率
  profitFactor: number; // 盈亏比
  totalTrades: number; // 交易次数
  finalAsset: number; // 最终资产

  // 实际回测时间
  actualStartDate?: string;
  actualEndDate?: string;

  // 时间序列数据
  equityCurve: EquityPoint[]; // 资金曲线
  drawdownSeries: DrawdownPoint[]; // 回撤序列
  trades: Trade[]; // 交易记录
  monthlyReturns: MonthlyReturn[]; // 月度收益

  // 对比数据
  benchmarkEquity?: EquityPoint[]; // 基准曲线
  excessReturn?: number; // 超额收益
}

export interface EquityPoint {
  date: string;
  value: number;
  return?: number;
}

export interface DrawdownPoint {
  date: string;
  drawdown: number;
}

export interface Trade {
  date: string;
  type: 'buy' | 'sell';
  code: string;
  name: string;
  price: number;
  shares: number;
  amount: number;
  commission: number;
}

export interface MonthlyReturn {
  year: number;
  month: number;
  return: number;
}

// 生成模拟的价格数据
export function generateMockPriceData(
  startDate: string,
  endDate: string,
  basePrice: number = 100,
  volatility: number = 0.02,
  trend: number = 0.0003
): { date: string; price: number }[] {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const data: { date: string; price: number }[] = [];
  
  let currentPrice = basePrice;
  let currentDate = new Date(start);
  
  while (currentDate <= end) {
    // 跳过周末
    if (currentDate.getDay() !== 0 && currentDate.getDay() !== 6) {
      // 随机游走 + 趋势
      const randomReturn = (Math.random() - 0.5) * volatility;
      currentPrice = currentPrice * (1 + trend + randomReturn);
      
      data.push({
        date: currentDate.toISOString().split('T')[0],
        price: currentPrice,
      });
    }
    
    currentDate.setDate(currentDate.getDate() + 1);
  }
  
  return data;
}

// 生成模拟的ETF数据
export function generateMockETFData(
  etfCodes: string[],
  startDate: string,
  endDate: string
): Record<string, { date: string; price: number }[]> {
  const data: Record<string, { date: string; price: number }[]> = {};
  
  etfCodes.forEach((code, index) => {
    // 不同ETF有不同的特性
    let volatility = 0.015 + Math.random() * 0.01;
    let trend = 0.0002 + (Math.random() - 0.5) * 0.0002;
    let basePrice = 1 + index * 0.5;
    
    // 货币基金特殊处理
    if (code === '511880') {
      volatility = 0.0001;
      trend = 0.0001;
      basePrice = 100;
    }
    
    data[code] = generateMockPriceData(startDate, endDate, basePrice, volatility, trend);
  });
  
  return data;
}

// 计算简单移动平均
export function calculateSMA(prices: number[], period: number): number[] {
  const sma: number[] = [];
  for (let i = 0; i < prices.length; i++) {
    if (i < period - 1) {
      sma.push(NaN);
    } else {
      const sum = prices.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
      sma.push(sum / period);
    }
  }
  return sma;
}

// 计算指数移动平均
export function calculateEMA(prices: number[], period: number): number[] {
  const ema: number[] = [];
  const multiplier = 2 / (period + 1);
  
  // 第一个EMA值使用SMA
  const firstSMA = prices.slice(0, period).reduce((a, b) => a + b, 0) / period;
  
  for (let i = 0; i < prices.length; i++) {
    if (i < period - 1) {
      ema.push(NaN);
    } else if (i === period - 1) {
      ema.push(firstSMA);
    } else {
      ema.push((prices[i] - ema[i - 1]) * multiplier + ema[i - 1]);
    }
  }
  
  return ema;
}

// 计算RSI
export function calculateRSI(prices: number[], period: number): number[] {
  const rsi: number[] = [];
  
  for (let i = 0; i < prices.length; i++) {
    if (i < period) {
      rsi.push(NaN);
      continue;
    }
    
    let gains = 0;
    let losses = 0;
    
    for (let j = i - period + 1; j <= i; j++) {
      const change = prices[j] - prices[j - 1];
      if (change > 0) gains += change;
      else losses -= change;
    }
    
    const avgGain = gains / period;
    const avgLoss = losses / period;
    
    if (avgLoss === 0) {
      rsi.push(100);
    } else {
      const rs = avgGain / avgLoss;
      rsi.push(100 - 100 / (1 + rs));
    }
  }
  
  return rsi;
}

// 计算标准差
export function calculateStdDev(values: number[]): number {
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const squaredDiffs = values.map(v => Math.pow(v - mean, 2));
  const variance = squaredDiffs.reduce((a, b) => a + b, 0) / values.length;
  return Math.sqrt(variance);
}

// 计算线性回归斜率和R²
export function calculateLinearRegression(
  prices: number[]
): { slope: number; rSquared: number } {
  const n = prices.length;
  const x = Array.from({ length: n }, (_, i) => i);
  const y = prices;
  
  const sumX = x.reduce((a, b) => a + b, 0);
  const sumY = y.reduce((a, b) => a + b, 0);
  const sumXY = x.reduce((sum, xi, i) => sum + xi * y[i], 0);
  const sumX2 = x.reduce((sum, xi) => sum + xi * xi, 0);
  const sumY2 = y.reduce((sum, yi) => sum + yi * yi, 0);
  
  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  
  const meanY = sumY / n;
  const ssTotal = y.reduce((sum, yi) => sum + Math.pow(yi - meanY, 2), 0);
  const yPred = x.map(xi => (sumY - slope * sumX) / n + slope * xi);
  const ssResidual = y.reduce((sum, yi, i) => sum + Math.pow(yi - yPred[i], 2), 0);
  const rSquared = 1 - ssResidual / ssTotal;
  
  return { slope, rSquared };
}

// 计算最大回撤
export function calculateMaxDrawdown(equityCurve: number[]): number {
  let maxDrawdown = 0;
  let peak = equityCurve[0];
  
  for (const value of equityCurve) {
    if (value > peak) {
      peak = value;
    }
    const drawdown = (peak - value) / peak;
    if (drawdown > maxDrawdown) {
      maxDrawdown = drawdown;
    }
  }
  
  return maxDrawdown;
}

// 计算夏普比率
export function calculateSharpeRatio(returns: number[], riskFreeRate: number = 0.03): number {
  const excessReturns = returns.map(r => r - riskFreeRate / 252);
  const meanExcessReturn = excessReturns.reduce((a, b) => a + b, 0) / excessReturns.length;
  const stdDev = calculateStdDev(excessReturns);
  return stdDev === 0 ? 0 : (meanExcessReturn / stdDev) * Math.sqrt(252);
}
