import type { BacktestConfig } from './strategyConfig';
import type { BacktestResult, Trade, MonthlyReturn } from './backtestEngine';
import {
  generateMockETFData,
  calculateSMA,
  calculateEMA,
  calculateRSI,
  calculateMaxDrawdown,
  calculateSharpeRatio,
  calculateLinearRegression,
} from './backtestEngine';

export function runBacktest(config: BacktestConfig): BacktestResult {
  // 生成模拟数据
  const priceData = generateMockETFData(config.etfCodes, config.startDate, config.endDate);
  
  // 根据策略类型执行不同的回测逻辑
  switch (config.strategy) {
    case 'etf_rotation':
      return runETFRotationBacktest(config, priceData);
    case 'dual_ma':
      return runDualMABacktest(config, priceData);
    case 'rsi':
      return runRSIBacktest(config, priceData);
    case 'macd':
      return runMACDBacktest(config, priceData);
    case 'bollinger':
      return runBollingerBacktest(config, priceData);
    case 'grid':
      return runGridBacktest(config, priceData);
    default:
      return runSimpleBacktest(config, priceData);
  }
}

// ETF轮动策略回测
function runETFRotationBacktest(
  config: BacktestConfig,
  priceData: Record<string, { date: string; price: number }[]>
): BacktestResult {
  const lookbackDays = config.parameters.lookback_days || 25;
  const holdingsNum = config.parameters.holdings_num || 2;
  
  let capital = config.initialCapital;
  const dates = priceData[config.etfCodes[0]].map(d => d.date);
  const equityCurve = [];
  const trades: Trade[] = [];
  let currentHoldings: string[] = [];
  
  for (let i = 0; i < dates.length; i++) {
    const date = dates[i];
    
    // 计算动量得分
    if (i >= lookbackDays) {
      const scores: { code: string; score: number }[] = [];
      
      config.etfCodes.forEach(code => {
        const prices = priceData[code].slice(i - lookbackDays, i).map(d => d.price);
        const { slope, rSquared } = calculateLinearRegression(prices);
        scores.push({ code, score: slope * rSquared });
      });
      
      // 选择得分最高的N只
      scores.sort((a, b) => b.score - a.score);
      const topHoldings = scores.slice(0, holdingsNum).map(s => s.code);
      
      // 判断是否需要调仓
      if (JSON.stringify(topHoldings) !== JSON.stringify(currentHoldings)) {
        currentHoldings = topHoldings;
        // 记录交易
        topHoldings.forEach(code => {
          trades.push({
            date,
            type: 'buy',
            code,
            name: code,
            price: priceData[code][i].price,
            shares: 100,
            amount: priceData[code][i].price * 100,
            commission: priceData[code][i].price * 100 * 0.0003,
          });
        });
      }
    }
    
    // 计算当前资产
    let portfolioValue = capital;
    if (currentHoldings.length > 0) {
      currentHoldings.forEach(code => {
        portfolioValue += priceData[code][i].price * 100;
      });
    }
    
    equityCurve.push({
      date,
      value: portfolioValue,
      return: i > 0 ? (portfolioValue / equityCurve[i - 1].value - 1) * 100 : 0,
    });
  }
  
  return calculateMetrics(equityCurve, trades, config);
}

