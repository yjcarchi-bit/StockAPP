import React from 'react';
import { Badge } from '../ui/badge';
import type { Strategy } from '../../utils/strategyConfig';

interface StrategyIntroPanelProps {
  strategy: Strategy;
}

export default function StrategyIntroPanel({ strategy }: StrategyIntroPanelProps) {
  const isCompound = strategy.category === 'compound';
  
  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <div className={`flex-shrink-0 w-16 h-16 rounded-full flex items-center justify-center text-3xl ${
          isCompound ? 'bg-purple-100 dark:bg-purple-900/30' : 'bg-blue-100 dark:bg-blue-900/30'
        }`}>
          {strategy.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <h3 className="text-xl font-semibold">{strategy.name}</h3>
            <Badge 
              className={isCompound 
                ? 'bg-purple-500 hover:bg-purple-600' 
                : 'bg-primary hover:bg-primary/90'
              }
            >
              {strategy.type}
            </Badge>
            {isCompound && (
              <Badge variant="outline" className="border-purple-500 text-purple-500">
                复合策略
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground leading-relaxed">{strategy.description}</p>
        </div>
      </div>

      <div className="border-t pt-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-lg">📋</span>
              <h4 className="font-medium">策略逻辑</h4>
            </div>
            <div className="space-y-2">
              {strategy.logic.map((step, index) => (
                <div key={index} className="text-sm text-muted-foreground leading-relaxed pl-1">
                  {step}
                </div>
              ))}
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-lg">⚙️</span>
              <h4 className="font-medium">参数说明</h4>
            </div>
            <div className="space-y-2">
              {strategy.parameters.map((param, index) => (
                <div key={index} className="text-sm">
                  <span className="text-foreground font-medium">• {param.label}:</span>
                  <span className="text-muted-foreground ml-1">{param.description}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="space-y-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">✅</span>
                  <h4 className="font-medium">适用场景</h4>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">{strategy.适用场景}</p>
              </div>

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">⚠️</span>
                  <h4 className="font-medium">风险提示</h4>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">{strategy.风险提示}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
