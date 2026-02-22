import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Play, FileDown } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { strategies, etfPool, defaultBacktestConfig, type StrategyType, type Strategy } from '../../utils/strategyConfig';
import StrategyIntroPanel from '../backtest/StrategyIntroPanel';
import BacktestParams from '../backtest/BacktestParams';
import StrategyParams from '../backtest/StrategyParams';
import ETFSelector from '../backtest/ETFSelector';
import BacktestResults from '../backtest/BacktestResults';
import { runBacktest } from '../../utils/backtestRunner';
import type { BacktestResult } from '../../utils/backtestEngine';

export default function StrategyBacktest() {
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyType>('etf_rotation');
  const [isIntroExpanded, setIsIntroExpanded] = useState(true);
  const [selectedETFs, setSelectedETFs] = useState<string[]>(
    etfPool.filter(etf => etf.selected).map(etf => etf.code)
  );
  const [backtestParams, setBacktestParams] = useState({
    startDate: '2021-01-01',
    endDate: '2024-01-01',
    initialCapital: 100000,
    benchmark: '510300',
  });
  const [strategyParams, setStrategyParams] = useState<Record<string, any>>({});
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);

  const currentStrategy = strategies.find(s => s.id === selectedStrategy)!;

  const handleStrategyChange = (strategyId: StrategyType) => {
    setSelectedStrategy(strategyId);
    setIsIntroExpanded(true);
    // 重置策略参数为默认值
    const strategy = strategies.find(s => s.id === strategyId)!;
    const defaultParams: Record<string, any> = {};
    strategy.parameters.forEach(param => {
      defaultParams[param.key] = param.default;
    });
    setStrategyParams(defaultParams);
    setResult(null);
  };

  const handleRunBacktest = async () => {
    setIsRunning(true);
    
    // 模拟异步回测过程
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    const config = {
      strategy: selectedStrategy,
      ...backtestParams,
      ...defaultBacktestConfig,
      parameters: strategyParams,
      etfCodes: selectedETFs,
    };
    
    const backtestResult = runBacktest(config);
    setResult(backtestResult);
    setIsRunning(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl">📈 策略回测</h1>
          <p className="text-gray-600 mt-2">选择策略、配置参数，开始回测分析</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 左侧策略选择 */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>选择策略</CardTitle>
              <CardDescription>6种经典量化策略</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {strategies.map(strategy => (
                <button
                  key={strategy.id}
                  onClick={() => handleStrategyChange(strategy.id)}
                  className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
                    selectedStrategy === strategy.id
                      ? 'bg-blue-50 border-2 border-blue-500 text-blue-700'
                      : 'bg-white border border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center">
                    <span className="text-2xl mr-3">{strategy.icon}</span>
                    <div>
                      <div className="font-medium">{strategy.name}</div>
                      <div className="text-xs text-gray-500">{strategy.type}</div>
                    </div>
                  </div>
                </button>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* 右侧配置和结果 */}
        <div className="lg:col-span-3 space-y-6">
          {/* 策略介绍面板 */}
          <Card>
            <CardHeader
              className="cursor-pointer hover:bg-gray-50 transition-colors"
              onClick={() => setIsIntroExpanded(!isIntroExpanded)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {isIntroExpanded ? (
                    <ChevronDown className="h-5 w-5" />
                  ) : (
                    <ChevronRight className="h-5 w-5" />
                  )}
                  <span className="text-2xl">{currentStrategy.icon}</span>
                  <div>
                    <CardTitle>{currentStrategy.name} - 策略介绍</CardTitle>
                  </div>
                </div>
              </div>
            </CardHeader>
            {isIntroExpanded && (
              <CardContent>
                <StrategyIntroPanel strategy={currentStrategy} />
              </CardContent>
            )}
          </Card>

          {/* 参数配置 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <BacktestParams
              params={backtestParams}
              onChange={setBacktestParams}
            />
            <StrategyParams
              strategy={currentStrategy}
              params={strategyParams}
              onChange={setStrategyParams}
            />
          </div>

          {/* ETF池配置 */}
          <ETFSelector
            etfs={etfPool}
            selectedCodes={selectedETFs}
            onChange={setSelectedETFs}
          />

          {/* 操作按钮 */}
          <div className="flex items-center justify-between">
            <Button
              size="lg"
              onClick={handleRunBacktest}
              disabled={isRunning || selectedETFs.length === 0}
              className="bg-blue-600 hover:bg-blue-700"
            >
              <Play className="mr-2 h-5 w-5" />
              {isRunning ? '回测运行中...' : '🚀 开始回测'}
            </Button>
            {result && (
              <Button variant="outline" size="lg">
                <FileDown className="mr-2 h-5 w-5" />
                📄 导出报告
              </Button>
            )}
          </div>

          {/* 回测结果 */}
          {result && <BacktestResults result={result} />}
        </div>
      </div>
    </div>
  );
}
