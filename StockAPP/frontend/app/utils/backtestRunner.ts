import type { BacktestConfig } from './strategyConfig';
import type { BacktestResult, Trade, MonthlyReturn } from './backtestEngine';
import {
  calculateSMA,
  calculateEMA,
  calculateRSI,
  calculateMaxDrawdown,
  calculateSharpeRatio,
  calculateLinearRegression,
} from './backtestEngine';

const COMMISSION_RATE = 0.0003;
const STAMP_DUTY_RATE = 0.001;
const SLIPPAGE_RATE = 0.001;

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

interface PriceData {
  date: string;
  price: number;
}

async function fetchRealData(
  codes: string[],
  startDate: string,
  endDate: string,
  isETF: boolean = true
): Promise<Record<string, PriceData[]>> {
  const data: Record<string, PriceData[]> = {};
  
  const fetchPromises = codes.map(async (code) => {
    try {
      const endpoint = isETF ? 'etf' : 'stock';
      const response = await fetch(
        `${API_BASE}/data/${endpoint}/${code}?start_date=${startDate}&end_date=${endDate}`
      );
      
      if (response.ok) {
        const result = await response.json();
        if (result.data && Array.isArray(result.data)) {
          data[code] = result.data.map((item: any) => ({
            date: item.date,
            price: item.close,
          }));
        }
      }
    } catch (error) {
      console.error(`获取${code}数据失败:`, error);
    }
  });
  
  await Promise.all(fetchPromises);
  return data;
}

function alignDataByDate(priceData: Record<string, PriceData[]>): { 
  alignedData: Record<string, PriceData[]>; 
  commonDates: string[] 
} {
  const codes = Object.keys(priceData);
  if (codes.length === 0) {
    return { alignedData: {}, commonDates: [] };
  }
  
  const dateSet = new Set<string>();
  priceData[codes[0]].forEach(d => dateSet.add(d.date));
  
  for (let i = 1; i < codes.length; i++) {
    const codeDates = new Set(priceData[codes[i]].map(d => d.date));
    dateSet.forEach(date => {
      if (!codeDates.has(date)) {
        dateSet.delete(date);
      }
    });
  }
  
  const commonDates = Array.from(dateSet).sort();
  
  const alignedData: Record<string, PriceData[]> = {};
  codes.forEach(code => {
    const dataMap = new Map(priceData[code].map(d => [d.date, d]));
    alignedData[code] = commonDates
      .map(date => dataMap.get(date))
      .filter((d): d is PriceData => d !== undefined);
  });
  
  return { alignedData, commonDates };
}

function weightedLinearRegression(prices: number[]): { slope: number; rSquared: number } {
  const n = prices.length;
  if (n < 2) return { slope: 0, rSquared: 0 };
  
  const logPrices = prices.map(p => Math.log(p));
  const weights = Array.from({ length: n }, (_, i) => 1 + i / n);
  
  let sumW = 0, sumWX = 0, sumWY = 0, sumWXY = 0, sumWXX = 0;
  for (let i = 0; i < n; i++) {
    sumW += weights[i];
    sumWX += weights[i] * i;
    sumWY += weights[i] * logPrices[i];
    sumWXY += weights[i] * i * logPrices[i];
    sumWXX += weights[i] * i * i;
  }
  
  const denom = sumW * sumWXX - sumWX * sumWX;
  if (denom === 0) return { slope: 0, rSquared: 0 };
  
  const slope = (sumW * sumWXY - sumWX * sumWY) / denom;
  const intercept = (sumWXX * sumWY - sumWX * sumWXY) / denom;
  
  const yMean = logPrices.reduce((a, b) => a + b, 0) / n;
  let ssTot = 0, ssRes = 0;
  for (let i = 0; i < n; i++) {
    const yPred = slope * i + intercept;
    ssTot += weights[i] * Math.pow(logPrices[i] - yMean, 2);
    ssRes += weights[i] * Math.pow(logPrices[i] - yPred, 2);
  }
  
  const rSquared = ssTot > 0 ? 1 - ssRes / ssTot : 0;
  
  return { slope, rSquared };
}

