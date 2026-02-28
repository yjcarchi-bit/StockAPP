export const API_BASE = import.meta.env.VITE_API_BASE || '/api';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
  });

  if (!response.ok) {
    let detail = `请求失败(${response.status})`;
    try {
      const data = await response.json();
      detail = data?.detail || data?.message || detail;
    } catch {
      // noop
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export interface ApiBacktestParams {
  start_date: string;
  end_date: string;
  initial_capital: number;
  commission_rate?: number;
  stamp_duty?: number;
  slippage?: number;
}

export interface ApiBacktestRunRequest {
  strategy: string;
  strategy_params: Record<string, unknown>;
  backtest_params: ApiBacktestParams;
  etf_codes: string[];
}

export interface ApiBacktestResult {
  result_id: string;
  strategy: string;
  metrics: {
    total_return: number;
    annual_return: number;
    max_drawdown: number;
    sharpe_ratio: number;
    sortino_ratio: number;
    calmar_ratio: number;
    win_rate: number;
    profit_factor: number;
    total_trades: number;
    final_value: number;
    benchmark_return: number;
  };
  equity_curve: Array<{ date: string; value: number }>;
  trades: Array<{
    timestamp: string;
    code: string;
    side: 'buy' | 'sell';
    price: number;
    amount: number;
    value: number;
  }>;
  monthly_returns: Array<{ year: number; month: number; return_rate: number }>;
  daily_positions: Array<{
    date: string;
    positions: Array<{
      code: string;
      name: string;
      shares: number;
      price: number;
      market_value: number;
      profit: number;
      daily_profit: number;
      profit_pct: number;
    }>;
    cash: number;
    total_value: number;
    total_profit: number;
    total_daily_profit: number;
  }>;
}

export interface ApiCompareRequest {
  strategies: string[];
  strategy_params_list: Array<Record<string, unknown>>;
  backtest_params: ApiBacktestParams;
  etf_codes: string[];
}

export interface ApiCompareResult {
  results: ApiBacktestResult[];
  best_return_strategy: string;
  best_sharpe_strategy: string;
  min_drawdown_strategy: string;
}

export interface ApiOptimizeRequest {
  strategy: string;
  param_grid: Record<string, unknown[]>;
  fixed_params: Record<string, unknown>;
  backtest_params: ApiBacktestParams;
  etf_codes: string[];
  optimization_metric: string;
  method: 'grid' | 'random';
  n_iter: number;
}

export interface ApiOptimizationResult {
  best_params: Record<string, unknown>;
  best_metrics: ApiBacktestResult['metrics'];
  all_results: Array<Record<string, unknown>>;
  optimization_time: number;
  total_combinations: number;
}

export interface ApiUpdateStatus {
  running: boolean;
  update_time: string;
  last_update: string | null;
  etf_codes_count: number;
  stock_codes_count: number;
}

export interface ApiResponse {
  success: boolean;
  message: string;
  data?: unknown;
}

export interface CacheInfo {
  cache_dir: string;
  file_count: number;
  total_size_mb: number;
  expire_hours?: number;
}

export interface ETFDataResponse {
  code: string;
  name: string;
  data: Array<{
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
}

export interface StockSearchItem {
  code: string;
  name: string;
  market?: string;
  industry?: string;
}

export const apiClient = {
  runBacktest(payload: ApiBacktestRunRequest) {
    return request<ApiBacktestResult>('/backtest/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  compareBacktest(payload: ApiCompareRequest) {
    return request<ApiCompareResult>('/backtest/compare', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  optimizeBacktest(payload: ApiOptimizeRequest) {
    return request<ApiOptimizationResult>('/backtest/optimize', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getHS300Stocks() {
    return request<StockSearchItem[]>('/data/hs300/stocks');
  },

  searchStocks(keyword: string, limit = 20) {
    return request<StockSearchItem[]>(
      `/data/stock/search?keyword=${encodeURIComponent(keyword)}&limit=${limit}`
    );
  },

  getCacheInfo() {
    return request<CacheInfo>('/data-update/cache/info');
  },

  triggerUpdate() {
    return request<ApiResponse>('/data-update/trigger', {
      method: 'POST',
    });
  },

  getUpdateStatus() {
    return request<ApiUpdateStatus>('/data-update/status');
  },

  getETFData(code: string, startDate: string, endDate: string) {
    return request<ETFDataResponse>(
      `/data/etf/${code}?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`
    );
  },
};
