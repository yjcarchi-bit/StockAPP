import { useMemo, useState } from 'react';
import { usePersistentState } from './usePersistentState';
import { apiClient } from '../utils/apiClient';
import {
  getStrategyByIdOrFirst,
  normalizeStrategyParams,
  strategyNeedsCustomEtfPool,
} from '../utils/backtestDomain';
import { type Strategy, type StrategyType } from '../utils/strategyConfig';

const METRIC_KEYS = new Set([
  'total_return',
  'annual_return',
  'max_drawdown',
  'sharpe_ratio',
  'sortino_ratio',
  'calmar_ratio',
  'win_rate',
  'profit_factor',
  'total_trades',
  'final_value',
  'benchmark_return',
]);

export interface OptimizationResult {
  params: Record<string, unknown>;
  totalReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
}

export interface OptimizationDateRange {
  startDate: string;
  endDate: string;
}

export interface ParamGridInfo {
  grids: Record<string, unknown[]>;
  fixedParams: Record<string, unknown>;
  totalCombinations: number;
}

const DEFAULT_OPTIMIZATION_PARAMS: OptimizationDateRange = {
  startDate: '2021-01-01',
  endDate: '2024-01-01',
};

function buildParamGrid(strategy: Strategy): ParamGridInfo {
  const grids: Record<string, unknown[]> = {};
  const fixedParams: Record<string, unknown> = {};
  let totalCombinations = 1;

  strategy.parameters.forEach((param) => {
    if (
      param.type === 'slider' &&
      param.min !== undefined &&
      param.max !== undefined &&
      param.step !== undefined
    ) {
      const values: number[] = [];
      for (let value = param.min; value <= param.max; value += param.step * 2) {
        values.push(value);
      }
      grids[param.key] = values;
      totalCombinations *= values.length;
      return;
    }

    if (param.type === 'select' && param.options) {
      const values = param.options.map((option) => option.value);
      grids[param.key] = values;
      totalCombinations *= values.length;
      return;
    }

    fixedParams[param.key] = param.default;
  });

  return { grids, fixedParams, totalCombinations };
}

function toOptimizationResultRow(row: Record<string, unknown>): OptimizationResult {
  const params: Record<string, unknown> = {};
  Object.entries(row).forEach(([key, value]) => {
    if (!METRIC_KEYS.has(key)) {
      params[key] = value;
    }
  });

  return {
    params,
    totalReturn: Number(row.total_return ?? 0),
    sharpeRatio: Number(row.sharpe_ratio ?? 0),
    maxDrawdown: Math.abs(Number(row.max_drawdown ?? 0)),
  };
}

export function useOptimizationPage() {
  const [selectedStrategy, setSelectedStrategy] = usePersistentState<StrategyType>(
    'optimization_strategy',
    'etf_rotation'
  );
  const [selectedETF, setSelectedETF] = usePersistentState('optimization_etf', '510300');
  const [dateRange, setDateRange] = usePersistentState<OptimizationDateRange>(
    'optimization_date_range',
    DEFAULT_OPTIMIZATION_PARAMS
  );
  const [initialCapital, setInitialCapital] = usePersistentState('optimization_capital', 100000);
  const [optimizationMethod, setOptimizationMethod] = usePersistentState<'grid' | 'random'>(
    'optimization_method',
    'grid'
  );
  const [optimizationTarget, setOptimizationTarget] = usePersistentState<'sharpe' | 'return'>(
    'optimization_target',
    'sharpe'
  );
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<OptimizationResult[]>([]);
  const [bestResult, setBestResult] = useState<OptimizationResult | null>(null);

  const currentStrategy = useMemo(
    () => getStrategyByIdOrFirst(selectedStrategy),
    [selectedStrategy]
  );
  const needsCustomEtfPool = useMemo(
    () => strategyNeedsCustomEtfPool(selectedStrategy),
    [selectedStrategy]
  );

  const paramGridInfo = useMemo(() => buildParamGrid(currentStrategy), [currentStrategy]);

  const optimize = async () => {
    setIsOptimizing(true);
    setProgress(0);

    try {
      setProgress(30);

      const optimizeResult = await apiClient.optimizeBacktest({
        strategy: selectedStrategy,
        param_grid: normalizeStrategyParams(paramGridInfo.grids),
        fixed_params: normalizeStrategyParams(paramGridInfo.fixedParams),
        backtest_params: {
          start_date: dateRange.startDate,
          end_date: dateRange.endDate,
          initial_capital: initialCapital,
          commission_rate: 0.0003,
          stamp_duty: 0.001,
          slippage: 0.001,
        },
        etf_codes: needsCustomEtfPool ? [selectedETF] : [],
        optimization_metric: optimizationTarget === 'sharpe' ? 'sharpe_ratio' : 'total_return',
        method: optimizationMethod,
        n_iter: 20,
      });

      setProgress(80);

      const allResults = optimizeResult.all_results.map((row) =>
        toOptimizationResultRow(row as Record<string, unknown>)
      );

      const sortedResults = [...allResults].sort((a, b) => {
        if (optimizationTarget === 'sharpe') {
          return b.sharpeRatio - a.sharpeRatio;
        }
        return b.totalReturn - a.totalReturn;
      });

      setResults(sortedResults);
      setBestResult({
        params: optimizeResult.best_params,
        totalReturn: optimizeResult.best_metrics.total_return,
        sharpeRatio: optimizeResult.best_metrics.sharpe_ratio,
        maxDrawdown: Math.abs(optimizeResult.best_metrics.max_drawdown),
      });
      setProgress(100);
    } catch (error) {
      console.error('参数优化失败:', error);
      setResults([]);
      setBestResult(null);
    } finally {
      setIsOptimizing(false);
    }
  };

  return {
    selectedStrategy,
    selectedETF,
    needsCustomEtfPool,
    dateRange,
    initialCapital,
    optimizationMethod,
    optimizationTarget,
    isOptimizing,
    progress,
    results,
    bestResult,
    currentStrategy,
    totalCombinations: paramGridInfo.totalCombinations,
    setSelectedStrategy,
    setSelectedETF,
    setDateRange,
    setInitialCapital,
    setOptimizationMethod,
    setOptimizationTarget,
    optimize,
  };
}