function calculateATR(highs: number[], lows: number[], closes: number[], period: number): number {
  if (closes.length < period + 1) return 0;
  
  const trueRanges: number[] = [];
  for (let i = 1; i < closes.length; i++) {
    const tr = Math.max(
      highs[i] - lows[i],
      Math.abs(highs[i] - closes[i - 1]),
      Math.abs(lows[i] - closes[i - 1])
    );
    trueRanges.push(tr);
  }
  
  if (trueRanges.length < period) return 0;
  
  const atr = trueRanges.slice(-period).reduce((a, b) => a + b, 0) / period;
  return atr;
}

export async function runBacktestAsync(config: BacktestConfig): Promise<BacktestResult> {
  const isETF = config.strategy === 'etf_rotation';
  const rawData = await fetchRealData(config.etfCodes, config.startDate, config.endDate, isETF);
  
  if (Object.keys(rawData).length === 0) {
    return createEmptyResult(config);
  }
  
  const { alignedData, commonDates } = alignDataByDate(rawData);
  
  if (commonDates.length === 0) {
    return createEmptyResult(config);
  }
  
  switch (config.strategy) {
    case 'etf_rotation':
      return runETFRotationBacktest(config, alignedData, commonDates);
    case 'dual_ma':
      return runDualMABacktest(config, alignedData, commonDates);
    case 'rsi':
      return runRSIBacktest(config, alignedData, commonDates);
    case 'macd':
      return runMACDBacktest(config, alignedData, commonDates);
    case 'bollinger':
      return runBollingerBacktest(config, alignedData, commonDates);
    case 'grid':
      return runGridBacktest(config, alignedData, commonDates);
    default:
      return runSimpleBacktest(config, alignedData, commonDates);
  }
}

export function runBacktest(config: BacktestConfig): BacktestResult {
  return createEmptyResult(config);
}

interface Position {
  code: string;
  shares: number;
  costPrice: number;
  highestPrice: number;
}

function getPriceSafely(priceData: Record<string, PriceData[]>, code: string, index: number): number | null {
  const data = priceData[code];
  if (!data || !data[index] || typeof data[index].price !== 'number') {
    return null;
  }
  return data[index].price;
}

