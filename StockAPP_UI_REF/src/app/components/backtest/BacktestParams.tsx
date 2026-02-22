import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';

interface BacktestParamsProps {
  params: {
    startDate: string;
    endDate: string;
    initialCapital: number;
    benchmark: string;
  };
  onChange: (params: any) => void;
}

export default function BacktestParams({ params, onChange }: BacktestParamsProps) {
  const updateParam = (key: string, value: any) => {
    onChange({ ...params, [key]: value });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>📅 回测参数</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label htmlFor="startDate">开始日期</Label>
          <Input
            id="startDate"
            type="date"
            value={params.startDate}
            onChange={e => updateParam('startDate', e.target.value)}
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="endDate">结束日期</Label>
          <Input
            id="endDate"
            type="date"
            value={params.endDate}
            onChange={e => updateParam('endDate', e.target.value)}
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="initialCapital">初始资金（元）</Label>
          <Input
            id="initialCapital"
            type="number"
            value={params.initialCapital}
            onChange={e => updateParam('initialCapital', Number(e.target.value))}
            className="mt-1"
            step="10000"
            min="10000"
          />
        </div>

        <div>
          <Label htmlFor="benchmark">基准指数</Label>
          <Select value={params.benchmark} onValueChange={v => updateParam('benchmark', v)}>
            <SelectTrigger className="mt-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="510300">沪深300</SelectItem>
              <SelectItem value="510500">中证500</SelectItem>
              <SelectItem value="159915">创业板指</SelectItem>
              <SelectItem value="000001">上证指数</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="pt-4 border-t">
          <details className="cursor-pointer">
            <summary className="text-sm font-medium text-gray-700 hover:text-gray-900">
              ⚙️ 交易费用设置
            </summary>
            <div className="mt-3 space-y-3 text-sm text-gray-600">
              <div className="flex justify-between">
                <span>佣金费率:</span>
                <span>0.03%</span>
              </div>
              <div className="flex justify-between">
                <span>印花税:</span>
                <span>0.1%</span>
              </div>
              <div className="flex justify-between">
                <span>滑点:</span>
                <span>0.1%</span>
              </div>
            </div>
          </details>
        </div>
      </CardContent>
    </Card>
  );
}