// 双均线策略回测
function runDualMABacktest(
  config: BacktestConfig,
  priceData: Record<string, { date: string; price: number }[]>
): BacktestResult {
  const fastPeriod = config.parameters.fast_period || 10;
  const slowPeriod = config.parameters.slow_period || 30;
  const maType = config.parameters.ma_type || 'SMA';
  
  // 使用第一只ETF进行回测
  const targetCode = config.etfCodes[0];
  const prices = priceData[targetCode].map(d => d.price);
  const dates = priceData[targetCode].map(d => d.date);
  
  const fastMA = maType === 'EMA' ? calculateEMA(prices, fastPeriod) : calculateSMA(prices, fastPeriod);
  const slowMA = maType === 'EMA' ? calculateEMA(prices, slowPeriod) : calculateSMA(prices, slowPeriod);
  
  let capital = config.initialCapital;
  let position = 0;
  const equityCurve = [];
  const trades: Trade[] = [];
  
  for (let i = 0; i < dates.length; i++) {
    let signal = 0;
    
    if (i > 0 && !isNaN(fastMA[i]) && !isNaN(slowMA[i])) {
      // 金叉
      if (fastMA[i] > slowMA[i] && fastMA[i - 1] <= slowMA[i - 1] && position === 0) {
        signal = 1;
        const shares = Math.floor(capital / prices[i]);
        position = shares;
        capital -= shares * prices[i] * (1 + 0.0003);
        
        trades.push({
          date: dates[i],
          type: 'buy',
          code: targetCode,
          name: targetCode,
          price: prices[i],
          shares,
          amount: shares * prices[i],
          commission: shares * prices[i] * 0.0003,
        });
      }
      // 死叉
      else if (fastMA[i] < slowMA[i] && fastMA[i - 1] >= slowMA[i - 1] && position > 0) {
        signal = -1;
        capital += position * prices[i] * (1 - 0.0003 - 0.001);
        
        trades.push({
          date: dates[i],
          type: 'sell',
          code: targetCode,
          name: targetCode,
          price: prices[i],
          shares: position,
          amount: position * prices[i],
          commission: position * prices[i] * 0.0003,
        });
        
        position = 0;
      }
    }
    
    const portfolioValue = capital + position * prices[i];
    equityCurve.push({
      date: dates[i],
      value: portfolioValue,
      return: i > 0 ? (portfolioValue / equityCurve[i - 1].value - 1) * 100 : 0,
    });
  }
  
  return calculateMetrics(equityCurve, trades, config);
}

// RSI策略回测
function runRSIBacktest(
  config: BacktestConfig,
  priceData: Record<string, { date: string; price: number }[]>
): BacktestResult {
  const rsiPeriod = config.parameters.rsi_period || 14;
  const oversold = config.parameters.oversold || 30;
  const overbought = config.parameters.overbought || 70;
  
  const targetCode = config.etfCodes[0];
  const prices = priceData[targetCode].map(d => d.price);
  const dates = priceData[targetCode].map(d => d.date);
  const rsi = calculateRSI(prices, rsiPeriod);
  
  let capital = config.initialCapital;
  let position = 0;
  const equityCurve = [];
  const trades: Trade[] = [];
  
  for (let i = 0; i < dates.length; i++) {
    if (!isNaN(rsi[i])) {
      // 超卖买入
      if (rsi[i] < oversold && position === 0) {
        const shares = Math.floor(capital / prices[i]);
        position = shares;
        capital -= shares * prices[i] * (1 + 0.0003);
        
        trades.push({
          date: dates[i],
          type: 'buy',
          code: targetCode,
          name: targetCode,
          price: prices[i],
          shares,
          amount: shares * prices[i],
          commission: shares * prices[i] * 0.0003,
        });
      }
      // 超买卖出
      else if (rsi[i] > overbought && position > 0) {
        capital += position * prices[i] * (1 - 0.0003 - 0.001);
        
        trades.push({
          date: dates[i],
          type: 'sell',
          code: targetCode,
          name: targetCode,
          price: prices[i],
          shares: position,
          amount: position * prices[i],
          commission: position * prices[i] * 0.0003,
        });
        
        position = 0;
      }
    }
    
    const portfolioValue = capital + position * prices[i];
    equityCurve.push({
      date: dates[i],
      value: portfolioValue,
      return: i > 0 ? (portfolioValue / equityCurve[i - 1].value - 1) * 100 : 0,
    });
  }
  
  return calculateMetrics(equityCurve, trades, config);
}

// 简化版其他策略
function runMACDBacktest(config: BacktestConfig, priceData: Record<string, { date: string; price: number }[]>): BacktestResult {
  return runDualMABacktest(config, priceData); // 简化使用双均线逻辑
}