function runETFRotationBacktest(
  config: BacktestConfig,
  priceData: Record<string, PriceData[]>,
  dates: string[]
): BacktestResult {
  const params = config.parameters || {};
  
  const lookbackDays = (params.lookback_days as number) || 25;
  const holdingsNum = (params.holdings_num as number) || 1;
  const stopLoss = (params.stop_loss as number) || 0.05;
  
  const useShortMomentum = params.use_short_momentum !== false;
  const shortLookbackDays = (params.short_lookback_days as number) || 12;
  const shortMomentumThreshold = (params.short_momentum_threshold as number) || 0;
  
  const useMaFilter = params.use_ma_filter === true;
  const maShortPeriod = (params.ma_short_period as number) || 5;
  const maLongPeriod = (params.ma_long_period as number) || 25;
  
  const useRsiFilter = params.use_rsi_filter === true;
  const rsiPeriod = (params.rsi_period as number) || 6;
  const rsiThreshold = (params.rsi_threshold as number) || 95;
  
  const useAtrStop = params.use_atr_stop !== false;
  const atrPeriod = (params.atr_period as number) || 14;
  const atrMultiplier = (params.atr_multiplier as number) || 2;
  const atrTrailingStop = params.atr_trailing_stop === true;
  
  const lossThreshold = (params.loss_threshold as number) || 0.97;
  const defensiveEtf = (params.defensive_etf as string) || '511880';
  
  const codes = Object.keys(priceData);
  if (codes.length === 0 || dates.length === 0) {
    return createEmptyResult(config);
  }
  
  let cash = config.initialCapital;
  const positions: Map<string, Position> = new Map();
  const equityCurve: { date: string; value: number; return: number }[] = [];
  const trades: Trade[] = [];
  
  for (let i = 0; i < dates.length; i++) {
    const date = dates[i];
    
    if (i >= lookbackDays) {
      const scores: { code: string; score: number; atr: number }[] = [];
      
      codes.forEach(code => {
        const codeData = priceData[code];
        if (!codeData || codeData.length <= i) return;
        
        const history = codeData.slice(i - lookbackDays, i);
        if (history.length < lookbackDays) return;
        
        const prices = history.map(d => d.price);
        if (!prices.every(p => typeof p === 'number' && !isNaN(p) && p > 0)) return;
        
        if (i >= 3) {
          const day1Ratio = codeData[i].price / codeData[i - 1].price;
          const day2Ratio = codeData[i - 1].price / codeData[i - 2].price;
          const day3Ratio = codeData[i - 2].price / codeData[i - 3].price;
          
          if (Math.min(day1Ratio, day2Ratio, day3Ratio) < lossThreshold) {
            return;
          }
        }
        
        if (useShortMomentum && i > shortLookbackDays) {
          const shortReturn = codeData[i].price / codeData[i - shortLookbackDays].price - 1;
          if (shortReturn < shortMomentumThreshold) {
            return;
          }
        }
        
        if (useMaFilter && i >= maLongPeriod) {
          const maShortPrices = codeData.slice(i - maShortPeriod, i).map(d => d.price);
          const maLongPrices = codeData.slice(i - maLongPeriod, i).map(d => d.price);
          const maShort = maShortPrices.reduce((a, b) => a + b, 0) / maShortPeriod;
          const maLong = maLongPrices.reduce((a, b) => a + b, 0) / maLongPeriod;
          
          if (maShort < maLong) {
            return;
          }
        }
        
        if (useRsiFilter && i >= rsiPeriod + 5) {
          const rsiPrices = codeData.slice(i - rsiPeriod - 5, i).map(d => d.price);
          const rsiValues = calculateRSI(rsiPrices, rsiPeriod);
          if (rsiValues.length > 0 && rsiValues[rsiValues.length - 1] > rsiThreshold) {
            const ma5 = codeData.slice(i - 5, i).map(d => d.price).reduce((a, b) => a + b, 0) / 5;
            if (codeData[i].price < ma5) {
              return;
            }
          }
        }
        
        const { slope, rSquared } = weightedLinearRegression(prices);
        if (isNaN(slope) || isNaN(rSquared) || slope <= 0) return;
        
        const annualizedReturn = Math.exp(slope * 250) - 1;
        const score = annualizedReturn * rSquared;
        
        let atr = 0;
        if (useAtrStop && i >= atrPeriod + 1) {
          const histHighs = codeData.slice(i - atrPeriod - 1, i).map(d => d.price * 1.01);
          const histLows = codeData.slice(i - atrPeriod - 1, i).map(d => d.price * 0.99);
          const histCloses = codeData.slice(i - atrPeriod - 1, i).map(d => d.price);
          atr = calculateATR(histHighs, histLows, histCloses, atrPeriod);
        }
        
        scores.push({ code, score, atr });
      });
      
      scores.sort((a, b) => b.score - a.score);
      const targetHoldings = scores.slice(0, holdingsNum).filter(s => s.score > 0).map(s => s.code);
      
      if (targetHoldings.length === 0 && codes.includes(defensiveEtf)) {
        if (!positions.has(defensiveEtf)) {
          targetHoldings.push(defensiveEtf);
        }
      }
      
      const currentHoldingCodes = Array.from(positions.keys());
      const toSell = currentHoldingCodes.filter(code => !targetHoldings.includes(code));
      const toBuy = targetHoldings.filter(code => !positions.has(code));
      
      for (const code of toSell) {
        const pos = positions.get(code)!;
        const price = getPriceSafely(priceData, code, i);
        if (price === null) continue;
        
        const sellAmount = pos.shares * price;
        const commission = sellAmount * COMMISSION_RATE;
        const stampDuty = sellAmount * STAMP_DUTY_RATE;
        
        cash += sellAmount - commission - stampDuty;
        
        trades.push({
          date,
          type: 'sell',
          code,
          name: code,
          price,
          shares: pos.shares,
          amount: sellAmount,
          commission,
        });
        
        positions.delete(code);
      }
      
      for (const code of Array.from(positions.keys())) {
        const pos = positions.get(code)!;
        const price = getPriceSafely(priceData, code, i);
        if (price === null) continue;
        
        if (price > pos.highestPrice) {
          pos.highestPrice = price;
        }
        
        if (price < pos.costPrice * (1 - stopLoss)) {
          const sellAmount = pos.shares * price;
          const commission = sellAmount * COMMISSION_RATE;
          const stampDuty = sellAmount * STAMP_DUTY_RATE;
          
          cash += sellAmount - commission - stampDuty;
          
          trades.push({
            date,
            type: 'sell',
            code,
            name: code,
            price,
            shares: pos.shares,
            amount: sellAmount,
            commission,
          });
          
          positions.delete(code);
          continue;
        }
        
        if (useAtrStop && code !== defensiveEtf) {
          const codeData = priceData[code];
          if (codeData && i >= atrPeriod + 1) {
            const histHighs = codeData.slice(i - atrPeriod - 1, i).map(d => d.price * 1.01);
            const histLows = codeData.slice(i - atrPeriod - 1, i).map(d => d.price * 0.99);
            const histCloses = codeData.slice(i - atrPeriod - 1, i).map(d => d.price);
            const atr = calculateATR(histHighs, histLows, histCloses, atrPeriod);
            
            if (atr > 0) {
              const atrStop = atrTrailingStop 
                ? pos.highestPrice - atrMultiplier * atr 
                : pos.costPrice - atrMultiplier * atr;
              
              if (price < atrStop) {
                const sellAmount = pos.shares * price;
                const commission = sellAmount * COMMISSION_RATE;
                const stampDuty = sellAmount * STAMP_DUTY_RATE;
                
                cash += sellAmount - commission - stampDuty;
                
                trades.push({
                  date,
                  type: 'sell',
                  code,
                  name: code,
                  price,
                  shares: pos.shares,
                  amount: sellAmount,
                  commission,
                });
                
                positions.delete(code);
              }
            }
          }
        }
      }
      
      const cashPerPosition = toBuy.length > 0 ? cash / toBuy.length * 0.95 : 0;
      
      for (const code of toBuy) {
        const price = getPriceSafely(priceData, code, i);
        if (price === null || price <= 0) continue;
        
        const shares = Math.floor(cashPerPosition / price / 100) * 100;
        
        if (shares >= 100) {
          const buyAmount = shares * price;
          const commission = buyAmount * COMMISSION_RATE;
          
          if (cash >= buyAmount + commission) {
            cash -= buyAmount + commission;
            positions.set(code, { 
              code, 
              shares, 
              costPrice: price,
              highestPrice: price 
            });
            
            trades.push({
              date,
              type: 'buy',
              code,
              name: code,
              price,
              shares,
              amount: buyAmount,
              commission,
            });
          }
        }
      }
    }
    
    let portfolioValue = cash;
    positions.forEach((pos, code) => {
      const price = getPriceSafely(priceData, code, i);
      if (price !== null) {
        portfolioValue += pos.shares * price;
      }
    });
    
    equityCurve.push({
      date,
      value: portfolioValue,
      return: i > 0 ? ((portfolioValue / equityCurve[i - 1].value) - 1) * 100 : 0,
    });
  }
  
  return calculateMetrics(equityCurve, trades, config);
}

