import { useMemo, useState } from 'react';
import { usePersistentState } from './usePersistentState';
import { apiClient } from '../utils/apiClient';
import { adaptBacktestResult } from '../utils/backtestApiAdapter';
import type { BacktestResult } from '../utils/backtestEngine';
import { etfPool, strategies, type StrategyType } from '../utils/strategyConfig';
import {
  createDefaultStrategyParams,
  getDefaultSelectedEtfCodes,
  normalizeStrategyParams,
  strategiesNeedCustomEtfPool,
} from '../utils/backtestDomain';

export interface ComparePageParams {
  startDate: string;
  endDate: string;
  initialCapital: number;
}

export interface ComparisonDataPoint {
  name: string;
  总收益率: number;
  年化收益: number;
  最大回撤: number;
  夏普比率: number;
}

const DEFAULT_COMPARE_PARAMS: ComparePageParams = {
  startDate: '2021-01-01',
  endDate: '2024-01-01',
  initialCapital: 100000,
};

const DEFAULT_SELECTED_ETFS = getDefaultSelectedEtfCodes(etfPool);

function compareByReturn(a: ComparisonDataPoint, b: ComparisonDataPoint): number {
  return a.总收益率 - b.总收益率;
}

function compareBySharpe(a: ComparisonDataPoint, b: ComparisonDataPoint): number {
  return a.夏普比率 - b.夏普比率;
}

function compareByDrawdownAsc(a: ComparisonDataPoint, b: ComparisonDataPoint): number {
  return b.最大回撤 - a.最大回撤;
}

export function useComparePage() {
  const [selectedStrategies, setSelectedStrategies] = usePersistentState<StrategyType[]>(
    'compare_strategies',
    ['etf_rotation']
  );
  const [selectedETFs, setSelectedETFs] = usePersistentState<string[]>(
    'compare_etfs',
    DEFAULT_SELECTED_ETFS
  );
  const [params, setParams] = usePersistentState<ComparePageParams>('compare_params', DEFAULT_COMPARE_PARAMS);
  const [results, setResults] = useState<Map<StrategyType, BacktestResult>>(new Map());
  const [isRunning, setIsRunning] = useState(false);
  const needsCustomEtfPool = useMemo(
    () => strategiesNeedCustomEtfPool(selectedStrategies),
    [selectedStrategies]
  );

  const toggleStrategy = (strategyId: StrategyType) => {
    setSelectedStrategies((prev) => {
      if (prev.includes(strategyId)) {
        return prev.filter((item) => item !== strategyId);
      }
      if (prev.length >= 3) {
        return prev;
      }
      return [...prev, strategyId];
    });
  };

  const runCompare = async () => {
    setIsRunning(true);
    try {
      if (selectedStrategies.length < 2) {
        throw new Error('策略对比至少需要选择 2 个策略');
      }
      if (needsCustomEtfPool && selectedETFs.length === 0) {
        throw new Error('包含 ETF轮动策略时，请至少选择一只ETF');
      }

      const strategyParamsList = selectedStrategies.map((strategyId) =>
        normalizeStrategyParams(createDefaultStrategyParams(strategyId))
      );

      const compareResult = await apiClient.compareBacktest({
        strategies: selectedStrategies,
        strategy_params_list: strategyParamsList,
        backtest_params: {
          start_date: params.startDate,
          end_date: params.endDate,
          initial_capital: params.initialCapital,
          commission_rate: 0.0003,
          stamp_duty: 0.001,
          slippage: 0.001,
        },
        etf_codes: needsCustomEtfPool ? selectedETFs : [],
      });

      const newResults = new Map<StrategyType, BacktestResult>();
      compareResult.results.forEach((result) => {
        newResults.set(result.strategy as StrategyType, adaptBacktestResult(result));
      });
      setResults(newResults);
    } catch (error) {
      console.error('策略对比失败:', error);
      setResults(new Map());
    } finally {
      setIsRunning(false);
    }
  };

  const clearResults = () => {
    setResults(new Map());
  };

  const comparisonData = useMemo<ComparisonDataPoint[]>(() => {
    return selectedStrategies.map((strategyId) => {
      const strategy = strategies.find((item) => item.id === strategyId)!;
      const result = results.get(strategyId);
      return {
        name: strategy.name,
        总收益率: result?.totalReturn || 0,
        年化收益: result?.annualReturn || 0,
        最大回撤: result?.maxDrawdown || 0,
        夏普比率: result?.sharpeRatio || 0,
      };
    });
  }, [selectedStrategies, results]);

  const equityData = useMemo(() => {
    if (results.size === 0) {
      return [];
    }
    const firstResult = Array.from(results.values())[0];
    return firstResult.equityCurve
      .map((point, index) => {
        const dataPoint: Record<string, string | number> = { date: point.date };
        selectedStrategies.forEach((strategyId) => {
          const strategy = strategies.find((item) => item.id === strategyId)!;
          const result = results.get(strategyId);
          dataPoint[strategy.name] = result ? result.equityCurve[index]?.value || 0 : 0;
        });
        return dataPoint;
      })
      .filter((_, index) => index % 5 === 0);
  }, [results, selectedStrategies]);

  const bestReturn = useMemo(
    () =>
      comparisonData.length > 0
        ? comparisonData.reduce((best, current) => (compareByReturn(current, best) > 0 ? current : best))
        : null,
    [comparisonData]
  );

  const bestSharpe = useMemo(
    () =>
      comparisonData.length > 0
        ? comparisonData.reduce((best, current) => (compareBySharpe(current, best) > 0 ? current : best))
        : null,
    [comparisonData]
  );

  const minDrawdown = useMemo(
    () =>
      comparisonData.length > 0
        ? comparisonData.reduce((best, current) => (compareByDrawdownAsc(current, best) > 0 ? current : best))
        : null,
    [comparisonData]
  );

  return {
    selectedStrategies,
    selectedETFs,
    needsCustomEtfPool,
    params,
    results,
    isRunning,
    comparisonData,
    equityData,
    bestReturn,
    bestSharpe,
    minDrawdown,
    setSelectedETFs,
    setParams,
    toggleStrategy,
    runCompare,
    clearResults,
  };
}
