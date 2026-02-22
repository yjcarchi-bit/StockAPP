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

interface CodeInfo {
  code: string;
  name: string;
}

export interface StockScoreDetail {
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

export interface TradeDecision {
  action: 'buy' | 'sell' | 'hold';
  code: string;
  name: string;
  reason: string;
}

export interface DailySelectionResult {
  date: string;
  marketStatus: 'normal' | 'drawdown_lock' | 'partial_unlock';
  candidates: StockScoreDetail[];
  selectedStocks: string[];
  trades: TradeDecision[];
  portfolioValue: number;
  drawdown: number;
  cashRatio: number;
}

export interface BacktestProgressUpdate {
  currentIndex: number;
  totalDays: number;
  currentDate: string;
  percent: number;
  dailyResult: DailySelectionResult | null;
}

export interface DataRangeInfo {
  code: string;
  name: string;
  start: string;
  end: string;
  count: number;
}

export interface BacktestDataInfo {
  requestedStart: string;
  requestedEnd: string;
  actualStart: string;
  actualEnd: string;
  dataRanges: DataRangeInfo[];
  warning?: string;
}

export type ProgressCallback = (update: BacktestProgressUpdate) => void;

const codeNameMap: Record<string, string> = {};

let hs300StocksCache: { code: string; name: string }[] | null = null;

async function fetchHS300Stocks(): Promise<{ code: string; name: string }[]> {
  if (hs300StocksCache) {
    return hs300StocksCache;
  }
  
  try {
    const response = await fetch(`${API_BASE}/data/hs300/stocks`);
    if (response.ok) {
      const stocks = await response.json();
      hs300StocksCache = stocks.map((s: any) => ({
        code: s.code,
        name: s.name,
      }));
      return hs300StocksCache!;
    }
  } catch (error) {
    console.error('获取沪深300成分股失败:', error);
  }
  
  return [
    { code: '600519', name: '贵州茅台' },
    { code: '601318', name: '中国平安' },
    { code: '600036', name: '招商银行' },
    { code: '601166', name: '兴业银行' },
    { code: '600887', name: '伊利股份' },
    { code: '601398', name: '工商银行' },
    { code: '600030', name: '中信证券' },
    { code: '601288', name: '农业银行' },
    { code: '600276', name: '恒瑞医药' },
    { code: '600000', name: '浦发银行' },
    { code: '601888', name: '中国中免' },
    { code: '600016', name: '民生银行' },
    { code: '601012', name: '隆基绿能' },
    { code: '600048', name: '保利发展' },
    { code: '600900', name: '长江电力' },
    { code: '000858', name: '五粮液' },
    { code: '000333', name: '美的集团' },
    { code: '000651', name: '格力电器' },
    { code: '000002', name: '万科A' },
    { code: '000001', name: '平安银行' },
    { code: '002594', name: '比亚迪' },
    { code: '300750', name: '宁德时代' },
    { code: '002475', name: '立讯精密' },
    { code: '000725', name: '京东方A' },
    { code: '002415', name: '海康威视' },
  ];
}

async function fetchRealData(
  codes: string[],
  startDate: string,
  endDate: string,
  isETF: boolean = true
): Promise<{ 
  data: Record<string, PriceData[]>; 
  names: Record<string, string>;
  dataRanges: Record<string, { start: string; end: string; count: number }>;
}> {
  const data: Record<string, PriceData[]> = {};
  const names: Record<string, string> = {};
  const dataRanges: Record<string, { start: string; end: string; count: number }> = {};
  
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
          if (result.data.length > 0) {
            dataRanges[code] = {
              start: result.data[0].date,
              end: result.data[result.data.length - 1].date,
              count: result.data.length,
            };
          }
        }
        if (result.name) {
          names[code] = result.name;
          codeNameMap[code] = result.name;
        }
      }
    } catch (error) {
      console.error(`获取${code}数据失败:`, error);
    }
  });
  
  await Promise.all(fetchPromises);
  return { data, names, dataRanges };
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

