import React from 'react';
import { Play, Download } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { strategies, etfPool } from '../../utils/strategyConfig';
import { Progress } from '../ui/progress';
import { useOptimizationPage } from '../../hooks';

export default function ParameterOptimization() {
  const {
    selectedStrategy,
    selectedETF,
    needsCustomEtfPool,
    dateRange,
    initialCapital,
    optimizationMethod,
    optimizationTarget,
    isOptimizing,
    progress,
    results,
    bestResult,
    currentStrategy,
    totalCombinations,
    setSelectedStrategy,
    setSelectedETF,
    setDateRange,
    setInitialCapital,
    setOptimizationMethod,
    setOptimizationTarget,
    optimize,
  } = useOptimizationPage();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl mb-2 text-foreground">🔧 策略参数优化</h1>
        <p className="text-muted-foreground">通过参数优化找到最佳策略配置</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
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
                      ? 'bg-primary/10 border-2 border-primary'
                      : 'bg-card border border-border hover:bg-accent'
                  }`}
                >
                  <div className="flex items-center">
                    <span className="text-2xl mr-3">{strategy.icon}</span>
                    <div className="text-sm font-medium text-foreground">{strategy.name}</div>
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
                <Select
                  value={optimizationMethod}
                  onValueChange={(value) => setOptimizationMethod(value as 'grid' | 'random')}
                >
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
                <Select
                  value={optimizationTarget}
                  onValueChange={(value) => setOptimizationTarget(value as 'sharpe' | 'return')}
                >
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

        <div className="lg:col-span-3 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>参数网格设置</CardTitle>
              <CardDescription>当前策略的参数范围</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {currentStrategy.parameters.map(param => (
                  <div key={param.key} className="flex justify-between items-center p-3 bg-muted rounded">
                    <span className="font-medium text-foreground">{param.label}:</span>
                    <span className="text-muted-foreground">
                      {param.type === 'slider' && param.min !== undefined && param.max !== undefined
                        ? `${param.min} ~ ${param.max}`
                        : param.options?.map(o => o.label).join(', ')}
                    </span>
                  </div>
                ))}
              </div>

              <div className="mt-6 p-4 bg-primary/10 border border-primary/20 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-foreground">📊 参数组合总数:</span>
                  <span className="text-2xl font-bold text-primary">{totalCombinations}</span>
                </div>
                <div className="mt-2 text-sm text-muted-foreground">
                  预计耗时: 约 {Math.ceil(totalCombinations / 2)} 秒
                </div>
              </div>

              {needsCustomEtfPool ? (
                <div className="mt-4">
                  <Label>ETF池配置（ETF轮动策略）</Label>
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
              ) : (
                <div className="mt-4 p-3 bg-muted rounded text-sm text-muted-foreground">
                  当前策略使用内置证券池，优化时无需单独配置 ETF 池。
                </div>
              )}

              <Button
                className="w-full mt-6 bg-primary hover:bg-primary/90"
                size="lg"
                onClick={optimize}
                disabled={isOptimizing}
              >
                <Play className="mr-2 h-5 w-5" />
                {isOptimizing ? '优化中...' : '🚀 开始优化'}
              </Button>

              {isOptimizing && (
                <div className="mt-4">
                  <Progress value={progress} className="w-full" />
                  <p className="text-sm text-muted-foreground mt-2 text-center">
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
                    <div className="p-4 bg-muted rounded-lg">
                      <div className="text-sm text-muted-foreground">总组合数</div>
                      <div className="text-2xl font-bold text-foreground">{results.length}</div>
                    </div>
                    <div className="p-4 bg-primary/10 rounded-lg">
                      <div className="text-sm text-muted-foreground">最优收益</div>
                      <div className="text-2xl font-bold text-primary">
                        +{bestResult.totalReturn.toFixed(2)}%
                      </div>
                    </div>
                    <div className="p-4 bg-green-500/10 rounded-lg">
                      <div className="text-sm text-muted-foreground">最优夏普</div>
                      <div className="text-2xl font-bold text-green-500">
                        {bestResult.sharpeRatio.toFixed(2)}
                      </div>
                    </div>
                    <div className="p-4 bg-red-500/10 rounded-lg">
                      <div className="text-sm text-muted-foreground">最大回撤</div>
                      <div className="text-2xl font-bold text-red-500">
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
                          <div key={key} className="flex justify-between p-3 bg-primary/10 rounded">
                            <span className="font-medium text-foreground">{param?.label || key}:</span>
                            <span className="text-primary font-bold">
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
                      <div className="flex justify-between p-3 bg-muted rounded">
                        <span className="text-muted-foreground">总收益率:</span>
                        <span className="font-bold text-green-500">
                          +{bestResult.totalReturn.toFixed(2)}%
                        </span>
                      </div>
                      <div className="flex justify-between p-3 bg-muted rounded">
                        <span className="text-muted-foreground">夏普比率:</span>
                        <span className="font-bold text-foreground">{bestResult.sharpeRatio.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between p-3 bg-muted rounded">
                        <span className="text-muted-foreground">最大回撤:</span>
                        <span className="font-bold text-red-500">
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
                      <thead className="sticky top-0 bg-muted border-b">
                        <tr>
                          <th className="p-2 text-left text-foreground">排名</th>
                          <th className="p-2 text-left text-foreground">参数配置</th>
                          <th className="p-2 text-right text-foreground">总收益率</th>
                          <th className="p-2 text-right text-foreground">夏普比率</th>
                          <th className="p-2 text-right text-foreground">最大回撤</th>
                        </tr>
                      </thead>
                      <tbody>
                        {results.slice(0, 10).map((result, index) => (
                          <tr key={index} className="border-b hover:bg-muted/50">
                            <td className="p-2 text-foreground">#{index + 1}</td>
                            <td className="p-2 text-xs text-muted-foreground">
                              {Object.entries(result.params)
                                .map(([k, v]) => `${k}=${typeof v === 'number' && v < 1 ? v.toFixed(2) : v}`)
                                .join(', ')}
                            </td>
                            <td className="p-2 text-right text-green-500">
                              +{result.totalReturn.toFixed(2)}%
                            </td>
                            <td className="p-2 text-right text-foreground">{result.sharpeRatio.toFixed(2)}</td>
                            <td className="p-2 text-right text-red-500">
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
                <Button size="lg" className="flex-1 bg-primary hover:bg-primary/90">
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
