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

export type {
  RealtimeQuote,
  StrategySignal,
  ConnectionStatus,
  UseRealtimeDataOptions,
  UseRealtimeDataReturn,
} from './useRealtimeData';
