import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, ChevronRight, Play, FileDown, Layers, Target, Loader2, Download } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { strategies, strategiesByCategory, etfPool, defaultBacktestConfig, type StrategyType, type Strategy } from '../../utils/strategyConfig';
import StrategyIntroPanel from '../backtest/StrategyIntroPanel';
import BacktestParams from '../backtest/BacktestParams';
import StrategyParams from '../backtest/StrategyParams';
import ETFSelector from '../backtest/ETFSelector';
import StockSelector from '../backtest/StockSelector';
import BacktestResults from '../backtest/BacktestResults';
import BacktestProgress from '../backtest/BacktestProgress';
import { runBacktestAsync } from '../../utils/backtestRunner';
import type { BacktestResult } from '../../utils/backtestEngine';
import type { DailySelectionResult } from '../../utils/backtestRunner';
import { usePersistentState } from '../../hooks';

interface Stock {
  code: string;
  name: string;
  market?: string;
  industry?: string;
}

interface LogEntry {
  time: string;
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
}

function getTodayDate(): string {
  const today = new Date();
  return today.toISOString().split('T')[0];
}

function getDefaultStartDate(): string {
  return '2015-01-01';
}

const DEFAULT_SELECTED_ETFS = etfPool.filter(etf => etf.selected).map(etf => etf.code);

const DEFAULT_BACKTEST_PARAMS = {
  startDate: getDefaultStartDate(),
  endDate: getTodayDate(),
  initialCapital: 100000,
  benchmark: '510300',
};

