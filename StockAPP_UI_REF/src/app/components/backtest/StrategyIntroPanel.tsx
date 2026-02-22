import React from 'react';
import { Badge } from '../ui/badge';
import type { Strategy } from '../../utils/strategyConfig';

interface StrategyIntroPanelProps {
  strategy: Strategy;
}

export default function StrategyIntroPanel({ strategy }: StrategyIntroPanelProps) {
  return (
    <div className="space-y-6">
      {/* 策略概述 */}
      <div className="flex items-start space-x-4">
        <div className="flex-shrink-0 w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center text-3xl">
          {strategy.icon}
        </div>
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <h3 className="text-xl">{strategy.name}</h3>
            <Badge style={{ backgroundColor: strategy.color, color: 'white' }}>
              {strategy.type}
            </Badge>
          </div>
          <p className="text-gray-600">{strategy.description}</p>
        </div>
      </div>

      <div className="border-t pt-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* 策略逻辑 */}
          <div>
            <div className="flex items-center space-x-2 mb-3">
              <span>📋</span>
              <h4 className="font-medium">策略逻辑</h4>
            </div>
            <div className="space-y-2">
              {strategy.logic.map((step, index) => (
                <div key={index} className="text-sm text-gray-600">
                  {step}
                </div>
              ))}
            </div>
          </div>

          {/* 参数说明 */}
          <div>
            <div className="flex items-center space-x-2 mb-3">
              <span>⚙️</span>
              <h4 className="font-medium">参数说明</h4>
            </div>
            <div className="space-y-2">
              {strategy.parameters.map((param, index) => (
                <div key={index} className="text-sm">
                  <span className="text-gray-700">• {param.label}:</span>
                  <span className="text-gray-500 ml-1">{param.description}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 使用说明 */}
          <div>
            <div className="flex items-center space-x-2 mb-3">
              <span>✅</span>
              <h4 className="font-medium">适用场景</h4>
            </div>
            <p className="text-sm text-gray-600 mb-4">{strategy.适用场景}</p>

            <div className="flex items-center space-x-2 mb-3">
              <span>⚠️</span>
              <h4 className="font-medium">风险提示</h4>
            </div>
            <p className="text-sm text-gray-600">{strategy.风险提示}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
