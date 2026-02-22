import React from 'react';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

interface ScoreRadarChartProps {
  scores: {
    momentum5: number;
    momentum20: number;
    trendStrength: number;
    volumeRatio: number;
    volatility: number;
    marketCap: number;
  };
  maxScores?: {
    momentum5: number;
    momentum20: number;
    trendStrength: number;
    volumeRatio: number;
    volatility: number;
    marketCap: number;
  };
  size?: number;
}

const defaultMaxScores = {
  momentum5: 25,
  momentum20: 20,
  trendStrength: 25,
  volumeRatio: 10,
  volatility: 10,
  marketCap: 10,
};

const factorLabels: Record<string, string> = {
  momentum5: '5日动量',
  momentum20: '20日动量',
  trendStrength: '趋势强度',
  volumeRatio: '量比因子',
  volatility: '波动率',
  marketCap: '市值因子',
};

export default function ScoreRadarChart({
  scores,
  maxScores = defaultMaxScores,
  size = 200,
}: ScoreRadarChartProps) {
  const data = Object.entries(scores).map(([key, value]) => ({
    factor: factorLabels[key] || key,
    score: value,
    maxScore: maxScores[key as keyof typeof maxScores],
    percentage: Math.round((value / maxScores[key as keyof typeof maxScores]) * 100),
  }));

  return (
    <div style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid 
            stroke="hsl(var(--border))"
            strokeWidth={1}
          />
          <PolarAngleAxis 
            dataKey="factor" 
            tick={{ 
              fill: 'hsl(var(--muted-foreground))', 
              fontSize: 10,
            }}
            tickLine={false}
          />
          <PolarRadiusAxis 
            angle={30} 
            domain={[0, 100]}
            tick={{ 
              fill: 'hsl(var(--muted-foreground))', 
              fontSize: 8,
            }}
            tickCount={5}
            axisLine={false}
          />
          <Radar
            name="得分"
            dataKey="percentage"
            stroke="hsl(var(--primary))"
            fill="hsl(var(--primary))"
            fillOpacity={0.3}
            strokeWidth={2}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div className="bg-popover border border-border rounded-lg p-2 shadow-lg">
                    <div className="text-sm font-medium">{data.factor}</div>
                    <div className="text-xs text-muted-foreground">
                      得分: {data.score} / {data.maxScore}
                    </div>
                    <div className="text-xs text-primary">
                      百分比: {data.percentage}%
                    </div>
                  </div>
                );
              }
              return null;
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