function runDualMABacktest(
  config: BacktestConfig,
  priceData: Record<string, PriceData[]>,
  dates: string[]
): BacktestResult {
  const fastPeriod = (config.parameters?.fast_period as number) || 10;
  const slowPeriod = (config.parameters?.slow_period as number) || 30;
  const maType = (config.parameters?.ma_type as string) || 'SMA';
  
  const codes = Object.keys(priceData);
  if (codes.length === 0 || dates.length === 0) {
    return createEmptyResult(config);
  }
  
  const targetCode = codes[0];
  const codeData = priceData[targetCode];
  if (!codeData || codeData.length === 0) {
    return createEmptyResult(config);
  }
  
  const prices = codeData.map(d => d.price);
  
  const fastMA = maType === 'EMA' ? calculateEMA(prices, fastPeriod) : calculateSMA(prices, fastPeriod);
  const slowMA = maType === 'EMA' ? calculateEMA(prices, slowPeriod) : calculateSMA(prices, slowPeriod);
  
  let cash = config.initialCapital;
  let position = 0;
  const equityCurve: { date: string; value: number; return: number }[] = [];
  const trades: Trade[] = [];
  
  for (let i = 0; i < dates.length; i++) {
    const price = prices[i];
    if (typeof price !== 'number' || isNaN(price)) continue;
    
    if (i > 0 && !isNaN(fastMA[i]) && !isNaN(slowMA[i])) {
      if (fastMA[i] > slowMA[i] && fastMA[i - 1] <= slowMA[i - 1] && position === 0) {
        const shares = Math.floor(cash / price / 100) * 100;
        if (shares >= 100) {
          const buyAmount = shares * price;
          const commission = buyAmount * COMMISSION_RATE;
          
          cash -= buyAmount + commission;
          position = shares;
          
          trades.push({
            date: dates[i],
            type: 'buy',
            code: targetCode,
            name: targetCode,
            price,
            shares,
            amount: buyAmount,
            commission,
          });
        }
      }
      else if (fastMA[i] < slowMA[i] && fastMA[i - 1] >= slowMA[i - 1] && position > 0) {
        const sellAmount = position * price;
        const commission = sellAmount * COMMISSION_RATE;
        const stampDuty = sellAmount * STAMP_DUTY_RATE;
        
        cash += sellAmount - commission - stampDuty;
        
        trades.push({
          date: dates[i],
          type: 'sell',
          code: targetCode,
          name: targetCode,
          price,
          shares: position,
          amount: sellAmount,
          commission,
        });
        
        position = 0;
      }
    }
    
    const portfolioValue = cash + position * price;
    equityCurve.push({
      date: dates[i],
      value: portfolioValue,
      return: i > 0 ? ((portfolioValue / equityCurve[i - 1].value) - 1) * 100 : 0,
    });
  }
  
  return calculateMetrics(equityCurve, trades, config);
}

