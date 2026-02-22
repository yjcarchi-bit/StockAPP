import React, { useState, useEffect, useRef, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, ComposedChart, Brush } from 'recharts';
import type { EquityPoint, DrawdownPoint } from '../../utils/backtestEngine';

interface EquityCurveChartProps {
  equityCurve: EquityPoint[];
  drawdownSeries: DrawdownPoint[];
}

export default function EquityCurveChart({ equityCurve, drawdownSeries }: EquityCurveChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [chartHeight, setChartHeight] = useState(300);
  const [containerWidth, setContainerWidth] = useState(800);

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const width = containerRef.current.offsetWidth;
        setContainerWidth(width);
        
        if (width < 400) {
          setChartHeight(200);
        } else if (width < 600) {
          setChartHeight(250);
        } else if (width < 900) {
          setChartHeight(300);
        } else if (width < 1200) {
          setChartHeight(350);
        } else {
          setChartHeight(400);
        }
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  const { chartData, sampledData, xTickInterval, dataLength } = useMemo(() => {
    const data = equityCurve.map((point, index) => ({
      date: point.date,
      fullDate: point.date,
      资产净值: point.value,
      回撤: -drawdownSeries[index]?.drawdown || 0,
    }));

    const totalPoints = data.length;
    let sampled = data;
    let tickInterval = 0;

    if (totalPoints > 500) {
      const sampleRate = Math.ceil(totalPoints / 300);
      sampled = data.filter((_, i) => i % sampleRate === 0 || i === totalPoints - 1);
      tickInterval = Math.ceil(sampled.length / 8);
    } else if (totalPoints > 200) {
      const sampleRate = Math.ceil(totalPoints / 200);
      sampled = data.filter((_, i) => i % sampleRate === 0 || i === totalPoints - 1);
      tickInterval = Math.ceil(sampled.length / 6);
    } else if (totalPoints > 100) {
      tickInterval = Math.ceil(totalPoints / 10);
    } else if (totalPoints > 50) {
      tickInterval = Math.ceil(totalPoints / 8);
    } else {
      tickInterval = Math.ceil(totalPoints / 5);
    }

    return {
      chartData: data,
      sampledData: sampled,
      xTickInterval: Math.max(tickInterval, 0),
      dataLength: totalPoints,
    };
  }, [equityCurve, drawdownSeries]);

  const minValue = Math.min(...sampledData.map(d => d.资产净值));
  const maxValue = Math.max(...sampledData.map(d => d.资产净值));
  const yDomain = [Math.floor(minValue * 0.95), Math.ceil(maxValue * 1.05)];

  const formatXAxisTick = (value: string) => {
    const date = new Date(value);
    const month = date.getMonth() + 1;
    const day = date.getDate();
    
    if (dataLength > 365 * 2) {
      return `${date.getFullYear()}/${month}`;
    } else if (dataLength > 365) {
      return `${month}月`;
    } else if (dataLength > 90) {
      return `${month}/${day}`;
    } else {
      return `${month}/${day}`;
    }
  };

  const formatCurrency = (value: number) => {
    if (value >= 100000000) {
      return `${(value / 100000000).toFixed(2)}亿`;
    } else if (value >= 10000) {
      return `${(value / 10000).toFixed(1)}万`;
    }
    return value.toFixed(0);
  };

  const showBrush = dataLength > 200;

  return (
    <div ref={containerRef} className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">策略资金曲线</h3>
        <span className="text-sm text-muted-foreground">
          共 {dataLength} 个交易日
        </span>
      </div>
      
      <div style={{ width: '100%', height: chartHeight + (showBrush ? 60 : 0) }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart 
            data={sampledData} 
            margin={{ top: 10, right: 30, left: 10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color, #e5e7eb)" />
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 11, fill: 'var(--text-muted, #6b7280)' }}
              tickFormatter={formatXAxisTick}
              interval={xTickInterval}
              angle={dataLength > 365 ? -45 : 0}
              textAnchor={dataLength > 365 ? 'end' : 'middle'}
              height={dataLength > 365 ? 60 : 30}
            />
            <YAxis 
              tick={{ fontSize: 11, fill: 'var(--text-muted, #6b7280)' }}
              domain={yDomain}
              tickFormatter={formatCurrency}
              width={60}
            />
            <Tooltip
              formatter={(value: number) => [
                new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(value),
                '资产净值',
              ]}
              labelFormatter={(label) => `日期: ${label}`}
              contentStyle={{ 
                backgroundColor: 'var(--card-bg, #fff)',
                border: '1px solid var(--border-color, #e5e7eb)',
                borderRadius: '8px',
                fontSize: '12px',
              }}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            {showBrush && (
              <Brush 
                dataKey="date" 
                height={30} 
                stroke="#2563eb"
                tickFormatter={formatXAxisTick}
              />
            )}
            <Line
              type="monotone"
              dataKey="资产净值"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
              name="策略净值"
              activeDot={{ r: 4, fill: '#2563eb' }}
              isAnimationActive={dataLength < 500}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-medium">回撤曲线</h3>
        </div>
        <div style={{ width: '100%', height: chartHeight * 0.6 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart 
              data={sampledData} 
              margin={{ top: 10, right: 30, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color, #e5e7eb)" />
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 11, fill: 'var(--text-muted, #6b7280)' }}
                tickFormatter={formatXAxisTick}
                interval={xTickInterval}
                angle={dataLength > 365 ? -45 : 0}
                textAnchor={dataLength > 365 ? 'end' : 'middle'}
                height={dataLength > 365 ? 60 : 30}
              />
              <YAxis 
                tick={{ fontSize: 11, fill: 'var(--text-muted, #6b7280)' }}
                tickFormatter={(value) => `${Math.abs(value).toFixed(1)}%`}
                width={60}
              />
              <Tooltip
                formatter={(value: number) => [
                  `${Math.abs(value).toFixed(2)}%`,
                  '回撤',
                ]}
                labelFormatter={(label) => `日期: ${label}`}
                contentStyle={{ 
                  backgroundColor: 'var(--card-bg, #fff)',
                  border: '1px solid var(--border-color, #e5e7eb)',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Area
                type="monotone"
                dataKey="回撤"
                fill="#ef4444"
                stroke="#dc2626"
                fillOpacity={0.6}
                name="回撤幅度"
                isAnimationActive={dataLength < 500}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {dataLength > 365 && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-sm text-blue-700 dark:text-blue-300">
          💡 提示：数据量较大（{dataLength}个交易日），可拖动图表下方滑块查看特定时间段
        </div>
      )}
    </div>
  );
}
