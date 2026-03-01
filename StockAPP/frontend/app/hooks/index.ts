/**
 * Hooks 模块导出
 */

export {
  useRealtimeData,
  useRealtimeQuotes,
  useStrategySignal,
} from './useRealtimeData';

export {
  usePersistentState,
  usePersistentCallback,
  clearPersistentState,
  getPersistentState,
  setPersistentState,
} from './usePersistentState';

export {
  useBacktestPage,
  getLogColor,
  getLogPrefix,
} from './useBacktestPage';

export {
  useComparePage,
} from './useComparePage';

export {
  useOptimizationPage,
} from './useOptimizationPage';

export type {
  RealtimeQuote,
  StrategySignal,
  ConnectionStatus,
  UseRealtimeDataOptions,
  UseRealtimeDataReturn,
} from './useRealtimeData';
