import React, { useState } from 'react';
import { Play, Download } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { strategies, etfPool, type StrategyType } from '../../utils/strategyConfig';
import { runBacktest } from '../../utils/backtestRunner';
import { Progress } from '../ui/progress';

interface OptimizationResult {
  params: Record<string, any>;
  totalReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
}

export default function ParameterOptimization() {
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyType>('dual_ma');
  const [selectedETF, setSelectedETF] = useState('510300');
  const [dateRange, setDateRange] = useState({
    startDate: '2021-01-01',
    endDate: '2024-01-01',
  });
  const [initialCapital, setInitialCapital] = useState(100000);
  const [optimizationMethod, setOptimizationMethod] = useState<'grid' | 'random'>('grid');
  const [optimizationTarget, setOptimizationTarget] = useState<'sharpe' | 'return'>('sharpe');
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<OptimizationResult[]>([]);
  const [bestResult, setBestResult] = useState<OptimizationResult | null>(null);

  const currentStrategy = strategies.find(s => s.id === selectedStrategy)!;

  // 生成参数网格
  const generateParamGrid = () => {
    const strategy = strategies.find(s => s.id === selectedStrategy)!;
    const grids: Record<string, any[]> = {};
    let totalCombinations = 1;

    strategy.parameters.forEach(param => {
      if (param.type === 'slider' && param.min !== undefined && param.max !== undefined && param.step !== undefined) {
        const values = [];
        for (let v = param.min; v <= param.max; v += param.step * 2) {
          values.push(v);
        }
        grids[param.key] = values;
        totalCombinations *= values.length;
      } else if (param.type === 'select' && param.options) {
        grids[param.key] = param.options.map(o => o.value);
        totalCombinations *= param.options.length;
      }
    });

    return { grids, totalCombinations };
  };

  const handleOptimize = async () => {
    setIsOptimizing(true);
    setProgress(0);
    
    const { grids, totalCombinations } = generateParamGrid();
    const allResults: OptimizationResult[] = [];
    
    // 生成所有参数组合
    const paramKeys = Object.keys(grids);
    const combinations: Record<string, any>[] = [];
    
    const generateCombinations = (index: number, current: Record<string, any>) => {
      if (index === paramKeys.length) {
        combinations.push({ ...current });
        return;
      }
      
      const key = paramKeys[index];
      grids[key].forEach((value: any) => {
        current[key] = value;
        generateCombinations(index + 1, current);
      });
    };
    
    generateCombinations(0, {});
    
    // 运行回测
    for (let i = 0; i < Math.min(combinations.length, 20); i++) {
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const params = combinations[i];
      const config = {
        strategy: selectedStrategy,
        ...dateRange,
        initialCapital,
        benchmark: '510300',
        commission: 0.0003,
        stampDuty: 0.001,
        slippage: 0.001,
        parameters: params,
        etfCodes: [selectedETF],
      };
      
      const result = runBacktest(config);
      allResults.push({
        params,
        totalReturn: result.totalReturn,
        sharpeRatio: result.sharpeRatio,
        maxDrawdown: result.maxDrawdown,
      });
      
      setProgress(((i + 1) / Math.min(combinations.length, 20)) * 100);
    }
    
    // 排序结果
    const sortedResults = allResults.sort((a, b) => {
      if (optimizationTarget === 'sharpe') {
        return b.sharpeRatio - a.sharpeRatio;
      } else {
        return b.totalReturn - a.totalReturn;
      }
    });
    
    setResults(sortedResults);
    setBestResult(sortedResults[0]);
    setIsOptimizing(false);
  };

  const { totalCombinations } = generateParamGrid();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl mb-2">🔧 策略参数优化</h1>
        <p className="text-gray-600">通过参数优化找到最佳策略配置</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 左侧配置 */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>选择策略</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {strategies.slice(0, 4).map(strategy => (
                <button
                  key={strategy.id}
                  onClick={() => setSelectedStrategy(strategy.id)}
                  className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
                    selectedStrategy === strategy.id
                      ? 'bg-blue-50 border-2 border-blue-500'
                      : 'bg-white border border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center">
                    <span className="text-2xl mr-3">{strategy.icon}</span>
                    <div className="text-sm font-medium">{strategy.name}</div>
                  </div>
                </button>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>回测区间</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>开始日期</Label>
                <Input
                  type="date"
                  value={dateRange.startDate}
                  onChange={e => setDateRange({ ...dateRange, startDate: e.target.value })}
                  className="mt-1"
                />
              </div>
              <div>
                <Label>结束日期</Label>
                <Input
                  type="date"
                  value={dateRange.endDate}
                  onChange={e => setDateRange({ ...dateRange, endDate: e.target.value })}
                  className="mt-1"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>其他设置</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>初始资金</Label>
                <Input
                  type="number"
                  value={initialCapital}
                  onChange={e => setInitialCapital(Number(e.target.value))}
                  className="mt-1"
                  step="10000"
                />
              </div>
              
              <div>
                <Label>优化方法</Label>
                <Select value={optimizationMethod} onValueChange={(v: any) => setOptimizationMethod(v)}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="grid">网格搜索</SelectItem>
                    <SelectItem value="random">随机搜索</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>优化目标</Label>
                <Select value={optimizationTarget} onValueChange={(v: any) => setOptimizationTarget(v)}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sharpe">夏普比率</SelectItem>
                    <SelectItem value="return">总收益率</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 右侧结果 */}
        <div className="lg:col-span-3 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>参数网格设置</CardTitle>
              <CardDescription>当前策略的参数范围</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {currentStrategy.parameters.map(param => (
                  <div key={param.key} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <span className="font-medium">{param.label}:</span>
                    <span className="text-gray-600">
                      {param.type === 'slider' && param.min !== undefined && param.max !== undefined
                        ? `${param.min} ~ ${param.max}`
                        : param.options?.map(o => o.label).join(', ')}
                    </span>
                  </div>
                ))}
              </div>

              <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="font-medium">📊 参数组合总数:</span>
                  <span className="text-2xl font-bold text-blue-600">{totalCombinations}</span>
                </div>
                <div className="mt-2 text-sm text-gray-600">
                  预计耗时: 约 {Math.ceil(totalCombinations / 2)} 秒
                </div>
              </div>

              <div className="mt-4">
                <Label>证券代码</Label>
                <Select value={selectedETF} onValueChange={setSelectedETF}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {etfPool.slice(0, 5).map(etf => (
                      <SelectItem key={etf.code} value={etf.code}>
                        {etf.code} - {etf.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Button
                className="w-full mt-6 bg-blue-600 hover:bg-blue-700"
                size="lg"
                onClick={handleOptimize}
                disabled={isOptimizing}
              >
                <Play className="mr-2 h-5 w-5" />
                {isOptimizing ? '优化中...' : '🚀 开始优化'}
              </Button>

              {isOptimizing && (
                <div className="mt-4">
                  <Progress value={progress} className="w-full" />
                  <p className="text-sm text-gray-600 mt-2 text-center">
                    优化进度: {progress.toFixed(0)}%
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {bestResult && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>📊 优化结果</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <div className="text-sm text-gray-600">总组合数</div>
                      <div className="text-2xl font-bold">{results.length}</div>
                    </div>
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <div className="text-sm text-gray-600">最优收益</div>
                      <div className="text-2xl font-bold text-blue-600">
                        +{bestResult.totalReturn.toFixed(2)}%
                      </div>
                    </div>
                    <div className="p-4 bg-green-50 rounded-lg">
                      <div className="text-sm text-gray-600">最优夏普</div>
                      <div className="text-2xl font-bold text-green-600">
                        {bestResult.sharpeRatio.toFixed(2)}
                      </div>
                    </div>
                    <div className="p-4 bg-red-50 rounded-lg">
                      <div className="text-sm text-gray-600">最大回撤</div>
                      <div className="text-2xl font-bold text-red-600">
                        {bestResult.maxDrawdown.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle>🏆 最优参数</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {Object.entries(bestResult.params).map(([key, value]) => {
                        const param = currentStrategy.parameters.find(p => p.key === key);
                        return (
                          <div key={key} className="flex justify-between p-3 bg-blue-50 rounded">
                            <span className="font-medium">{param?.label || key}:</span>
                            <span className="text-blue-600 font-bold">
                              {typeof value === 'number' && value < 1 ? value.toFixed(2) : value}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>📈 最优指标</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex justify-between p-3 bg-gray-50 rounded">
                        <span className="text-gray-700">总收益率:</span>
                        <span className="font-bold text-green-600">
                          +{bestResult.totalReturn.toFixed(2)}%
                        </span>
                      </div>
                      <div className="flex justify-between p-3 bg-gray-50 rounded">
                        <span className="text-gray-700">夏普比率:</span>
                        <span className="font-bold">{bestResult.sharpeRatio.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between p-3 bg-gray-50 rounded">
                        <span className="text-gray-700">最大回撤:</span>
                        <span className="font-bold text-red-600">
                          {bestResult.maxDrawdown.toFixed(2)}%
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>排名列表</CardTitle>
                  <CardDescription>按 {optimizationTarget === 'sharpe' ? '夏普比率' : '总收益率'} 排序</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="max-h-96 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-gray-50 border-b">
                        <tr>
                          <th className="p-2 text-left">排名</th>
                          <th className="p-2 text-left">参数配置</th>
                          <th className="p-2 text-right">总收益率</th>
                          <th className="p-2 text-right">夏普比率</th>
                          <th className="p-2 text-right">最大回撤</th>
                        </tr>
                      </thead>
                      <tbody>
                        {results.slice(0, 10).map((result, index) => (
                          <tr key={index} className="border-b hover:bg-gray-50">
                            <td className="p-2">#{index + 1}</td>
                            <td className="p-2 text-xs">
                              {Object.entries(result.params)
                                .map(([k, v]) => `${k}=${typeof v === 'number' && v < 1 ? v.toFixed(2) : v}`)
                                .join(', ')}
                            </td>
                            <td className="p-2 text-right text-green-600">
                              +{result.totalReturn.toFixed(2)}%
                            </td>
                            <td className="p-2 text-right">{result.sharpeRatio.toFixed(2)}</td>
                            <td className="p-2 text-right text-red-600">
                              {result.maxDrawdown.toFixed(2)}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              <div className="flex gap-4">
                <Button variant="outline" size="lg" className="flex-1">
                  <Download className="mr-2 h-5 w-5" />
                  📥 导出优化结果
                </Button>
                <Button size="lg" className="flex-1 bg-blue-600 hover:bg-blue-700">
                  🔄 使用最优参数回测
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
