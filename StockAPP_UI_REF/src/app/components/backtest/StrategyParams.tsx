import React, { useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Label } from '../ui/label';
import { Slider } from '../ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import type { Strategy } from '../../utils/strategyConfig';

interface StrategyParamsProps {
  strategy: Strategy;
  params: Record<string, any>;
  onChange: (params: Record<string, any>) => void;
}

export default function StrategyParams({ strategy, params, onChange }: StrategyParamsProps) {
  const updateParam = (key: string, value: any) => {
    onChange({ ...params, [key]: value });
  };

  // 初始化参数
  useEffect(() => {
    const defaultParams: Record<string, any> = {};
    strategy.parameters.forEach(param => {
      if (params[param.key] === undefined) {
        defaultParams[param.key] = param.default;
      }
    });
    if (Object.keys(defaultParams).length > 0) {
      onChange({ ...params, ...defaultParams });
    }
  }, [strategy.id]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>📊 策略参数</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {strategy.parameters.map(param => {
          const value = params[param.key] ?? param.default;

          if (param.type === 'slider') {
            return (
              <div key={param.key}>
                <div className="flex justify-between items-center mb-2">
                  <Label>{param.label}</Label>
                  <span className="text-sm font-medium text-blue-600">
                    {typeof value === 'number' && value < 1 ? value.toFixed(2) : value}
                  </span>
                </div>
                <Slider
                  value={[value]}
                  onValueChange={([v]) => updateParam(param.key, v)}
                  min={param.min}
                  max={param.max}
                  step={param.step}
                  className="mt-2"
                />
                <p className="text-xs text-gray-500 mt-1">{param.description}</p>
              </div>
            );
          }

          if (param.type === 'select' && param.options) {
            return (
              <div key={param.key}>
                <Label>{param.label}</Label>
                <Select value={value} onValueChange={v => updateParam(param.key, v)}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {param.options.map(opt => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-500 mt-1">{param.description}</p>
              </div>
            );
          }

          return null;
        })}

        <div className="pt-4 border-t">
          <details className="cursor-pointer">
            <summary className="text-sm font-medium text-gray-700 hover:text-gray-900">
              🔧 高级参数
            </summary>
            <div className="mt-3 text-sm text-gray-600">
              <p>暂无高级参数可配置</p>
            </div>
          </details>
        </div>
      </CardContent>
    </Card>
  );
}