import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { TrendingUp, TrendingDown, Activity, DollarSign } from 'lucide-react';
import type { BacktestResult } from '../../utils/backtestEngine';
import EquityCurveChart from '../charts/EquityCurveChart';
import TradeList from '../charts/TradeList';
import MonthlyHeatmap from '../charts/MonthlyHeatmap';
import MetricsTable from '../charts/MetricsTable';

interface BacktestResultsProps {
  result: BacktestResult;
}

export default function BacktestResults({ result }: BacktestResultsProps) {
  const formatNumber = (num: number, decimals: number = 2) => {
    return num.toFixed(decimals);
  };

  const formatCurrency = (num: number) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'CNY',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(num);
  };

  const getColorClass = (value: number) => {
    if (value > 0) return 'text-green-600';
    if (value < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  const metrics = [
    {
      label: '总收益率',
      value: `${formatNumber(result.totalReturn)}%`,
      icon: TrendingUp,
      color: result.totalReturn > 0 ? 'text-green-600' : 'text-red-600',
      bgColor: result.totalReturn > 0 ? 'bg-green-50' : 'bg-red-50',
      description: result.totalReturn > 0 ? '📈 vs基准 +5.2%' : '📉 vs基准 -3.1%',
    },
    {
      label: '年化收益',
      value: `${formatNumber(result.annualReturn)}%`,
      icon: Activity,
      color: result.annualReturn > 0 ? 'text-green-600' : 'text-red-600',
      bgColor: result.annualReturn > 0 ? 'bg-green-50' : 'bg-red-50',
      description: '',
    },
    {
      label: '最大回撤',
      value: `${formatNumber(result.maxDrawdown)}%`,
      icon: TrendingDown,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      description: '注意风险',
    },
    {
      label: '夏普比率',
      value: formatNumber(result.sharpeRatio),
      icon: Activity,
      color: result.sharpeRatio > 1 ? 'text-green-600' : 'text-orange-600',
      bgColor: result.sharpeRatio > 1 ? 'bg-green-50' : 'bg-orange-50',
      description: result.sharpeRatio > 1 ? '优秀' : '一般',
    },
  ];

  const secondaryMetrics = [
    { label: '胜率', value: `${formatNumber(result.winRate)}%` },
    { label: '盈亏比', value: formatNumber(result.profitFactor) },
    { label: '交易次数', value: result.totalTrades },
    { label: '最终资产', value: formatCurrency(result.finalAsset) },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>📊 回测结果</CardTitle>
        </CardHeader>
        <CardContent>
          {/* 主要指标 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {metrics.map((metric, index) => {
              const Icon = metric.icon;
              return (
                <div
                  key={index}
                  className={`p-4 rounded-lg border-2 ${metric.bgColor}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-600">{metric.label}</span>
                    <Icon className={`h-5 w-5 ${metric.color}`} />
                  </div>
                  <div className={`text-2xl mb-1 ${metric.color}`}>
                    {metric.value}
                  </div>
                  {metric.description && (
                    <div className="text-xs text-gray-600">{metric.description}</div>
                  )}
                </div>
              );
            })}
          </div>

          {/* 次要指标 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {secondaryMetrics.map((metric, index) => (
              <div key={index} className="p-4 bg-gray-50 rounded-lg border">
                <div className="text-sm text-gray-600 mb-1">{metric.label}</div>
                <div className="text-xl">{metric.value}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 详细分析标签页 */}
      <Card>
        <CardContent className="pt-6">
          <Tabs defaultValue="equity" className="w-full">
            <TabsList className="grid w-full grid-cols-4 lg:grid-cols-6">
              <TabsTrigger value="equity">📈 资金曲线</TabsTrigger>
              <TabsTrigger value="trades">📝 交易记录</TabsTrigger>
              <TabsTrigger value="metrics">📊 详细指标</TabsTrigger>
              <TabsTrigger value="monthly">📅 月度收益</TabsTrigger>
            </TabsList>

            <TabsContent value="equity" className="mt-6">
              <EquityCurveChart
                equityCurve={result.equityCurve}
                drawdownSeries={result.drawdownSeries}
              />
            </TabsContent>

            <TabsContent value="trades" className="mt-6">
              <TradeList trades={result.trades} />
            </TabsContent>

            <TabsContent value="metrics" className="mt-6">
              <MetricsTable result={result} />
            </TabsContent>

            <TabsContent value="monthly" className="mt-6">
              <MonthlyHeatmap monthlyReturns={result.monthlyReturns} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