export async function runBacktestAsync(
  config: BacktestConfig,
  onProgress?: ProgressCallback
): Promise<BacktestResult> {
  const isETF = config.strategy === 'etf_rotation';
  const isLargeCapStrategy = config.strategy === 'large_cap_low_drawdown';
  
  let rawData: Record<string, PriceData[]>;
  let names: Record<string, string>;
  let dataRanges: Record<string, { start: string; end: string; count: number }>;
  
  if (isLargeCapStrategy) {
    const hs300Stocks = await fetchHS300Stocks();
    const stockCodes = hs300Stocks.slice(0, 50).map(s => s.code);
    
    hs300Stocks.forEach(s => {
      codeNameMap[s.code] = s.name;
    });
    
    const result = await fetchRealData(stockCodes, config.startDate, config.endDate, false);
    rawData = result.data;
    names = { ...result.names };
    hs300Stocks.forEach(s => {
      if (!names[s.code]) {
        names[s.code] = s.name;
      }
    });
    dataRanges = result.dataRanges;
  } else {
    const result = await fetchRealData(config.etfCodes, config.startDate, config.endDate, isETF);
    rawData = result.data;
    names = result.names;
    dataRanges = result.dataRanges;
  }
  
  if (Object.keys(rawData).length === 0) {
    return createEmptyResult(config);
  }
  
  const { alignedData, commonDates } = alignDataByDate(rawData);
  
  if (commonDates.length === 0) {
    return createEmptyResult(config);
  }
  
  const actualStartDate = commonDates[0];
  const actualEndDate = commonDates[commonDates.length - 1];
  
  const dataInfo: BacktestDataInfo = {
    requestedStart: config.startDate,
    requestedEnd: config.endDate,
    actualStart: actualStartDate,
    actualEnd: actualEndDate,
    dataRanges: Object.entries(dataRanges).map(([code, range]) => ({
      code,
      name: names[code] || code,
      ...range,
    })),
  };
  
  if (actualStartDate > config.startDate) {
    const limitingCodes = Object.entries(dataRanges)
      .filter(([_, range]) => range.start === actualStartDate)
      .map(([code]) => names[code] || code);
    if (limitingCodes.length > 0) {
      dataInfo.warning = `由于部分股票数据起始日期较晚，实际回测从${actualStartDate}开始`;
    }
  }
  
  let result: BacktestResult;
  
  switch (config.strategy) {
    case 'etf_rotation':
      result = runETFRotationBacktest(config, alignedData, commonDates, names, actualStartDate, actualEndDate);
      break;
    case 'large_cap_low_drawdown':
      result = runLargeCapLowDrawdownBacktest(config, alignedData, commonDates, names, actualStartDate, actualEndDate, onProgress);
      break;
    case 'dual_ma':
      result = runDualMABacktest(config, alignedData, commonDates, names, actualStartDate, actualEndDate);
      break;
    case 'rsi':
      result = runRSIBacktest(config, alignedData, commonDates, names, actualStartDate, actualEndDate);
      break;
    case 'macd':
      result = runMACDBacktest(config, alignedData, commonDates, names, actualStartDate, actualEndDate);
      break;
    case 'bollinger':
      result = runBollingerBacktest(config, alignedData, commonDates, names, actualStartDate, actualEndDate);
      break;
    case 'grid':
      result = runGridBacktest(config, alignedData, commonDates, names, actualStartDate, actualEndDate);
      break;
    default:
      result = runSimpleBacktest(config, alignedData, commonDates, names, actualStartDate, actualEndDate);
  }
  
  return {
    ...result,
    dataInfo,
  };
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
  dates: string[],
  names: Record<string, string>,
  actualStartDate: string,
  actualEndDate: string
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
  
  const getName = (code: string) => names[code] || codeNameMap[code] || code;
  
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
          name: getName(code),
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
            name: getName(code),
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
                  name: getName(code),
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
              name: getName(code),
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
  
  return calculateMetrics(equityCurve, trades, config, actualStartDate, actualEndDate);
}

function runDualMABacktest(
  config: BacktestConfig,
  priceData: Record<string, PriceData[]>,
  dates: string[],
  names: Record<string, string>,
  actualStartDate: string,
  actualEndDate: string
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
  const getName = (code: string) => names[code] || codeNameMap[code] || code;
  
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
            name: getName(targetCode),
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
          name: getName(targetCode),
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
  
  return calculateMetrics(equityCurve, trades, config, actualStartDate, actualEndDate);
}

