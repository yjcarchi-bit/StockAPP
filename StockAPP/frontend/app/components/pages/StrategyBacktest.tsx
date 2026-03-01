import React, { useRef, useEffect, useState } from 'react';
import { ChevronDown, ChevronRight, Play, Loader2, Download } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { strategies, etfPool, type Strategy } from '../../utils/strategyConfig';
import StrategyIntroPanel from '../backtest/StrategyIntroPanel';
import BacktestParams from '../backtest/BacktestParams';
import StrategyParams from '../backtest/StrategyParams';
import ETFSelector from '../backtest/ETFSelector';
import BacktestResults from '../backtest/BacktestResults';
import { getLogColor, getLogPrefix, useBacktestPage } from '../../hooks';

export default function StrategyBacktest() {
  const logContainerRef = useRef<HTMLDivElement>(null);
  const [expandedParamCard, setExpandedParamCard] = useState<'backtest' | 'strategy' | null>('backtest');
  const {
    selectedStrategy,
    isIntroExpanded,
    selectedETFs,
    needsCustomEtfPool,
    backtestParams,
    strategyParams,
    currentStrategy,
    isRunning,
    result,
    progress,
    progressText,
    logs,
    setIsIntroExpanded,
    setSelectedETFs,
    setBacktestParams,
    setStrategyParams,
    clearLogs,
    handleStrategyChange,
    runBacktest,
    exportReport,
  } = useBacktestPage();

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const handleRunBacktest = () => {
    setExpandedParamCard(null);
    void runBacktest();
  };

  const renderStrategyCard = (strategy: Strategy) => {
    const isSelected = selectedStrategy === strategy.id;
    
    return (
      <button
        key={strategy.id}
        onClick={() => handleStrategyChange(strategy.id)}
        className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
          isSelected
            ? 'bg-purple-500/10 border-2 border-purple-500 text-purple-600 dark:text-purple-400'
            : 'bg-card border border-border hover:bg-accent'
        }`}
      >
        <div className="flex items-center">
          <span className="text-2xl mr-3">{strategy.icon}</span>
          <div className="flex-1">
            <div className="font-medium">{strategy.name}</div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-muted-foreground">{strategy.type}</span>
              <span className="text-xs px-1.5 py-0.5 bg-purple-500/20 text-purple-500 rounded">
                复合策略
              </span>
            </div>
          </div>
        </div>
      </button>
    );
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
                <span className="text-lg">📊</span>
                <CardTitle className="text-base">可用策略</CardTitle>
              </div>
              <CardDescription className="text-xs">
                选择回测策略
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {strategies.map(renderStrategyCard)}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-3 space-y-6">
          <div className="flex items-center justify-between p-5 bg-gradient-to-r from-card via-card to-purple-500/5 rounded-xl border shadow-sm">
            <div className="flex items-center gap-5">
              <div className="w-16 h-16 rounded-xl flex items-center justify-center text-3xl bg-purple-500/20">
                {currentStrategy.icon}
              </div>
              <div>
                <h2 className="text-2xl font-bold">{currentStrategy.name}</h2>
                <div className="flex items-center gap-2 mt-1">
                  <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                  <span className="text-sm text-purple-500 font-medium">多因子量化策略</span>
                  <span className="text-xs text-muted-foreground">综合多个因子进行选股择时</span>
                </div>
              </div>
            </div>
            <Button
              size="lg"
              onClick={handleRunBacktest}
              disabled={isRunning || (needsCustomEtfPool && selectedETFs.length === 0)}
              className="bg-purple-500 hover:bg-purple-600 shadow-lg"
            >
              {isRunning ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  回测运行中...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-5 w-5" />
                  开始回测
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
            <BacktestParams
              params={backtestParams}
              onChange={setBacktestParams}
              collapsible
              open={expandedParamCard === 'backtest'}
              onOpenChange={(open) => setExpandedParamCard(open ? 'backtest' : null)}
            />
            <StrategyParams
              strategy={currentStrategy}
              params={strategyParams}
              onChange={setStrategyParams}
              collapsible
              open={expandedParamCard === 'strategy'}
              onOpenChange={(open) => setExpandedParamCard(open ? 'strategy' : null)}
            />
          </div>

          {needsCustomEtfPool ? (
            <ETFSelector
              etfs={etfPool}
              selectedCodes={selectedETFs}
              onChange={setSelectedETFs}
            />
          ) : (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">标的配置</CardTitle>
                <CardDescription>
                  当前策略使用内置证券池，已自动按策略规则加载，不需要手动配置 ETF 池。
                </CardDescription>
              </CardHeader>
            </Card>
          )}

          {isRunning && (
            <Card className="border-primary/50 bg-gradient-to-r from-primary/5 to-transparent">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-primary" />
                  回测进度
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="w-full bg-secondary rounded-full h-4 overflow-hidden shadow-inner">
                  <div 
                    className="bg-gradient-to-r from-purple-500 to-purple-500/70 h-full rounded-full transition-all duration-300 ease-out flex items-center justify-end pr-2"
                    style={{ width: `${progress}%` }}
                  >
                    {progress > 10 && (
                      <span className="text-xs font-bold text-white">{progress}%</span>
                    )}
                  </div>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground flex items-center gap-2">
                    <span className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></span>
                    {progressText}
                  </span>
                  <span className="font-medium text-purple-500">{progress}%</span>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <span>📝</span>
                  回测日志
                  {isRunning && (
                    <span className="text-xs px-2 py-0.5 bg-purple-500/20 text-purple-500 rounded-full animate-pulse">
                      运行中
                    </span>
                  )}
                </CardTitle>
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
                className={`bg-gray-900 dark:bg-gray-950 rounded-lg p-4 font-mono text-sm overflow-y-auto transition-all duration-300 ${
                  isRunning ? 'h-80' : 'h-48'
                }`}
              >
                {logs.length === 0 ? (
                  <div className="text-gray-500 text-center py-8">
                    <div className="text-4xl mb-2">📊</div>
                    点击"开始回测"后，日志将显示在这里
                  </div>
                ) : (
                  logs.map((log, index) => (
                    <div key={index} className={`${getLogColor(log.level)} mb-1 leading-relaxed`}>
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
              <div className="flex justify-end">
                <Button variant="outline" size="lg" onClick={exportReport}>
                  <Download className="mr-2 h-5 w-5" />
                  📄 导出报告
                </Button>
              </div>
              <BacktestResults result={result} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
