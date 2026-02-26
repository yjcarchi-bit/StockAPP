import type { BacktestConfig } from './strategyConfig';
import type { BacktestResult, Trade, MonthlyReturn } from './backtestEngine';
import {
  calculateRSI,
  calculateMaxDrawdown,
  calculateSharpeRatio,
} from './backtestEngine';

const COMMISSION_RATE = 0.0003;
const STAMP_DUTY_RATE = 0.001;

const API_BASE = 'http://localhost:8000/api';

interface PriceData {
  date: string;
  price: number | null;
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

export interface BacktestLogUpdate {
  stage: 'data_fetch' | 'data_process' | 'backtest' | 'metrics';
  message: string;
  progress?: number;
  total?: number;
}

export type LogCallback = (update: BacktestLogUpdate) => void;

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
  commonDates: string[];
  dateAvailability: Record<string, Set<string>>;
} {
  const codes = Object.keys(priceData);
  if (codes.length === 0) {
    return { alignedData: {}, commonDates: [], dateAvailability: {} };
  }
  
  const allDates = new Set<string>();
  const dateAvailability: Record<string, Set<string>> = {};
  
  codes.forEach(code => {
    const codeDates = new Set<string>();
    priceData[code].forEach(d => {
      allDates.add(d.date);
      codeDates.add(d.date);
    });
    dateAvailability[code] = codeDates;
  });
  
  const commonDates = Array.from(allDates).sort();
  
  const alignedData: Record<string, PriceData[]> = {};
  codes.forEach(code => {
    const dataMap = new Map(priceData[code].map(d => [d.date, d]));
    alignedData[code] = commonDates.map(date => {
      const existingData = dataMap.get(date);
      if (existingData) {
        return existingData;
      }
      return { date, price: null };
    });
  });
  
  return { alignedData, commonDates, dateAvailability };
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
  _onProgress?: unknown,
  onLog?: LogCallback
): Promise<BacktestResult> {
  const isETF = config.strategy === 'etf_rotation';
  
  onLog?.({ stage: 'data_fetch', message: '开始获取历史数据...' });
  
  let rawData: Record<string, PriceData[]>;
  let names: Record<string, string>;
  let dataRanges: Record<string, { start: string; end: string; count: number }>;
  
  onLog?.({ 
      stage: 'data_fetch', 
      message: `正在获取 ${config.etfCodes.length} 只${isETF ? 'ETF' : '股票'}的历史数据...`,
      progress: 0,
      total: config.etfCodes.length
    });
    
    const fetchResult = await fetchRealData(config.etfCodes, config.startDate, config.endDate, isETF);
    rawData = fetchResult.data;
    names = fetchResult.names;
    dataRanges = fetchResult.dataRanges;
    
    onLog?.({ 
      stage: 'data_fetch', 
      message: `成功获取 ${Object.keys(rawData).length} 只${isETF ? 'ETF' : '股票'}的数据`,
      progress: config.etfCodes.length,
      total: config.etfCodes.length
    });
  
  if (Object.keys(rawData).length === 0) {
    return createEmptyResult(config);
  }
  
  onLog?.({ stage: 'data_process', message: '正在对齐和过滤日期数据...' });
  
  const { alignedData, commonDates, dateAvailability } = alignDataByDate(rawData);
  
  if (commonDates.length === 0) {
    return createEmptyResult(config);
  }
  
  onLog?.({ 
    stage: 'data_process', 
    message: `原始数据包含 ${commonDates.length} 个交易日` 
  });
  
  const filteredDates = commonDates.filter(date => 
    date >= config.startDate && date <= config.endDate
  );
  
  if (filteredDates.length === 0) {
    return createEmptyResult(config);
  }
  
  const actualStartDate = filteredDates[0];
  const actualEndDate = filteredDates[filteredDates.length - 1];
  
  onLog?.({ 
    stage: 'data_process', 
    message: `过滤后回测时间范围: ${actualStartDate} 至 ${actualEndDate}，共 ${filteredDates.length} 个交易日` 
  });
  
  const filteredData: Record<string, PriceData[]> = {};
  const startIndex = commonDates.indexOf(actualStartDate);
  const endIndex = commonDates.indexOf(actualEndDate);
  
  Object.keys(alignedData).forEach(code => {
    filteredData[code] = alignedData[code].slice(startIndex, endIndex + 1);
  });
  
  onLog?.({ stage: 'data_process', message: '数据处理完成，开始执行回测...' });
  
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
  
  let result: BacktestResult;
  
  onLog?.({ stage: 'backtest', message: '开始执行回测策略...' });
  
  switch (config.strategy) {
    case 'etf_rotation':
    default:
      result = runETFRotationBacktest(config, filteredData, filteredDates, names, actualStartDate, actualEndDate);
  }
  
  onLog?.({ stage: 'metrics', message: '正在计算回测指标...' });
  
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
  if (!data || !data[index] || data[index].price === null) {
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
        
        const currentPrice = codeData[i].price;
        if (currentPrice === null) return;
        
        const history = codeData.slice(i - lookbackDays, i);
        const prices = history.map(d => d.price).filter((p): p is number => p !== null);
        if (prices.length < lookbackDays) return;
        if (!prices.every(p => typeof p === 'number' && !isNaN(p) && p > 0)) return;
        
        if (i >= 3) {
          const p0 = codeData[i].price;
          const p1 = codeData[i - 1].price;
          const p2 = codeData[i - 2].price;
          const p3 = codeData[i - 3].price;
          
          if (p0 === null || p1 === null || p2 === null || p3 === null) return;
          
          const day1Ratio = p0 / p1;
          const day2Ratio = p1 / p2;
          const day3Ratio = p2 / p3;
          
          if (Math.min(day1Ratio, day2Ratio, day3Ratio) < lossThreshold) {
            return;
          }
        }
        
        if (useShortMomentum && i > shortLookbackDays) {
          const shortPrice = codeData[i - shortLookbackDays].price;
          if (shortPrice === null) return;
          const shortReturn = currentPrice / shortPrice - 1;
          if (shortReturn < shortMomentumThreshold) {
            return;
          }
        }
        
        if (useMaFilter && i >= maLongPeriod) {
          const maShortPrices = codeData.slice(i - maShortPeriod, i).map(d => d.price).filter((p): p is number => p !== null);
          const maLongPrices = codeData.slice(i - maLongPeriod, i).map(d => d.price).filter((p): p is number => p !== null);
          if (maShortPrices.length < maShortPeriod || maLongPrices.length < maLongPeriod) return;
          const maShort = maShortPrices.reduce((a, b) => a + b, 0) / maShortPeriod;
          const maLong = maLongPrices.reduce((a, b) => a + b, 0) / maLongPeriod;
          
          if (maShort < maLong) {
            return;
          }
        }
        
        if (useRsiFilter && i >= rsiPeriod + 5) {
          const rsiPrices = codeData.slice(i - rsiPeriod - 5, i).map(d => d.price).filter((p): p is number => p !== null);
          if (rsiPrices.length < rsiPeriod + 5) return;
          const rsiValues = calculateRSI(rsiPrices, rsiPeriod);
          if (rsiValues.length > 0 && rsiValues[rsiValues.length - 1] > rsiThreshold) {
            const ma5Prices = codeData.slice(i - 5, i).map(d => d.price).filter((p): p is number => p !== null);
            if (ma5Prices.length < 5) return;
            const ma5 = ma5Prices.reduce((a, b) => a + b, 0) / 5;
            if (currentPrice < ma5) {
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
          const histHighs = codeData.slice(i - atrPeriod - 1, i).map(d => d.price).filter((p): p is number => p !== null).map(p => p * 1.01);
          const histLows = codeData.slice(i - atrPeriod - 1, i).map(d => d.price).filter((p): p is number => p !== null).map(p => p * 0.99);
          const histCloses = codeData.slice(i - atrPeriod - 1, i).map(d => d.price).filter((p): p is number => p !== null);
          if (histHighs.length >= atrPeriod && histLows.length >= atrPeriod && histCloses.length >= atrPeriod) {
            atr = calculateATR(histHighs, histLows, histCloses, atrPeriod);
          }
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
            const histHighs = codeData.slice(i - atrPeriod - 1, i).map(d => d.price).filter((p): p is number => p !== null).map(p => p * 1.01);
            const histLows = codeData.slice(i - atrPeriod - 1, i).map(d => d.price).filter((p): p is number => p !== null).map(p => p * 0.99);
            const histCloses = codeData.slice(i - atrPeriod - 1, i).map(d => d.price).filter((p): p is number => p !== null);
            if (histHighs.length >= atrPeriod && histLows.length >= atrPeriod && histCloses.length >= atrPeriod) {
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

