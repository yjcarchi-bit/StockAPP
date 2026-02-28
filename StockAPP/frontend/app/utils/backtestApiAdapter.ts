import type { BacktestResult, DrawdownPoint, EquityPoint } from './backtestEngine';
import type { ApiBacktestResult } from './apiClient';

function buildDrawdownSeries(equityCurve: EquityPoint[]): DrawdownPoint[] {
  let peak = 0;
  return equityCurve.map((point) => {
    peak = Math.max(peak, point.value);
    const drawdown = peak > 0 ? ((peak - point.value) / peak) * 100 : 0;
    return {
      date: point.date,
      drawdown,
    };
  });
}

export function adaptBacktestResult(apiResult: ApiBacktestResult): BacktestResult {
  const equityCurve: EquityPoint[] = apiResult.equity_curve.map((p) => ({
    date: p.date,
    value: p.value,
  }));

  const drawdownSeries = buildDrawdownSeries(equityCurve);
  const actualStartDate = equityCurve[0]?.date;
  const actualEndDate = equityCurve[equityCurve.length - 1]?.date;

  return {
    totalReturn: apiResult.metrics.total_return ?? 0,
    annualReturn: apiResult.metrics.annual_return ?? 0,
    maxDrawdown: Math.abs(apiResult.metrics.max_drawdown ?? 0),
    sharpeRatio: apiResult.metrics.sharpe_ratio ?? 0,
    sortinoRatio: apiResult.metrics.sortino_ratio ?? 0,
    calmarRatio: apiResult.metrics.calmar_ratio ?? 0,
    winRate: apiResult.metrics.win_rate ?? 0,
    profitFactor: apiResult.metrics.profit_factor ?? 0,
    totalTrades: apiResult.metrics.total_trades ?? 0,
    finalAsset: apiResult.metrics.final_value ?? 0,
    actualStartDate,
    actualEndDate,
    equityCurve,
    drawdownSeries,
    trades: apiResult.trades.map((trade) => ({
      date: trade.timestamp,
      type: trade.side,
      code: trade.code,
      name: trade.code,
      price: trade.price,
      shares: trade.amount,
      amount: trade.value,
      commission: 0,
    })),
    monthlyReturns: apiResult.monthly_returns.map((item) => ({
      year: item.year,
      month: item.month,
      return: item.return_rate,
    })),
    dailyPositions: apiResult.daily_positions.map((day) => ({
      date: day.date,
      positions: day.positions.map((pos) => ({
        code: pos.code,
        name: pos.name,
        shares: pos.shares,
        price: pos.price,
        marketValue: pos.market_value,
        profit: pos.profit,
        dailyProfit: pos.daily_profit,
        profitPct: pos.profit_pct,
      })),
      cash: day.cash,
      totalValue: day.total_value,
      totalProfit: day.total_profit,
      totalDailyProfit: day.total_daily_profit,
    })),
    excessReturn: apiResult.metrics.total_return - (apiResult.metrics.benchmark_return ?? 0),
  };
}
