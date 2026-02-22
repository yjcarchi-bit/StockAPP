import React, { useState } from 'react';
import { Play, RotateCcw } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { strategies, strategiesByCategory, etfPool, type StrategyType, type Strategy } from '../../utils/strategyConfig';
import ETFSelector from '../backtest/ETFSelector';
import { runBacktest } from '../../utils/backtestRunner';
import type { BacktestResult } from '../../utils/backtestEngine';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

export default function StrategyCompare() {
  const [selectedStrategies, setSelectedStrategies] = useState<StrategyType[]>(['etf_rotation']);
  const [selectedETFs, setSelectedETFs] = useState<string[]>(
    etfPool.filter(etf => etf.selected).map(etf => etf.code)
  );
  const [params, setParams] = useState({
    startDate: '2021-01-01',
    endDate: '2024-01-01',
    initialCapital: 100000,
  });
  const [results, setResults] = useState<Map<StrategyType, BacktestResult>>(new Map());
  const [isRunning, setIsRunning] = useState(false);

  const toggleStrategy = (strategyId: StrategyType) => {
    if (selectedStrategies.includes(strategyId)) {
      setSelectedStrategies(selectedStrategies.filter(s => s !== strategyId));
    } else {
      if (selectedStrategies.length < 3) {
        setSelectedStrategies([...selectedStrategies, strategyId]);
      }
    }
  };

  const handleRunCompare = async () => {
    setIsRunning(true);
    await new Promise(resolve => setTimeout(resolve, 2000));

    const newResults = new Map<StrategyType, BacktestResult>();
    
    selectedStrategies.forEach(strategyId => {
      const strategy = strategies.find(s => s.id === strategyId)!;
      const defaultParams: Record<string, any> = {};
      strategy.parameters.forEach(param => {
        defaultParams[param.key] = param.default;
      });

      const config = {
        strategy: strategyId,
        ...params,
        benchmark: '510300',
        commission: 0.0003,
        stampDuty: 0.001,
        slippage: 0.001,
        parameters: defaultParams,
        etfCodes: selectedETFs,
      };

      const result = runBacktest(config);
      newResults.set(strategyId, result);
    });

    setResults(newResults);
    setIsRunning(false);
  };

  const handleClear = () => {
    setResults(new Map());
  };

  const comparisonData = selectedStrategies.map(strategyId => {
    const strategy = strategies.find(s => s.id === strategyId)!;
    const result = results.get(strategyId);
    return {
      name: strategy.name,
      总收益率: result?.totalReturn || 0,
      年化收益: result?.annualReturn || 0,
      最大回撤: result?.maxDrawdown || 0,
      夏普比率: result?.sharpeRatio || 0,
    };
  });

  const equityData = results.size > 0 ? 
    Array.from(results.values())[0].equityCurve.map((point, index) => {
      const dataPoint: any = { date: point.date };
      selectedStrategies.forEach(strategyId => {
        const strategy = strategies.find(s => s.id === strategyId)!;
        const result = results.get(strategyId);
        if (result) {
          dataPoint[strategy.name] = result.equityCurve[index]?.value || 0;
        }
      });
      return dataPoint;
    }).filter((_, i) => i % 5 === 0)
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl mb-2 text-foreground">📊 策略对比</h1>
        <p className="text-muted-foreground">对比多个策略的回测结果，帮助您选择最优策略</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>配置参数</CardTitle>
          <CardDescription>设置回测时间范围和初始资金</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="startDate">开始日期</Label>
              <Input
                id="startDate"
                type="date"
                value={params.startDate}
                onChange={e => setParams({ ...params, startDate: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="endDate">结束日期</Label>
              <Input
                id="endDate"
                type="date"
                value={params.endDate}
                onChange={e => setParams({ ...params, endDate: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="initialCapital">初始资金（元）</Label>
              <Input
                id="initialCapital"
                type="number"
                value={params.initialCapital}
                onChange={e => setParams({ ...params, initialCapital: Number(e.target.value) })}
                className="mt-1"
                step="10000"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <ETFSelector
        etfs={etfPool}
        selectedCodes={selectedETFs}
        onChange={setSelectedETFs}
      />

      <Card>
        <CardHeader>
          <CardTitle>📈 选择要对比的策略（最多3个）</CardTitle>
          <CardDescription>
            已选择 {selectedStrategies.length} 个策略
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 复合策略 */}
          <div>
            <div className="text-sm font-medium text-purple-500 mb-2">复合策略</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {strategiesByCategory.compound.map(strategy => {
                const isSelected = selectedStrategies.includes(strategy.id);
                const isDisabled = !isSelected && selectedStrategies.length >= 3;
                
                return (
                  <button
                    key={strategy.id}
                    onClick={() => !isDisabled && toggleStrategy(strategy.id)}
                    disabled={isDisabled}
                    className={`p-4 rounded-lg border-2 transition-all text-left ${
                      isSelected
                        ? 'bg-purple-500/10 border-purple-500 shadow-sm'
                        : isDisabled
                        ? 'bg-muted border-border opacity-50 cursor-not-allowed'
                        : 'bg-card border-border hover:border-purple-500/50'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`w-6 h-6 rounded border-2 flex items-center justify-center ${
                        isSelected ? 'bg-purple-500 border-purple-500' : 'border-muted-foreground'
                      }`}>
                        {isSelected && (
                          <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 12 12">
                            <path d="M10 3L4.5 8.5L2 6" stroke="currentColor" strokeWidth="2" fill="none" />
                          </svg>
                        )}
                      </div>
                      <span className="text-2xl">{strategy.icon}</span>
                      <div>
                        <div className="font-medium text-foreground">{strategy.name}</div>
                        <div className="text-xs text-muted-foreground">{strategy.type}</div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 简易策略 */}
          <div>
            <div className="text-sm font-medium text-primary mb-2">简易策略</div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {strategiesByCategory.simple.map(strategy => {
                const isSelected = selectedStrategies.includes(strategy.id);
                const isDisabled = !isSelected && selectedStrategies.length >= 3;
                
                return (
                  <button
                    key={strategy.id}
                    onClick={() => !isDisabled && toggleStrategy(strategy.id)}
                    disabled={isDisabled}
                    className={`p-4 rounded-lg border-2 transition-all text-left ${
                      isSelected
                        ? 'bg-primary/10 border-primary shadow-sm'
                        : isDisabled
                        ? 'bg-muted border-border opacity-50 cursor-not-allowed'
                        : 'bg-card border-border hover:border-primary/50'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`w-6 h-6 rounded border-2 flex items-center justify-center ${
                        isSelected ? 'bg-primary border-primary' : 'border-muted-foreground'
                      }`}>
                        {isSelected && (
                          <svg className="w-4 h-4 text-primary-foreground" fill="currentColor" viewBox="0 0 12 12">
                            <path d="M10 3L4.5 8.5L2 6" stroke="currentColor" strokeWidth="2" fill="none" />
                          </svg>
                        )}
                      </div>
                      <span className="text-2xl">{strategy.icon}</span>
                      <div>
                        <div className="font-medium text-foreground">{strategy.name}</div>
                        <div className="text-xs text-muted-foreground">{strategy.type}</div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center gap-4">
        <Button
          size="lg"
          onClick={handleRunCompare}
          disabled={isRunning || selectedStrategies.length === 0 || selectedETFs.length === 0}
          className="bg-primary hover:bg-primary/90"
        >
          <Play className="mr-2 h-5 w-5" />
          {isRunning ? '对比运行中...' : '🚀 开始对比回测'}
        </Button>
        {results.size > 0 && (
          <Button variant="outline" size="lg" onClick={handleClear}>
            <RotateCcw className="mr-2 h-5 w-5" />
            🔄 清除结果
          </Button>
        )}
      </div>

      {results.size > 0 && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>📊 对比结果</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted">
                      <th className="p-3 text-left font-medium text-foreground">策略</th>
                      <th className="p-3 text-right font-medium text-foreground">总收益率</th>
                      <th className="p-3 text-right font-medium text-foreground">年化收益</th>
                      <th className="p-3 text-right font-medium text-foreground">最大回撤</th>
                      <th className="p-3 text-right font-medium text-foreground">夏普比率</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparisonData.map((data, index) => (
                      <tr key={index} className="border-b hover:bg-muted/50">
                        <td className="p-3 font-medium text-foreground">{data.name}</td>
                        <td className={`p-3 text-right ${data.总收益率 > 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {data.总收益率.toFixed(2)}%
                        </td>
                        <td className={`p-3 text-right ${data.年化收益 > 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {data.年化收益.toFixed(2)}%
                        </td>
                        <td className="p-3 text-right text-red-500">
                          {data.最大回撤.toFixed(2)}%
                        </td>
                        <td className={`p-3 text-right ${data.夏普比率 > 1 ? 'text-green-500' : 'text-orange-500'}`}>
                          {data.夏普比率.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

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
                    const strategy = strategies.find(s => s.id === strategyId)!;
                    const colors = ['#2563eb', '#16a34a', '#dc2626'];
                    return (
                      <Line
                        key={strategyId}
                        type="monotone"
                        dataKey={strategy.name}
                        stroke={colors[index]}
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

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="bg-gradient-to-br from-green-500/10 to-green-500/20">
              <CardHeader>
                <CardTitle className="text-lg">🏆 最高收益</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">
                  {comparisonData.reduce((max, d) => d.总收益率 > max.总收益率 ? d : max).name}
                </div>
                <div className="text-green-500">
                  {comparisonData.reduce((max, d) => d.总收益率 > max.总收益率 ? d : max).总收益率.toFixed(2)}%
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-blue-500/10 to-blue-500/20">
              <CardHeader>
                <CardTitle className="text-lg">📈 最高夏普</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600">
                  {comparisonData.reduce((max, d) => d.夏普比率 > max.夏普比率 ? d : max).name}
                </div>
                <div className="text-blue-500">
                  {comparisonData.reduce((max, d) => d.夏普比率 > max.夏普比率 ? d : max).夏普比率.toFixed(2)}
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-orange-500/10 to-orange-500/20">
              <CardHeader>
                <CardTitle className="text-lg">🛡️ 最小回撤</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-orange-600">
                  {comparisonData.reduce((min, d) => d.最大回撤 < min.最大回撤 ? d : min).name}
                </div>
                <div className="text-orange-500">
                  {comparisonData.reduce((min, d) => d.最大回撤 < min.最大回撤 ? d : min).最大回撤.toFixed(2)}%
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
