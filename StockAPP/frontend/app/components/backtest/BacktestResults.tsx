import React from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { AlertTriangle } from 'lucide-react';
import EquityCurveChart from '../charts/EquityCurveChart';
import TradeList from '../charts/TradeList';
import MonthlyHeatmap from '../charts/MonthlyHeatmap';
import MetricsTable from '../charts/MetricsTable';
import type { BacktestResult } from '../../utils/backtestEngine';

interface BacktestResultsProps {
  result: BacktestResult;
}

export default function BacktestResults({ result }: BacktestResultsProps) {
  return (
    <div className="space-y-6">
      {result.dataInfo?.warning && (
        <div className="flex items-center gap-3 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
          <div className="text-sm text-yellow-700 dark:text-yellow-300">
            {result.dataInfo.warning}
          </div>
        </div>
      )}
      
      <Card>
        <CardHeader>
          <CardTitle>📊 回测结果</CardTitle>
          <CardDescription>
            {result.actualStartDate && result.actualEndDate ? (
              <>回测期间: {result.actualStartDate} 至 {result.actualEndDate}</>
            ) : (
              <>回测期间策略表现分析</>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <div className="text-sm text-green-600 dark:text-green-400">总收益率</div>
              <div className={`text-2xl font-bold ${result.totalReturn >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {result.totalReturn >= 0 ? '+' : ''}{result.totalReturn.toFixed(2)}%
              </div>
            </div>
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <div className="text-sm text-blue-600 dark:text-blue-400">年化收益</div>
              <div className={`text-2xl font-bold ${result.annualReturn >= 0 ? 'text-blue-600 dark:text-blue-400' : 'text-red-600 dark:text-red-400'}`}>
                {result.annualReturn >= 0 ? '+' : ''}{result.annualReturn.toFixed(2)}%
              </div>
            </div>
            <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <div className="text-sm text-red-600 dark:text-red-400">最大回撤</div>
              <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                -{result.maxDrawdown.toFixed(2)}%
              </div>
            </div>
            <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
              <div className="text-sm text-purple-600 dark:text-purple-400">夏普比率</div>
              <div className={`text-2xl font-bold ${result.sharpeRatio >= 1 ? 'text-purple-600 dark:text-purple-400' : 'text-gray-600 dark:text-gray-400'}`}>
                {result.sharpeRatio.toFixed(2)}
              </div>
            </div>
          </div>

          <Tabs defaultValue="chart" className="w-full">
            <TabsList className="grid w-full grid-cols-4 h-auto">
              <TabsTrigger value="chart" className="text-xs sm:text-sm">📈 资金曲线</TabsTrigger>
              <TabsTrigger value="trades" className="text-xs sm:text-sm">📋 交易记录</TabsTrigger>
              <TabsTrigger value="monthly" className="text-xs sm:text-sm">📅 月度收益</TabsTrigger>
              <TabsTrigger value="metrics" className="text-xs sm:text-sm">📊 详细指标</TabsTrigger>
            </TabsList>

            <TabsContent value="chart" className="mt-4">
              <EquityCurveChart 
                equityCurve={result.equityCurve} 
                drawdownSeries={result.drawdownSeries} 
              />
            </TabsContent>

            <TabsContent value="trades" className="mt-4">
              <TradeList trades={result.trades} />
            </TabsContent>

            <TabsContent value="monthly" className="mt-4">
              <MonthlyHeatmap monthlyReturns={result.monthlyReturns} />
            </TabsContent>

            <TabsContent value="metrics" className="mt-4">
              <MetricsTable result={result} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
