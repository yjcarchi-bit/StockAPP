import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { strategiesByCategory, type StrategyType } from '../../utils/strategyConfig';

interface StrategySelectionCardProps {
  selectedStrategies: StrategyType[];
  onToggleStrategy: (strategyId: StrategyType) => void;
}

function StrategyOptionCard({
  strategyId,
  name,
  icon,
  type,
  selectedStrategies,
  onToggleStrategy,
  selectedClassName,
  hoverClassName,
  selectedCheckClassName,
  selectedCheckIconClassName,
}: {
  strategyId: StrategyType;
  name: string;
  icon: string;
  type: string;
  selectedStrategies: StrategyType[];
  onToggleStrategy: (strategyId: StrategyType) => void;
  selectedClassName: string;
  hoverClassName: string;
  selectedCheckClassName: string;
  selectedCheckIconClassName: string;
}) {
  const isSelected = selectedStrategies.includes(strategyId);
  const isDisabled = !isSelected && selectedStrategies.length >= 3;

  return (
    <button
      onClick={() => !isDisabled && onToggleStrategy(strategyId)}
      disabled={isDisabled}
      className={`p-4 rounded-lg border-2 transition-all text-left ${
        isSelected
          ? selectedClassName
          : isDisabled
          ? 'bg-muted border-border opacity-50 cursor-not-allowed'
          : hoverClassName
      }`}
    >
      <div className="flex items-center space-x-3">
        <div
          className={`w-6 h-6 rounded border-2 flex items-center justify-center ${
            isSelected ? selectedCheckClassName : 'border-muted-foreground'
          }`}
        >
          {isSelected && (
            <svg className={`w-4 h-4 ${selectedCheckIconClassName}`} fill="currentColor" viewBox="0 0 12 12">
              <path d="M10 3L4.5 8.5L2 6" stroke="currentColor" strokeWidth="2" fill="none" />
            </svg>
          )}
        </div>
        <span className="text-2xl">{icon}</span>
        <div>
          <div className="font-medium text-foreground">{name}</div>
          <div className="text-xs text-muted-foreground">{type}</div>
        </div>
      </div>
    </button>
  );
}

export default function StrategySelectionCard({
  selectedStrategies,
  onToggleStrategy,
}: StrategySelectionCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>📈 选择要对比的策略（最多3个）</CardTitle>
        <CardDescription>已选择 {selectedStrategies.length} 个策略</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="text-sm font-medium text-purple-500 mb-2">复合策略</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {strategiesByCategory.compound.map((strategy) => (
              <StrategyOptionCard
                key={strategy.id}
                strategyId={strategy.id}
                name={strategy.name}
                icon={strategy.icon}
                type={strategy.type}
                selectedStrategies={selectedStrategies}
                onToggleStrategy={onToggleStrategy}
                selectedClassName="bg-purple-500/10 border-purple-500 shadow-sm"
                hoverClassName="bg-card border-border hover:border-purple-500/50"
                selectedCheckClassName="bg-purple-500 border-purple-500"
                selectedCheckIconClassName="text-white"
              />
            ))}
          </div>
        </div>

        <div>
          <div className="text-sm font-medium text-primary mb-2">简易策略</div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {strategiesByCategory.simple.map((strategy) => (
              <StrategyOptionCard
                key={strategy.id}
                strategyId={strategy.id}
                name={strategy.name}
                icon={strategy.icon}
                type={strategy.type}
                selectedStrategies={selectedStrategies}
                onToggleStrategy={onToggleStrategy}
                selectedClassName="bg-primary/10 border-primary shadow-sm"
                hoverClassName="bg-card border-border hover:border-primary/50"
                selectedCheckClassName="bg-primary border-primary"
                selectedCheckIconClassName="text-primary-foreground"
              />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
