import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import type { StrategyType } from '../../utils/strategyConfig';
import { strategies } from '../../utils/strategyConfig';
import type { ComparisonDataPoint } from '../../hooks/useComparePage';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';

interface CompareChartsProps {
  selectedStrategies: StrategyType[];
  comparisonData: ComparisonDataPoint[];
  equityData: Array<Record<string, string | number>>;
}

const LINE_COLORS = ['#2563eb', '#16a34a', '#dc2626'];

export default function CompareCharts({
  selectedStrategies,
  comparisonData,
  equityData,
}: CompareChartsProps) {
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>净值曲线对比</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={equityData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return `${date.getMonth() + 1}/${date.getDate()}`;
                }}
              />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              {selectedStrategies.map((strategyId, index) => {
                const strategy = strategies.find((item) => item.id === strategyId)!;
                return (
                  <Line
                    key={strategyId}
                    type="monotone"
                    dataKey={strategy.name}
                    stroke={LINE_COLORS[index]}
                    strokeWidth={2}
                    dot={false}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>总收益率对比</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={comparisonData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="总收益率" fill="#2563eb" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>最大回撤对比</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={comparisonData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="最大回撤" fill="#dc2626" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