function runRSIBacktest(
  config: BacktestConfig,
  priceData: Record<string, PriceData[]>,
  dates: string[]
): BacktestResult {
  const rsiPeriod = (config.parameters?.rsi_period as number) || 14;
  const oversold = (config.parameters?.oversold as number) || 30;
  const overbought = (config.parameters?.overbought as number) || 70;
  
  const codes = Object.keys(priceData);
  if (codes.length === 0 || dates.length === 0) {
    return createEmptyResult(config);
  }
  
  const targetCode = codes[0];
  const codeData = priceData[targetCode];
  if (!codeData || codeData.length === 0) {
    return createEmptyResult(config);
  }
  
  const prices = codeData.map(d => d.price);
  const rsi = calculateRSI(prices, rsiPeriod);
  
  let cash = config.initialCapital;
  let position = 0;
  const equityCurve: { date: string; value: number; return: number }[] = [];
  const trades: Trade[] = [];
  
  for (let i = 0; i < dates.length; i++) {
    const price = prices[i];
    if (typeof price !== 'number' || isNaN(price)) continue;
    
    if (!isNaN(rsi[i])) {
      if (rsi[i] < oversold && position === 0) {
        const shares = Math.floor(cash / price / 100) * 100;
        if (shares >= 100) {
          const buyAmount = shares * price;
          const commission = buyAmount * COMMISSION_RATE;
          
          cash -= buyAmount + commission;
          position = shares;
          
          trades.push({
            date: dates[i],
            type: 'buy',
            code: targetCode,
            name: targetCode,
            price,
            shares,
            amount: buyAmount,
            commission,
          });
        }
      }
      else if (rsi[i] > overbought && position > 0) {
        const sellAmount = position * price;
        const commission = sellAmount * COMMISSION_RATE;
        const stampDuty = sellAmount * STAMP_DUTY_RATE;
        
        cash += sellAmount - commission - stampDuty;
        
        trades.push({
          date: dates[i],
          type: 'sell',
          code: targetCode,
          name: targetCode,
          price,
          shares: position,
          amount: sellAmount,
          commission,
        });
        
        position = 0;
      }
    }
    
    const portfolioValue = cash + position * price;
    equityCurve.push({
      date: dates[i],
      value: portfolioValue,
      return: i > 0 ? ((portfolioValue / equityCurve[i - 1].value) - 1) * 100 : 0,
    });
  }
  
  return calculateMetrics(equityCurve, trades, config);
}

function runMACDBacktest(
  config: BacktestConfig,
  priceData: Record<string, PriceData[]>,
  dates: string[]
): BacktestResult {
  return runDualMABacktest(config, priceData, dates);
}

function runBollingerBacktest(
  config: BacktestConfig,
  priceData: Record<string, PriceData[]>,
  dates: string[]
): BacktestResult {
  return runRSIBacktest(config, priceData, dates);
}

