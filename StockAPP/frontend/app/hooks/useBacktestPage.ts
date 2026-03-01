import { useMemo, useState } from 'react';
import { usePersistentState } from './usePersistentState';
import { apiClient } from '../utils/apiClient';
import { adaptBacktestResult } from '../utils/backtestApiAdapter';
import type { BacktestResult } from '../utils/backtestEngine';
import {
  createDefaultStrategyParams,
  getDefaultSelectedEtfCodes,
  getStrategyByIdOrFirst,
  getTodayDateString,
  normalizeStrategyParams,
  strategyNeedsCustomEtfPool,
  type BacktestPageParams,
  type StrategyParamsRecord,
} from '../utils/backtestDomain';
import { defaultBacktestConfig, etfPool, type StrategyType } from '../utils/strategyConfig';

export type BacktestLogLevel = 'info' | 'warning' | 'error' | 'success';

export interface LogEntry {
  time: string;
  level: BacktestLogLevel;
  message: string;
}

const DEFAULT_SELECTED_ETFS = getDefaultSelectedEtfCodes(etfPool);

const DEFAULT_BACKTEST_PARAMS: BacktestPageParams = {
  startDate: '2015-01-01',
  endDate: getTodayDateString(),
  initialCapital: 100000,
  benchmark: '510300',
};

function formatUnknownError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

export function getLogColor(level: BacktestLogLevel): string {
  switch (level) {
    case 'info':
      return 'text-blue-600 dark:text-blue-400';
    case 'warning':
      return 'text-yellow-600 dark:text-yellow-400';
    case 'error':
      return 'text-red-600 dark:text-red-400';
    case 'success':
      return 'text-green-600 dark:text-green-400';
    default:
      return 'text-foreground';
  }
}

export function getLogPrefix(level: BacktestLogLevel): string {
  switch (level) {
    case 'info':
      return 'ℹ️';
    case 'warning':
      return '⚠️';
    case 'error':
      return '❌';
    case 'success':
      return '✅';
    default:
      return '';
  }
}