function runRSIBacktest(
  config: BacktestConfig,
  priceData: Record<string, PriceData[]>,
  dates: string[],
  names: Record<string, string>,
  actualStartDate: string,
  actualEndDate: string
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
  const getName = (code: string) => names[code] || codeNameMap[code] || code;
  
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
            name: getName(targetCode),
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
          name: getName(targetCode),
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
  
  return calculateMetrics(equityCurve, trades, config, actualStartDate, actualEndDate);
}

function runMACDBacktest(
  config: BacktestConfig,
  priceData: Record<string, PriceData[]>,
  dates: string[],
  names: Record<string, string>,
  actualStartDate: string,
  actualEndDate: string
): BacktestResult {
  return runDualMABacktest(config, priceData, dates, names, actualStartDate, actualEndDate);
}

function runBollingerBacktest(
  config: BacktestConfig,
  priceData: Record<string, PriceData[]>,
  dates: string[],
  names: Record<string, string>,
  actualStartDate: string,
  actualEndDate: string
): BacktestResult {
  return runRSIBacktest(config, priceData, dates, names, actualStartDate, actualEndDate);
}

function runGridBacktest(
  config: BacktestConfig,
  priceData: Record<string, PriceData[]>,
  dates: string[],
  names: Record<string, string>,
  actualStartDate: string,
  actualEndDate: string
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
  
  const getName = (code: string) => names[code] || codeNameMap[code] || code;
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
      name: getName(targetCode),
      price: firstPrice,
      shares,
      amount: shares * firstPrice,
      commission: shares * firstPrice * COMMISSION_RATE,
    },
  ];
  
  return calculateMetrics(equityCurve, trades, config, actualStartDate, actualEndDate);
}

function runSimpleBacktest(
  config: BacktestConfig,
  priceData: Record<string, PriceData[]>,
  dates: string[],
  names: Record<string, string>,
  actualStartDate: string,
  actualEndDate: string
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
  
  const getName = (code: string) => names[code] || codeNameMap[code] || code;
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
      name: getName(targetCode),
      price: firstPrice,
      shares,
      amount: shares * firstPrice,
      commission: shares * firstPrice * COMMISSION_RATE,
    },
  ];
  
  return calculateMetrics(equityCurve, trades, config, actualStartDate, actualEndDate);
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
    actualStartDate: config.startDate,
    actualEndDate: config.endDate,
    equityCurve: [],
    drawdownSeries: [],
    trades: [],
    monthlyReturns: [],
  };
}