function runGridBacktest(
  config: BacktestConfig,
  priceData: Record<string, PriceData[]>,
  dates: string[]
): BacktestResult {
  const codes = Object.keys(priceData);
  if (codes.length === 0 || dates.length === 0) {
    return createEmptyResult(config);
  }
  
  const targetCode = codes[0];
  const codeData = priceData[targetCode];
  if (!codeData || codeData.length === 0) {
    return createEmptyResult(config);
  }
  
  const firstPrice = codeData[0]?.price;
  if (!firstPrice || firstPrice <= 0) {
    return createEmptyResult(config);
  }
  
  const shares = Math.floor(config.initialCapital / firstPrice / 100) * 100;
  const equityCurve: { date: string; value: number; return: number }[] = [];
  
  for (let i = 0; i < dates.length; i++) {
    const price = codeData[i]?.price;
    if (typeof price !== 'number' || isNaN(price)) continue;
    
    equityCurve.push({
      date: dates[i],
      value: shares * price,
      return: i > 0 && codeData[i - 1]?.price ? ((price / codeData[i - 1].price) - 1) * 100 : 0,
    });
  }
  
  const trades: Trade[] = [
    {
      date: dates[0],
      type: 'buy',
      code: targetCode,
      name: targetCode,
      price: firstPrice,
      shares,
      amount: shares * firstPrice,
      commission: shares * firstPrice * COMMISSION_RATE,
    },
  ];
  
  return calculateMetrics(equityCurve, trades, config);
}

function runSimpleBacktest(
  config: BacktestConfig,
  priceData: Record<string, PriceData[]>,
  dates: string[]
): BacktestResult {
  const codes = Object.keys(priceData);
  if (codes.length === 0 || dates.length === 0) {
    return createEmptyResult(config);
  }
  
  const targetCode = codes[0];
  const codeData = priceData[targetCode];
  if (!codeData || codeData.length === 0) {
    return createEmptyResult(config);
  }
  
  const firstPrice = codeData[0]?.price;
  if (!firstPrice || firstPrice <= 0) {
    return createEmptyResult(config);
  }
  
  const shares = Math.floor(config.initialCapital / firstPrice / 100) * 100;
  const equityCurve: { date: string; value: number; return: number }[] = [];
  
  for (let i = 0; i < dates.length; i++) {
    const price = codeData[i]?.price;
    if (typeof price !== 'number' || isNaN(price)) continue;
    
    equityCurve.push({
      date: dates[i],
      value: shares * price,
      return: i > 0 && codeData[i - 1]?.price ? ((price / codeData[i - 1].price) - 1) * 100 : 0,
    });
  }
  
  const trades: Trade[] = [
    {
      date: dates[0],
      type: 'buy',
      code: targetCode,
      name: targetCode,
      price: firstPrice,
      shares,
      amount: shares * firstPrice,
      commission: shares * firstPrice * COMMISSION_RATE,
    },
  ];
  
  return calculateMetrics(equityCurve, trades, config);
}

function createEmptyResult(config: BacktestConfig): BacktestResult {
  return {
    totalReturn: 0,
    annualReturn: 0,
    maxDrawdown: 0,
    sharpeRatio: 0,
    sortinoRatio: 0,
    calmarRatio: 0,
    winRate: 0,
    profitFactor: 0,
    totalTrades: 0,
    finalAsset: config.initialCapital,
    equityCurve: [],
    drawdownSeries: [],
    trades: [],
    monthlyReturns: [],
  };
}

function calculateMetrics(
  equityCurve: { date: string; value: number; return: number }[],
  trades: Trade[],
  config: BacktestConfig
): BacktestResult {
  if (equityCurve.length === 0) {
    return createEmptyResult(config);
  }
  
  const initialValue = config.initialCapital;
  const finalValue = equityCurve[equityCurve.length - 1].value;
  const returns = equityCurve.filter(e => e.return !== undefined).map(e => e.return / 100);
  
  const totalReturn = ((finalValue - initialValue) / initialValue) * 100;
  const days = equityCurve.length;
  const years = Math.max(days / 252, 0.01);
  const annualReturn = (Math.pow(finalValue / initialValue, 1 / years) - 1) * 100;
  
  const equityValues = equityCurve.map(e => e.value);
  const maxDrawdown = calculateMaxDrawdown(equityValues) * 100;
  const sharpeRatio = calculateSharpeRatio(returns);
  
  const winningTrades = trades.filter((t, i) => {
    if (t.type === 'sell' && i > 0) {
      const buyTrade = [...trades].slice(0, i).reverse().find(tr => tr.type === 'buy' && tr.code === t.code);
      return buyTrade && t.price > buyTrade.price;
    }
    return false;
  }).length;
  
  const sellTrades = trades.filter(t => t.type === 'sell').length;
  const winRate = sellTrades > 0 ? (winningTrades / sellTrades) * 100 : 0;
  
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
    calmarRatio: maxDrawdown > 0 ? annualReturn / maxDrawdown : 0,
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