export function useBacktestPage() {
  const [selectedStrategy, setSelectedStrategy] = usePersistentState<StrategyType>('backtest_strategy', 'etf_rotation');
  const [isIntroExpanded, setIsIntroExpanded] = useState(true);
  const [selectedETFs, setSelectedETFs] = usePersistentState<string[]>('backtest_etfs', DEFAULT_SELECTED_ETFS);
  const [backtestParams, setBacktestParams] = usePersistentState<BacktestPageParams>('backtest_params', DEFAULT_BACKTEST_PARAMS);
  const [allStrategyParams, setAllStrategyParams] = usePersistentState<Record<StrategyType, StrategyParamsRecord>>(
    'backtest_all_strategy_params',
    {} as Record<StrategyType, StrategyParamsRecord>
  );
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = usePersistentState<BacktestResult | null>('backtest_result', null);
  const [progress, setProgress] = useState(0);
  const [progressText, setProgressText] = useState('');
  const [logs, setLogs] = usePersistentState<LogEntry[]>('backtest_logs', []);

  const currentStrategy = useMemo(
    () => getStrategyByIdOrFirst(selectedStrategy),
    [selectedStrategy]
  );

  const strategyParams = useMemo(
    () => allStrategyParams[selectedStrategy] ?? createDefaultStrategyParams(currentStrategy),
    [allStrategyParams, selectedStrategy, currentStrategy]
  );
  const needsCustomEtfPool = useMemo(
    () => strategyNeedsCustomEtfPool(selectedStrategy),
    [selectedStrategy]
  );

  const addLog = (level: BacktestLogLevel, message: string) => {
    const now = new Date();
    const time = now.toLocaleTimeString('zh-CN', { hour12: false });
    setLogs((prev) => [...prev, { time, level, message }]);
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const setStrategyParams = (params: StrategyParamsRecord) => {
    setAllStrategyParams((prev) => ({
      ...prev,
      [selectedStrategy]: params,
    }));
  };

  const handleStrategyChange = (strategyId: StrategyType) => {
    setSelectedStrategy(strategyId);
    setIsIntroExpanded(true);
    setResult(null);
    clearLogs();
  };

  const runBacktest = async () => {
    setIsRunning(true);
    setProgress(0);
    setProgressText('');
    clearLogs();
    setResult(null);

    addLog('info', `开始回测策略: ${currentStrategy.name}`);
    if (needsCustomEtfPool) {
      addLog('info', `已选择 ${selectedETFs.length} 只ETF: ${selectedETFs.join(', ')}`);
    } else {
      addLog('info', '当前策略使用内置证券池，无需配置ETF池');
    }

    if (needsCustomEtfPool && selectedETFs.length === 0) {
      addLog('error', '错误: 请至少选择一只ETF');
      setIsRunning(false);
      return;
    }

    addLog('info', `回测时间范围: ${backtestParams.startDate} 至 ${backtestParams.endDate}`);
    addLog('info', `初始资金: ${backtestParams.initialCapital.toLocaleString()} 元`);

    try {
      setProgress(10);
      setProgressText('正在初始化回测引擎...');
      addLog('info', '正在初始化回测引擎...');
      await new Promise((resolve) => setTimeout(resolve, 200));

      setProgress(20);
      setProgressText('正在从服务器获取历史数据...');
      addLog('info', '正在从服务器获取历史数据...');

      setProgress(35);
      setProgressText('正在提交回测请求...');
      addLog('info', '正在提交回测请求...');

      const apiResult = await apiClient.runBacktest({
        strategy: selectedStrategy,
        strategy_params: normalizeStrategyParams(strategyParams),
        backtest_params: {
          start_date: backtestParams.startDate,
          end_date: backtestParams.endDate,
          initial_capital: backtestParams.initialCapital,
          commission_rate: defaultBacktestConfig.commission,
          stamp_duty: defaultBacktestConfig.stampDuty,
          slippage: defaultBacktestConfig.slippage,
        },
        etf_codes: needsCustomEtfPool ? selectedETFs : [],
      });

      setProgress(75);
      setProgressText('正在解析回测结果...');
      addLog('info', '正在解析回测结果...');

      const backtestResult = adaptBacktestResult(apiResult);

      setProgress(100);
      setProgressText('回测完成!');
      addLog('success', '回测完成!');

      if (backtestResult.actualStartDate && backtestResult.actualEndDate) {
        addLog('info', `实际回测时间: ${backtestResult.actualStartDate} 至 ${backtestResult.actualEndDate}`);
      }

      setResult(backtestResult);

      if (backtestResult.equityCurve.length > 0) {
        addLog('success', `总收益率: ${backtestResult.totalReturn.toFixed(2)}%`);
        addLog('success', `年化收益: ${backtestResult.annualReturn.toFixed(2)}%`);
        addLog('success', `最大回撤: ${backtestResult.maxDrawdown.toFixed(2)}%`);
        addLog('success', `夏普比率: ${backtestResult.sharpeRatio.toFixed(2)}`);
        addLog('info', `交易次数: ${backtestResult.totalTrades}`);
      } else {
        addLog('warning', '未能获取到有效数据，请检查日期范围和证券代码');
      }
    } catch (error) {
      addLog('error', `回测失败: ${formatUnknownError(error)}`);
    } finally {
      setIsRunning(false);
    }
  };

  const exportReport = () => {
    if (!result) {
      return;
    }

    const reportContent = [
      '策略回测报告',
      '================',
      '',
      `策略名称: ${currentStrategy.name}`,
      `回测时间: ${result.actualStartDate || backtestParams.startDate} 至 ${result.actualEndDate || backtestParams.endDate}`,
      `初始资金: ¥${backtestParams.initialCapital.toLocaleString()}`,
      '',
      '=== 回测结果 ===',
      `总收益率: ${result.totalReturn.toFixed(2)}%`,
      `年化收益: ${result.annualReturn.toFixed(2)}%`,
      `最大回撤: ${result.maxDrawdown.toFixed(2)}%`,
      `夏普比率: ${result.sharpeRatio.toFixed(2)}`,
      `索提诺比率: ${result.sortinoRatio.toFixed(2)}`,
      `卡玛比率: ${result.calmarRatio.toFixed(2)}`,
      `胜率: ${result.winRate.toFixed(2)}%`,
      `盈亏比: ${result.profitFactor.toFixed(2)}`,
      `交易次数: ${result.totalTrades}`,
      `最终资产: ¥${result.finalAsset.toLocaleString()}`,
      '',
      '=== 交易记录 ===',
      ...result.trades.map(
        (trade, index) =>
          `${index + 1}. ${trade.date} ${trade.type === 'buy' ? '买入' : '卖出'} ${trade.name}(${trade.code}) 价格:¥${trade.price} 数量:${trade.shares} 金额:¥${trade.amount.toFixed(2)}`
      ),
    ].join('\n');

    const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `回测报告_${currentStrategy.name}_${getTodayDateString()}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    addLog('success', '报告已导出');
  };

  return {
    selectedStrategy,
    isIntroExpanded,
    selectedETFs,
    needsCustomEtfPool,
    backtestParams,
    strategyParams,
    currentStrategy,
    isRunning,
    result,
    progress,
    progressText,
    logs,
    setIsIntroExpanded,
    setSelectedETFs,
    setBacktestParams,
    setStrategyParams,
    clearLogs,
    handleStrategyChange,
    runBacktest,
    exportReport,
  };
}
