import React, { useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Label } from '../ui/label';
import { Slider } from '../ui/slider';
import { Switch } from '../ui/switch';
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

  const sliderParams = strategy.parameters.filter(p => p.type === 'slider');
  const booleanParams = strategy.parameters.filter(p => p.type === 'boolean');
  const selectParams = strategy.parameters.filter(p => p.type === 'select');

  return (
    <Card>
      <CardHeader>
        <CardTitle>📊 策略参数</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {sliderParams.length > 0 && (
          <div className="space-y-4">
            {sliderParams.map(param => {
              const value = params[param.key] ?? param.default;

              return (
                <div key={param.key}>
                  <div className="flex justify-between items-center mb-2">
                    <Label>{param.label}</Label>
                    <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
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
                  <p className="text-xs text-muted-foreground mt-1">{param.description}</p>
                </div>
              );
            })}
          </div>
        )}

        {selectParams.length > 0 && (
          <div className="space-y-4">
            {selectParams.map(param => {
              const value = params[param.key] ?? param.default;

              return (
                <div key={param.key}>
                  <Label>{param.label}</Label>
                  <Select value={String(value)} onValueChange={v => updateParam(param.key, v)}>
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {param.options?.map(opt => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground mt-1">{param.description}</p>
                </div>
              );
            })}
          </div>
        )}

        {booleanParams.length > 0 && (
          <div className="pt-4 border-t space-y-4">
            <h4 className="text-sm font-medium text-foreground mb-3">⚙️ 过滤与止损选项</h4>
            {booleanParams.map(param => {
              const value = params[param.key] ?? param.default;

              return (
                <div key={param.key} className="flex items-center justify-between py-2">
                  <div className="flex-1 pr-4">
                    <Label className="cursor-pointer text-sm font-medium">{param.label}</Label>
                    <p className="text-xs text-muted-foreground mt-0.5">{param.description}</p>
                  </div>
                  <div className="flex-shrink-0">
                    <button
                      type="button"
                      role="switch"
                      aria-checked={value === true}
                      onClick={() => updateParam(param.key, !value)}
                      className={`
                        relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                        focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
                        ${value ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'}
                      `}
                    >
                      <span
                        className={`
                          inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                          ${value ? 'translate-x-6' : 'translate-x-1'}
                        `}
                      />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
