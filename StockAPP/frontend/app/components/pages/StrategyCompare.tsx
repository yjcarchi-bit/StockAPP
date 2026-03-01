import React from 'react';
import { Play, RotateCcw } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { strategies, etfPool } from '../../utils/strategyConfig';
import ETFSelector from '../backtest/ETFSelector';
import StrategySelectionCard from '../compare/StrategySelectionCard';
import CompareResultsTable from '../compare/CompareResultsTable';
import CompareCharts from '../compare/CompareCharts';
import CompareHighlights from '../compare/CompareHighlights';
import { useComparePage } from '../../hooks';

export default function StrategyCompare() {
  const {
    selectedStrategies,
    selectedETFs,
    needsCustomEtfPool,
    params,
    results,
    isRunning,
    comparisonData,
    equityData,
    bestReturn,
    bestSharpe,
    minDrawdown,
    setSelectedETFs,
    setParams,
    toggleStrategy,
    runCompare,
    clearResults,
  } = useComparePage();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl mb-2 text-foreground">📊 策略对比</h1>
        <p className="text-muted-foreground">对比多个策略的回测结果，帮助您选择最优策略</p>
      </div>

      {strategies.length < 2 && (
        <Card className="border-yellow-300 bg-yellow-50 dark:bg-yellow-900/20">
          <CardContent className="pt-6 text-sm text-yellow-800 dark:text-yellow-200">
            当前仅配置了 1 个策略，无法进行对比。请先新增至少 2 个可用策略。
          </CardContent>
        </Card>
      )}

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

      {needsCustomEtfPool ? (
        <ETFSelector
          etfs={etfPool}
          selectedCodes={selectedETFs}
          onChange={setSelectedETFs}
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>标的配置</CardTitle>
            <CardDescription>
              当前选择的策略均使用内置证券池，不需要手动配置 ETF 池。
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      <StrategySelectionCard
        selectedStrategies={selectedStrategies}
        onToggleStrategy={toggleStrategy}
      />

      <div className="flex items-center gap-4">
        <Button
          size="lg"
          onClick={runCompare}
          disabled={isRunning || selectedStrategies.length < 2 || (needsCustomEtfPool && selectedETFs.length === 0)}
          className="bg-primary hover:bg-primary/90"
        >
          <Play className="mr-2 h-5 w-5" />
          {isRunning ? '对比运行中...' : '🚀 开始对比回测'}
        </Button>
        {results.size > 0 && (
          <Button variant="outline" size="lg" onClick={clearResults}>
            <RotateCcw className="mr-2 h-5 w-5" />
            🔄 清除结果
          </Button>
        )}
      </div>

      {results.size > 0 && (
        <>
          <CompareResultsTable comparisonData={comparisonData} />
          <CompareCharts
            selectedStrategies={selectedStrategies}
            comparisonData={comparisonData}
            equityData={equityData}
          />
          <CompareHighlights
            bestReturn={bestReturn}
            bestSharpe={bestSharpe}
            minDrawdown={minDrawdown}
          />
        </>
      )}
    </div>
  );
}
