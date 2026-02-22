import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, ComposedChart } from 'recharts';
import type { EquityPoint, DrawdownPoint } from '../../utils/backtestEngine';

interface EquityCurveChartProps {
  equityCurve: EquityPoint[];
  drawdownSeries: DrawdownPoint[];
}

export default function EquityCurveChart({ equityCurve, drawdownSeries }: EquityCurveChartProps) {
  // 合并数据
  const chartData = equityCurve.map((point, index) => ({
    date: point.date,
    资产净值: point.value,
    回撤: -drawdownSeries[index].drawdown,
  }));

  // 采样数据以提高性能（如果数据点太多）
  const sampledData = chartData.length > 200 
    ? chartData.filter((_, i) => i % Math.ceil(chartData.length / 200) === 0)
    : chartData;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium mb-4">策略资金曲线</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={sampledData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => {
                const date = new Date(value);
                return `${date.getMonth() + 1}/${date.getDate()}`;
              }}
            />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip
              formatter={(value: number) => [
                new Intl.NumberFormat('zh-CN').format(value),
                '',
              ]}
              labelFormatter={(label) => `日期: ${label}`}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="资产净值"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
              name="策略净值"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div>
        <h3 className="text-lg font-medium mb-4">回撤曲线</h3>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={sampledData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => {
                const date = new Date(value);
                return `${date.getMonth() + 1}/${date.getDate()}`;
              }}
            />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip
              formatter={(value: number) => [
                `${Math.abs(value).toFixed(2)}%`,
                '',
              ]}
              labelFormatter={(label) => `日期: ${label}`}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="回撤"
              fill="#ef4444"
              stroke="#dc2626"
              fillOpacity={0.6}
              name="回撤幅度"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