export default function StrategyBacktest() {
  const [selectedStrategy, setSelectedStrategy] = usePersistentState<StrategyType>('backtest_strategy', 'etf_rotation');
  const [isIntroExpanded, setIsIntroExpanded] = useState(true);
  const [selectedETFs, setSelectedETFs] = usePersistentState<string[]>('backtest_etfs', DEFAULT_SELECTED_ETFS);
  const [selectedStocks, setSelectedStocks] = usePersistentState<Stock[]>('backtest_stocks', []);
  const [backtestParams, setBacktestParams] = usePersistentState('backtest_params', DEFAULT_BACKTEST_PARAMS);
  const [strategyParams, setStrategyParams] = usePersistentState<Record<string, any>>('backtest_strategy_params', {});
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = usePersistentState<BacktestResult | null>('backtest_result', null);
  const [progress, setProgress] = useState(0);
  const [progressText, setProgressText] = useState('');
  const [currentDate, setCurrentDate] = useState('');
  const [totalDays, setTotalDays] = useState(0);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [dailyResult, setDailyResult] = useState<DailySelectionResult | null>(null);
  const [logs, setLogs] = usePersistentState<LogEntry[]>('backtest_logs', []);
  const logContainerRef = useRef<HTMLDivElement>(null);

  const currentStrategy = strategies.find(s => s.id === selectedStrategy)!;
  const isCompoundStrategy = currentStrategy.category === 'compound';
  const isAutoSelectStrategy = selectedStrategy === 'large_cap_low_drawdown';

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const addLog = (level: LogEntry['level'], message: string) => {
    const now = new Date();
    const time = now.toLocaleTimeString('zh-CN', { hour12: false });
    setLogs(prev => [...prev, { time, level, message }]);
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const handleStrategyChange = (strategyId: StrategyType) => {
    setSelectedStrategy(strategyId);
    setIsIntroExpanded(true);
    const strategy = strategies.find(s => s.id === strategyId)!;
    const defaultParams: Record<string, any> = {};
    strategy.parameters.forEach(param => {
      defaultParams[param.key] = param.default;
    });
    setStrategyParams(defaultParams);
    setResult(null);
    clearLogs();
  };

  const handleRunBacktest = async () => {
    setIsRunning(true);
    setProgress(0);
    setProgressText('');
    setDailyResult(null);
    clearLogs();
    setResult(null);

    addLog('info', `开始回测策略: ${currentStrategy.name}`);
    
    if (isAutoSelectStrategy) {
      addLog('info', '自动选股模式: 将从沪深300成分股中筛选优质标的');
    } else if (isCompoundStrategy) {
      addLog('info', `已选择 ${selectedETFs.length} 只ETF: ${selectedETFs.join(', ')}`);
      if (selectedETFs.length === 0) {
        addLog('error', '错误: 请至少选择一只ETF');
        setIsRunning(false);
        return;
      }
    } else {
      addLog('info', `已选择 ${selectedStocks.length} 只股票: ${selectedStocks.map(s => s.code).join(', ')}`);
      if (selectedStocks.length === 0) {
        addLog('error', '错误: 请至少选择一只股票');
        setIsRunning(false);
        return;
      }
    }

    addLog('info', `回测时间范围: ${backtestParams.startDate} 至 ${backtestParams.endDate}`);
    addLog('info', `初始资金: ${backtestParams.initialCapital.toLocaleString()} 元`);

    try {
      setProgress(10);
      setProgressText('正在初始化回测引擎...');
      addLog('info', '正在初始化回测引擎...');
      await new Promise(resolve => setTimeout(resolve, 200));

      setProgress(20);
      setProgressText('正在从服务器获取历史数据...');
      addLog('info', '正在从服务器获取历史数据...');

      const config = {
        strategy: selectedStrategy,
        ...backtestParams,
        ...defaultBacktestConfig,
        parameters: strategyParams,
        etfCodes: isAutoSelectStrategy 
          ? ['510300']
          : isCompoundStrategy 
            ? selectedETFs 
            : selectedStocks.map(s => s.code),
      };

      setProgress(40);
      setProgressText('正在处理数据...');
      addLog('info', '正在处理数据...');

      const handleProgress = (update: {
        currentIndex: number;
        totalDays: number;
        currentDate: string;
        percent: number;
        dailyResult: DailySelectionResult | null;
      }) => {
        setCurrentIndex(update.currentIndex);
        setTotalDays(update.totalDays);
        setCurrentDate(update.currentDate);
        setDailyResult(update.dailyResult);
        const adjustedPercent = 40 + Math.round(update.percent * 0.4);
        setProgress(adjustedPercent);
        setProgressText(`正在处理: ${update.currentDate}`);
      };

      const backtestResult = await runBacktestAsync(config, isAutoSelectStrategy ? handleProgress : undefined);
      
      setProgress(80);
      setProgressText('正在计算回测指标...');
      addLog('info', '正在计算回测指标...');
      await new Promise(resolve => setTimeout(resolve, 200));

      setProgress(100);
      setProgressText('回测完成!');
      addLog('success', '回测完成!');
      
      if (backtestResult.dataInfo?.warning) {
        addLog('warning', backtestResult.dataInfo.warning);
      }
      
      if (backtestResult.dataInfo) {
        addLog('info', `实际回测时间: ${backtestResult.dataInfo.actualStart} 至 ${backtestResult.dataInfo.actualEnd}`);
      }
      
      setResult(backtestResult);
      
      if (backtestResult.equityCurve.length > 0) {
        addLog('success', `总收益率: ${backtestResult.totalReturn.toFixed(2)}%`);
        addLog('success', `年化收益: ${backtestResult.annualReturn.toFixed(2)}%`);
        addLog('success', `最大回撤: ${backtestResult.maxDrawdown.toFixed(2)}%`);
        addLog('success', `夏普比率: ${backtestResult.sharpeRatio.toFixed(2)}`);
        addLog('info', `交易次数: ${backtestResult.totalTrades}`);
      } else {
        addLog('warning', '未能获取到有效数据，请检查日期范围和证券代码');
      }
    } catch (error) {
      addLog('error', `回测失败: ${error}`);
    } finally {
      setIsRunning(false);
    }
  };

  const getLogColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'info': return 'text-blue-600 dark:text-blue-400';
      case 'warning': return 'text-yellow-600 dark:text-yellow-400';
      case 'error': return 'text-red-600 dark:text-red-400';
      case 'success': return 'text-green-600 dark:text-green-400';
      default: return 'text-foreground';
    }
  };

  const getLogPrefix = (level: LogEntry['level']) => {
    switch (level) {
      case 'info': return 'ℹ️';
      case 'warning': return '⚠️';
      case 'error': return '❌';
      case 'success': return '✅';
      default: return '';
    }
  };

  const renderStrategyCard = (strategy: Strategy) => {
    const isSelected = selectedStrategy === strategy.id;
    const isCompound = strategy.category === 'compound';
    
    return (
      <button
        key={strategy.id}
        onClick={() => handleStrategyChange(strategy.id)}
        className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
          isSelected
            ? isCompound
              ? 'bg-purple-500/10 border-2 border-purple-500 text-purple-600 dark:text-purple-400'
              : 'bg-primary/10 border-2 border-primary text-primary'
            : 'bg-card border border-border hover:bg-accent'
        }`}
      >
        <div className="flex items-center">
          <span className="text-2xl mr-3">{strategy.icon}</span>
          <div className="flex-1">
            <div className="font-medium">{strategy.name}</div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-muted-foreground">{strategy.type}</span>
              {isCompound && (
                <span className="text-xs px-1.5 py-0.5 bg-purple-500/20 text-purple-500 rounded">
                  复合策略
                </span>
              )}
            </div>
          </div>
        </div>
      </button>
    );
  };

  const canRunBacktest = () => {
    if (isAutoSelectStrategy) {
      return true;
    }
    if (isCompoundStrategy) {
      return selectedETFs.length > 0;
    } else {
      return selectedStocks.length > 0;
    }
  };

  const handleExportReport = () => {
    if (!result) return;
    
    const reportContent = [
      `策略回测报告`,
      `================`,
      ``,
      `策略名称: ${currentStrategy.name}`,
      `回测时间: ${result.actualStartDate || backtestParams.startDate} 至 ${result.actualEndDate || backtestParams.endDate}`,
      `初始资金: ¥${backtestParams.initialCapital.toLocaleString()}`,
      ``,
      `=== 回测结果 ===`,
      `总收益率: ${result.totalReturn.toFixed(2)}%`,
      `年化收益: ${result.annualReturn.toFixed(2)}%`,
      `最大回撤: ${result.maxDrawdown.toFixed(2)}%`,
      `夏普比率: ${result.sharpeRatio.toFixed(2)}`,
      `索提诺比率: ${result.sortinoRatio.toFixed(2)}`,
      `卡玛比率: ${result.calmarRatio.toFixed(2)}`,
      `胜率: ${result.winRate.toFixed(2)}%`,
      `盈亏比: ${result.profitFactor.toFixed(2)}`,
      `交易次数: ${result.totalTrades}`,
      `最终资产: ¥${result.finalAsset.toLocaleString()}`,
      ``,
      `=== 交易记录 ===`,
      ...result.trades.map((trade, index) => 
        `${index + 1}. ${trade.date} ${trade.type === 'buy' ? '买入' : '卖出'} ${trade.name}(${trade.code}) 价格:¥${trade.price} 数量:${trade.shares} 金额:¥${trade.amount.toFixed(2)}`
      ),
    ].join('\n');
    
    const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `回测报告_${currentStrategy.name}_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    addLog('success', '报告已导出');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl text-foreground">📈 策略回测</h1>
          <p className="text-muted-foreground mt-2">选择策略、配置参数，开始回测分析</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-purple-500" />
                <CardTitle className="text-base">复合策略</CardTitle>
              </div>
              <CardDescription className="text-xs">
                多因子量化策略
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {strategiesByCategory.compound.map(renderStrategyCard)}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Target className="h-4 w-4 text-primary" />
                <CardTitle className="text-base">简易策略</CardTitle>
              </div>
              <CardDescription className="text-xs">
                单因子量化策略
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {strategiesByCategory.simple.map(renderStrategyCard)}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-3 space-y-6">
          <div className="flex items-center justify-between p-4 bg-card rounded-lg border">
            <div className="flex items-center gap-4">
              <span className="text-4xl">{currentStrategy.icon}</span>
              <div>
                <h2 className="text-xl font-bold">{currentStrategy.name}</h2>
                {currentStrategy.category === 'compound' && (
                  <span className="text-sm text-purple-500">多因子量化 - 综合多个因子进行选股择时</span>
                )}
                {currentStrategy.category === 'simple' && (
                  <span className="text-sm text-primary">单因子量化 - 基于单一因子信号交易</span>
                )}
              </div>
            </div>
            <Button
              size="lg"
              onClick={handleRunBacktest}
              disabled={isRunning || !canRunBacktest()}
              className="bg-primary hover:bg-primary/90"
            >
              {isRunning ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  回测运行中...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-5 w-5" />
                  🚀 开始回测
                </>
              )}
            </Button>
          </div>

          <Card>
            <CardHeader
              className="cursor-pointer hover:bg-accent transition-colors"
              onClick={() => setIsIntroExpanded(!isIntroExpanded)}
            >
              <div className="flex items-center gap-2">
                {isIntroExpanded ? (
                  <ChevronDown className="h-5 w-5" />
                ) : (
                  <ChevronRight className="h-5 w-5" />
                )}
                <CardTitle className="text-base">策略介绍</CardTitle>
              </div>
            </CardHeader>
            {isIntroExpanded && (
              <CardContent>
                <StrategyIntroPanel strategy={currentStrategy} />
              </CardContent>
            )}
          </Card>

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

          {isAutoSelectStrategy ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <span>🎯</span>
                  自动选股池
                </CardTitle>
                <CardDescription>
                  本策略自动从沪深300成分股中筛选优质标的
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                  <div className="text-3xl">📊</div>
                  <div className="flex-1">
                    <div className="font-medium text-blue-700 dark:text-blue-300">
                      沪深300成分股
                    </div>
                    <div className="text-sm text-blue-600 dark:text-blue-400 mt-1">
                      策略将自动从300只大盘蓝筹股中，通过六因子打分系统筛选优质标的
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">300</div>
                    <div className="text-xs text-blue-500">只股票</div>
                  </div>
                </div>
                <div className="mt-4 text-sm text-muted-foreground">
                  <div className="font-medium mb-2">六因子筛选体系：</div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                      <span>5日动量 (0-25分)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                      <span>20日动量 (0-20分)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                      <span>趋势强度 (0-25分)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                      <span>量比因子 (0-10分)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                      <span>波动率因子 (0-10分)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                      <span>市值因子 (0-10分)</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : isCompoundStrategy ? (
            <ETFSelector
              etfs={etfPool}
              selectedCodes={selectedETFs}
              onChange={setSelectedETFs}
            />
          ) : (
            <StockSelector
              selectedStocks={selectedStocks}
              onChange={setSelectedStocks}
              maxStocks={10}
            />
          )}

          {isRunning && (
            isAutoSelectStrategy ? (
              <BacktestProgress
                currentIndex={currentIndex}
                totalDays={totalDays}
                currentDate={currentDate}
                percent={progress}
                dailyResult={dailyResult}
              />
            ) : (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    回测进度
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="w-full bg-secondary rounded-full h-3 overflow-hidden">
                    <div 
                      className="bg-primary h-full rounded-full transition-all duration-300 ease-out"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{progressText}</span>
                    <span className="font-medium">{progress}%</span>
                  </div>
                </CardContent>
              </Card>
            )
          )}

          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">📝 回测日志</CardTitle>
                {logs.length > 0 && (
                  <Button variant="ghost" size="sm" onClick={clearLogs}>
                    清空日志
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <div 
                ref={logContainerRef}
                className="bg-gray-900 dark:bg-gray-950 rounded-lg p-4 h-48 overflow-y-auto font-mono text-sm"
              >
                {logs.length === 0 ? (
                  <div className="text-gray-500 text-center py-8">
                    点击"开始回测"后，日志将显示在这里
                  </div>
                ) : (
                  logs.map((log, index) => (
                    <div key={index} className={`${getLogColor(log.level)} mb-1`}>
                      <span className="text-gray-500">[{log.time}]</span>{' '}
                      <span>{getLogPrefix(log.level)}</span>{' '}
                      <span>{log.message}</span>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {result && result.equityCurve.length > 0 && (
            <>
              {result && (
                <div className="flex justify-end">
                  <Button variant="outline" size="lg" onClick={handleExportReport}>
                    <Download className="mr-2 h-5 w-5" />
                    📄 导出报告
                  </Button>
                </div>
              )}
              <BacktestResults result={result} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