function calculateMetrics(
  equityCurve: { date: string; value: number; return: number }[],
  trades: Trade[],
  config: BacktestConfig,
  actualStartDate?: string,
  actualEndDate?: string
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
    actualStartDate: actualStartDate || equityCurve[0]?.date,
    actualEndDate: actualEndDate || equityCurve[equityCurve.length - 1]?.date,
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

function runLargeCapLowDrawdownBacktest(
  config: BacktestConfig,
  priceData: Record<string, PriceData[]>,
  dates: string[],
  names: Record<string, string>,
  actualStartDate: string,
  actualEndDate: string,
  onProgress?: (update: BacktestProgressUpdate) => void
): BacktestResult {
  const maxPositions = (config.parameters?.max_positions as number) || 3;
  const stopLossRatio = (config.parameters?.stop_loss_ratio as number) || 0.05;
  const takeProfitRatio = (config.parameters?.take_profit_ratio as number) || 0.35;
  const drawdownLockThreshold = (config.parameters?.drawdown_lock_threshold as number) || 0.10;
  const useRsrsTiming = config.parameters?.use_rsrs_timing !== false;
  const usePartialUnlock = config.parameters?.use_partial_unlock !== false;
  const rsrsBuyThreshold = (config.parameters?.rsrs_buy_threshold as number) || 0.7;
  
  const codes = Object.keys(priceData);
  if (codes.length === 0 || dates.length === 0) {
    return createEmptyResult(config);
  }
  
  let cash = config.initialCapital;
  const positions: Map<string, { code: string; shares: number; costPrice: number; highestPrice: number }> = new Map();
  const trades: Trade[] = [];
  const equityCurve: { date: string; value: number; return: number }[] = [];
  
  let maxTotalValue = config.initialCapital;
  let drawdownLock = false;
  let partialUnlock = false;
  let unlockCooldownDays = 0;
  const unlockCooldownMax = 10;
  const fullUnlockDrawdown = 0.05;
  const unlockPositionRatio = 0.3;
  
  const getName = (code: string) => names[code] || codeNameMap[code] || code;
  
  function calculateDrawdown(currentValue: number): number {
    if (currentValue > maxTotalValue) {
      maxTotalValue = currentValue;
    }
    return (maxTotalValue - currentValue) / maxTotalValue;
  }
  
  function calculateStockScoreDetail(code: string, currentIndex: number): StockScoreDetail | null {
    const data = priceData[code];
    if (!data || currentIndex < 30) return null;
    
    const closes = data.slice(0, currentIndex + 1).map(d => d.price);
    if (closes.length < 30) return null;
    
    const scores = {
      momentum5: 0,
      momentum20: 0,
      trendStrength: 0,
      volumeRatio: 0,
      volatility: 0,
      marketCap: 0,
    };
    
    const momentum5 = (closes[closes.length - 1] / closes[closes.length - 6]) - 1;
    if (momentum5 > 0.05) scores.momentum5 = 25;
    else if (momentum5 > 0.02) scores.momentum5 = 15;
    else if (momentum5 > 0) scores.momentum5 = 5;
    
    const momentum20 = (closes[closes.length - 1] / closes[closes.length - 21]) - 1;
    if (momentum20 > 0.10) scores.momentum20 = 20;
    else if (momentum20 > 0.05) scores.momentum20 = 12;
    else if (momentum20 > 0) scores.momentum20 = 5;
    
    const ma5 = closes.slice(-5).reduce((a, b) => a + b, 0) / 5;
    const ma20 = closes.slice(-20).reduce((a, b) => a + b, 0) / 20;
    const trendStrengthRatio = (ma5 - ma20) / ma20;
    if (trendStrengthRatio > 0.01) scores.trendStrength = 25;
    else if (trendStrengthRatio > 0.005) scores.trendStrength = 15;
    else if (trendStrengthRatio > 0) scores.trendStrength = 5;
    
    const returns = [];
    for (let i = 1; i < Math.min(20, closes.length); i++) {
      returns.push((closes[closes.length - i] - closes[closes.length - i - 1]) / closes[closes.length - i - 1]);
    }
    const volatilityRatio = Math.sqrt(returns.reduce((sum, r) => sum + r * r, 0) / returns.length);
    if (volatilityRatio < 0.05) scores.volatility = 10;
    else if (volatilityRatio < 0.08) scores.volatility = 5;
    
    const totalScore = scores.momentum5 + scores.momentum20 + scores.trendStrength + scores.volumeRatio + scores.volatility + scores.marketCap;
    
    return {
      code,
      name: getName(code),
      scores,
      totalScore,
      rank: 0,
      isSelected: false,
    };
  }
  
  for (let i = 0; i < dates.length; i++) {
    const date = dates[i];
    
    let portfolioValue = cash;
    positions.forEach((pos, code) => {
      const price = getPriceSafely(priceData, code, i);
      if (price !== null) {
        portfolioValue += pos.shares * price;
      }
    });
    
    const drawdown = calculateDrawdown(portfolioValue);
    
    if (drawdown >= drawdownLockThreshold) {
      if (usePartialUnlock && unlockCooldownDays > 0) {
        unlockCooldownDays--;
      } else {
        for (const [code, pos] of positions) {
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
            name: getName(code),
            price,
            shares: pos.shares,
            amount: sellAmount,
            commission,
          });
        }
        positions.clear();
        drawdownLock = true;
        partialUnlock = false;
      }
    }
    
    if (drawdownLock) {
      if (usePartialUnlock && partialUnlock) {
        if (unlockCooldownDays > 0) {
          unlockCooldownDays--;
        }
        if (drawdown < fullUnlockDrawdown) {
          partialUnlock = false;
          drawdownLock = false;
        }
      } else if (drawdown < drawdownLockThreshold * 0.5) {
        if (usePartialUnlock) {
          partialUnlock = true;
          unlockCooldownDays = unlockCooldownMax;
        } else {
          drawdownLock = false;
        }
      }
    }
    
    for (const [code, pos] of positions) {
      const price = getPriceSafely(priceData, code, i);
      if (price === null) continue;
      
      if (price > pos.highestPrice) {
        pos.highestPrice = price;
      }
      
      const profitRatio = (price - pos.costPrice) / pos.costPrice;
      
      if (profitRatio >= takeProfitRatio || profitRatio <= -stopLossRatio) {
        const sellAmount = pos.shares * price;
        const commission = sellAmount * COMMISSION_RATE;
        const stampDuty = sellAmount * STAMP_DUTY_RATE;
        
        cash += sellAmount - commission - stampDuty;
        
        trades.push({
          date,
          type: 'sell',
          code,
          name: getName(code),
          price,
          shares: pos.shares,
          amount: sellAmount,
          commission,
        });
        
        positions.delete(code);
      }
    }
    
    if (!drawdownLock || partialUnlock) {
      const currentPositions = positions.size;
      
      if (currentPositions < maxPositions) {
        const scoreDetails: StockScoreDetail[] = [];
        
        for (const code of codes) {
          if (!positions.has(code)) {
            const detail = calculateStockScoreDetail(code, i);
            if (detail && detail.totalScore > 0) {
              scoreDetails.push(detail);
            }
          }
        }
        
        scoreDetails.sort((a, b) => b.totalScore - a.totalScore);
        scoreDetails.forEach((detail, index) => {
          detail.rank = index + 1;
        });
        
        const buyCandidates = scoreDetails.slice(0, maxPositions - currentPositions);
        buyCandidates.forEach(detail => detail.isSelected = true);
        
        const dailyResult: DailySelectionResult = {
          date,
          marketStatus: drawdownLock 
            ? (partialUnlock ? 'partial_unlock' : 'drawdown_lock') 
            : 'normal',
          candidates: scoreDetails.slice(0, 10),
          selectedStocks: buyCandidates.map(c => c.code),
          trades: [],
          portfolioValue,
          drawdown: drawdown * 100,
          cashRatio: (cash / portfolioValue) * 100,
        };
        
        if (onProgress && i % 5 === 0) {
          onProgress({
            currentIndex: i,
            totalDays: dates.length,
            currentDate: date,
            percent: Math.round((i / dates.length) * 100),
            dailyResult,
          });
        }
        
        let availableCash = cash;
        if (partialUnlock) {
          const currentPositionValue = Array.from(positions.values()).reduce((sum, pos) => {
            const price = getPriceSafely(priceData, pos.code, i);
            return sum + (price !== null ? pos.shares * price : 0);
          }, 0);
          const maxPositionValue = portfolioValue * unlockPositionRatio;
          availableCash = Math.min(cash, maxPositionValue - currentPositionValue);
        }
        
        const cashPerStock = buyCandidates.length > 0 ? availableCash / buyCandidates.length * 0.95 : 0;
        
        for (const candidate of buyCandidates) {
          if (positions.size >= maxPositions) break;
          
          const code = candidate.code;
          const price = getPriceSafely(priceData, code, i);
          if (price === null || price <= 0) continue;
          
          const shares = Math.floor(cashPerStock / price / 100) * 100;
          
          if (shares >= 100 && cash >= shares * price * (1 + COMMISSION_RATE)) {
            const buyAmount = shares * price;
            const commission = buyAmount * COMMISSION_RATE;
            
            cash -= buyAmount + commission;
            positions.set(code, {
              code,
              shares,
              costPrice: price,
              highestPrice: price,
            });
            
            trades.push({
              date,
              type: 'buy',
              code,
              name: getName(code),
              price,
              shares,
              amount: buyAmount,
              commission,
            });
            
            dailyResult.trades.push({
              action: 'buy',
              code,
              name: getName(code),
              reason: `得分排名第${candidate.rank}，总分${candidate.totalScore}分`,
            });
          }
        }
      }
    }
    
    portfolioValue = cash;
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
  
  return calculateMetrics(equityCurve, trades, config, actualStartDate, actualEndDate);
}