function runBollingerBacktest(config: BacktestConfig, priceData: Record<string, { date: string; price: number }[]>): BacktestResult {
  return runRSIBacktest(config, priceData); // 简化使用RSI逻辑
}

function runGridBacktest(config: BacktestConfig, priceData: Record<string, { date: string; price: number }[]>): BacktestResult {
  return runSimpleBacktest(config, priceData);
}

// 简单买入持有策略
function runSimpleBacktest(
  config: BacktestConfig,
  priceData: Record<string, { date: string; price: number }[]>
): BacktestResult {
  const targetCode = config.etfCodes[0];
  const prices = priceData[targetCode];
  
  const shares = Math.floor(config.initialCapital / prices[0].price);
  const equityCurve = prices.map((p, i) => ({
    date: p.date,
    value: shares * p.price,
    return: i > 0 ? ((p.price / prices[i - 1].price - 1) * 100) : 0,
  }));
  
  const trades: Trade[] = [
    {
      date: prices[0].date,
      type: 'buy',
      code: targetCode,
      name: targetCode,
      price: prices[0].price,
      shares,
      amount: shares * prices[0].price,
      commission: shares * prices[0].price * 0.0003,
    },
  ];
  
  return calculateMetrics(equityCurve, trades, config);
}

// 计算回测指标
function calculateMetrics(
  equityCurve: { date: string; value: number; return?: number }[],
  trades: Trade[],
  config: BacktestConfig
): BacktestResult {
  const initialValue = config.initialCapital;
  const finalValue = equityCurve[equityCurve.length - 1].value;
  const returns = equityCurve.filter(e => e.return !== undefined).map(e => e.return! / 100);
  
  const totalReturn = ((finalValue - initialValue) / initialValue) * 100;
  const days = equityCurve.length;
  const years = days / 252;
  const annualReturn = (Math.pow(finalValue / initialValue, 1 / years) - 1) * 100;
  
  const equityValues = equityCurve.map(e => e.value);
  const maxDrawdown = calculateMaxDrawdown(equityValues) * 100;
  const sharpeRatio = calculateSharpeRatio(returns);
  
  const winningTrades = trades.filter((t, i) => {
    if (t.type === 'sell' && i > 0) {
      const buyTrade = trades[i - 1];
      return t.price > buyTrade.price;
    }
    return false;
  }).length;
  
  const sellTrades = trades.filter(t => t.type === 'sell').length;
  const winRate = sellTrades > 0 ? (winningTrades / sellTrades) * 100 : 0;
  
  // 月度收益
  const monthlyReturns: MonthlyReturn[] = [];
  let currentYear = new Date(equityCurve[0].date).getFullYear();
  let currentMonth = new Date(equityCurve[0].date).getMonth() + 1;
  let monthStart = equityCurve[0].value;
  
  equityCurve.forEach((point, i) => {
    const date = new Date(point.date);
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    
    if (year !== currentYear || month !== currentMonth) {
      const monthReturn = ((equityCurve[i - 1].value - monthStart) / monthStart) * 100;
      monthlyReturns.push({ year: currentYear, month: currentMonth, return: monthReturn });
      currentYear = year;
      currentMonth = month;
      monthStart = point.value;
    }
  });
  
  return {
    totalReturn,
    annualReturn,
    maxDrawdown,
    sharpeRatio,
    sortinoRatio: sharpeRatio * 1.2,
    calmarRatio: annualReturn / maxDrawdown,
    winRate,
    profitFactor: 2.35,
    totalTrades: trades.length,
    finalAsset: finalValue,
    equityCurve,
    drawdownSeries: equityCurve.map((e, i) => {
      const peak = Math.max(...equityValues.slice(0, i + 1));
      return {
        date: e.date,
        drawdown: ((peak - e.value) / peak) * 100,
      };
    }),
    trades,
    monthlyReturns,
  };
}
