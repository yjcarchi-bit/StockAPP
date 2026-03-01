import { strategies, type ETF, type Strategy, type StrategyType } from './strategyConfig';

export type StrategyParamsRecord = Record<string, unknown>;

export interface BacktestPageParams {
  startDate: string;
  endDate: string;
  initialCapital: number;
  benchmark: string;
}

export function getTodayDateString(): string {
  return new Date().toISOString().split('T')[0];
}

export function getDefaultSelectedEtfCodes(pool: Pick<ETF, 'code' | 'selected'>[]): string[] {
  return pool.filter((item) => item.selected).map((item) => item.code);
}

export function getStrategyById(strategyId: StrategyType, strategyList: Strategy[] = strategies): Strategy | undefined {
  return strategyList.find((item) => item.id === strategyId);
}

export function getStrategyByIdOrFirst(strategyId: StrategyType, strategyList: Strategy[] = strategies): Strategy {
  return getStrategyById(strategyId, strategyList) ?? strategyList[0];
}

export function createDefaultStrategyParams(
  strategy: StrategyType | Strategy,
  strategyList: Strategy[] = strategies
): StrategyParamsRecord {
  const resolvedStrategy =
    typeof strategy === 'string' ? getStrategyByIdOrFirst(strategy, strategyList) : strategy;
  const defaults: StrategyParamsRecord = {};
  resolvedStrategy.parameters.forEach((param) => {
    defaults[param.key] = param.default;
  });
  return defaults;
}

export function normalizeStrategyParams(params: StrategyParamsRecord): StrategyParamsRecord {
  const mapped: StrategyParamsRecord = { ...params };
  if (Object.prototype.hasOwnProperty.call(mapped, 'stop_loss')) {
    mapped.stop_loss_ratio = mapped.stop_loss;
    delete mapped.stop_loss;
  }
  if (Object.prototype.hasOwnProperty.call(mapped, 'use_short_momentum')) {
    mapped.use_short_momentum_filter = mapped.use_short_momentum;
    delete mapped.use_short_momentum;
  }
  if (Object.prototype.hasOwnProperty.call(mapped, 'use_atr_stop')) {
    mapped.use_atr_stop_loss = mapped.use_atr_stop;
    delete mapped.use_atr_stop;
  }
  return mapped;
}

export function strategyNeedsCustomEtfPool(strategyId: StrategyType): boolean {
  return strategyId === 'etf_rotation';
}

export function strategiesNeedCustomEtfPool(strategyIds: StrategyType[]): boolean {
  return strategyIds.some((strategyId) => strategyNeedsCustomEtfPool(strategyId));
}
