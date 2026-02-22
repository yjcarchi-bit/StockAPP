import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Badge } from '../ui/badge';
import type { DailySelectionResult, StockScoreDetail, TradeDecision } from '../../utils/backtestRunner';
import { TrendingUp, TrendingDown, AlertTriangle, Lock, Unlock, ShoppingCart, Banknote } from 'lucide-react';
import ScoreRadarChart from './ScoreRadarChart';

interface BacktestProgressProps {
  currentIndex: number;
  totalDays: number;
  currentDate: string;
  percent: number;
  dailyResult: DailySelectionResult | null;
}

const factorNames: Record<string, string> = {
  momentum5: '5日动量',
  momentum20: '20日动量',
  trendStrength: '趋势强度',
  volumeRatio: '量比因子',
  volatility: '波动率',
  marketCap: '市值因子',
};

const factorMaxScores: Record<string, number> = {
  momentum5: 25,
  momentum20: 20,
  trendStrength: 25,
  volumeRatio: 10,
  volatility: 10,
  marketCap: 10,
};

function getMarketStatusBadge(status: DailySelectionResult['marketStatus']) {
  switch (status) {
    case 'normal':
      return (
        <Badge variant="default" className="bg-green-500 hover:bg-green-600">
          <TrendingUp className="w-3 h-3 mr-1" />
          正常交易
        </Badge>
      );
    case 'drawdown_lock':
      return (
        <Badge variant="destructive" className="bg-red-500 hover:bg-red-600">
          <Lock className="w-3 h-3 mr-1" />
          回撤锁定
        </Badge>
      );
    case 'partial_unlock':
      return (
        <Badge variant="outline" className="border-yellow-500 text-yellow-600">
          <Unlock className="w-3 h-3 mr-1" />
          部分解锁
        </Badge>
      );
  }
}

function getTradeActionBadge(action: TradeDecision['action']) {
  switch (action) {
    case 'buy':
      return (
        <Badge variant="default" className="bg-green-500 hover:bg-green-600">
          <TrendingUp className="w-3 h-3 mr-1" />
          买入
        </Badge>
      );
    case 'sell':
      return (
        <Badge variant="destructive" className="bg-red-500 hover:bg-red-600">
          <TrendingDown className="w-3 h-3 mr-1" />
          卖出
        </Badge>
      );
    case 'hold':
      return (
        <Badge variant="outline">
          持有
        </Badge>
      );
  }
}

function ScoreBar({ score, maxScore, label }: { score: number; maxScore: number; label: string }) {
  const percentage = (score / maxScore) * 100;
  const colorClass = percentage >= 80 ? 'bg-green-500' : percentage >= 50 ? 'bg-yellow-500' : 'bg-gray-300';
  
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-16 text-muted-foreground truncate">{label}</span>
      <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
        <div 
          className={`h-full ${colorClass} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="w-8 text-right font-mono">{score}/{maxScore}</span>
    </div>
  );
}

function StockScoreRow({ detail, rank }: { detail: StockScoreDetail; rank: number }) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  
  return (
    <div className="border-b last:border-b-0">
      <div 
        className="flex items-center gap-3 p-2 hover:bg-muted/50 cursor-pointer transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="w-8 text-center">
          {detail.isSelected ? (
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs font-bold">
              {rank}
            </span>
          ) : (
            <span className="text-muted-foreground text-sm">{rank}</span>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium truncate">{detail.name}</span>
            <span className="text-xs text-muted-foreground">{detail.code}</span>
            {detail.isSelected && (
              <Badge variant="outline" className="text-xs bg-green-50 border-green-200 text-green-700">
                已选
              </Badge>
            )}
          </div>
        </div>
        <div className="text-right">
          <div className="font-bold text-lg">{detail.totalScore}</div>
          <div className="text-xs text-muted-foreground">总分</div>
        </div>
      </div>
      
      {isExpanded && (
        <div className="px-4 pb-3 pt-1 bg-muted/30">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <ScoreRadarChart scores={detail.scores} size={140} />
            </div>
            <div className="flex-1 space-y-1.5 pt-2">
              {Object.entries(detail.scores).map(([key, value]) => (
                <ScoreBar 
                  key={key} 
                  score={value} 
                  maxScore={factorMaxScores[key]} 
                  label={factorNames[key]} 
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function BacktestProgress({
  currentIndex,
  totalDays,
  currentDate,
  percent,
  dailyResult,
}: BacktestProgressProps) {
  if (!dailyResult) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-500" />
            回测进度
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="w-full bg-secondary rounded-full h-3 overflow-hidden">
              <div 
                className="bg-primary h-full rounded-full transition-all duration-300 ease-out"
                style={{ width: `${percent}%` }}
              />
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">正在初始化...</span>
              <span className="font-medium">{percent}%</span>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              回测进度
            </CardTitle>
            {getMarketStatusBadge(dailyResult.marketStatus)}
          </div>
          <CardDescription>
            当前处理日期: {currentDate}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="w-full bg-secondary rounded-full h-3 overflow-hidden">
            <div 
              className="bg-primary h-full rounded-full transition-all duration-300 ease-out"
              style={{ width: `${percent}%` }}
            />
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">
              {currentIndex} / {totalDays} 交易日
            </span>
            <span className="font-medium">{percent}%</span>
          </div>
          
          <div className="grid grid-cols-3 gap-3 pt-2">
            <div className="text-center p-2 bg-muted/50 rounded-lg">
              <div className="text-lg font-bold text-primary">
                ¥{dailyResult.portfolioValue.toLocaleString()}
              </div>
              <div className="text-xs text-muted-foreground">组合市值</div>
            </div>
            <div className="text-center p-2 bg-muted/50 rounded-lg">
              <div className={`text-lg font-bold ${dailyResult.drawdown > 5 ? 'text-red-500' : 'text-green-500'}`}>
                {dailyResult.drawdown.toFixed(2)}%
              </div>
              <div className="text-xs text-muted-foreground">当前回撤</div>
            </div>
            <div className="text-center p-2 bg-muted/50 rounded-lg">
              <div className="text-lg font-bold text-blue-500">
                {dailyResult.cashRatio.toFixed(1)}%
              </div>
              <div className="text-xs text-muted-foreground">现金比例</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {dailyResult.trades.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <ShoppingCart className="w-4 h-4 text-blue-500" />
              当日调仓决策
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {dailyResult.trades.map((trade, index) => (
                <div 
                  key={index}
                  className="flex items-center gap-3 p-2 bg-muted/30 rounded-lg"
                >
                  {getTradeActionBadge(trade.action)}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{trade.name}</span>
                      <span className="text-xs text-muted-foreground">{trade.code}</span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {trade.reason}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Banknote className="w-4 h-4 text-green-500" />
            候选股票打分排名
          </CardTitle>
          <CardDescription>
            点击展开查看六因子详情 (共 {dailyResult.candidates.length} 只候选)
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {dailyResult.candidates.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">
              暂无符合条件的候选股票
            </div>
          ) : (
            <div className="max-h-80 overflow-y-auto">
              {dailyResult.candidates.map((detail, index) => (
                <StockScoreRow 
                  key={detail.code} 
                  detail={detail} 
                  rank={index + 1} 
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
