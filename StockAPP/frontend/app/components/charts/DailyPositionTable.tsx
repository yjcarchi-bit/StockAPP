import React from 'react';
import { ScrollArea } from '../ui/scroll-area';
import type { DailyPosition } from '../../utils/backtestEngine';

interface DailyPositionTableProps {
  dailyPositions: DailyPosition[];
}

export default function DailyPositionTable({ dailyPositions }: DailyPositionTableProps) {
  const formatCurrency = (num: number) => {
    return new Intl.NumberFormat('zh-CN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  };

  const formatPercent = (num: number) => {
    const sign = num >= 0 ? '+' : '';
    return `${sign}${num.toFixed(2)}%`;
  };

  if (!dailyPositions || dailyPositions.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        暂无持仓数据
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="text-sm text-muted-foreground">
        共 {dailyPositions.length} 个交易日持仓记录
      </div>
      <div className="border rounded-lg overflow-hidden">
        <ScrollArea className="h-[500px]">
          <div className="divide-y">
            {dailyPositions.map((dayPosition, dayIndex) => (
              <div key={dayIndex} className="p-3 hover:bg-muted/30">
                <div className="font-medium text-sm mb-2 text-primary">
                  {dayPosition.date}
                </div>
                <table className="w-full text-xs">
                  <tbody>
                    {dayPosition.positions.map((pos, index) => (
                      <tr key={index} className="border-b border-muted/50 last:border-0">
                        <td className="py-1.5 pr-2">
                          <span className="font-medium">{pos.name || pos.code}</span>
                          <span className="text-muted-foreground ml-1">({pos.code})</span>
                        </td>
                        <td className="py-1.5 px-2 text-right">{pos.shares}股</td>
                        <td className="py-1.5 px-2 text-right font-mono">{pos.price.toFixed(3)}</td>
                        <td className="py-1.5 px-2 text-right font-mono">{formatCurrency(pos.marketValue)}</td>
                        <td className={`py-1.5 px-2 text-right font-mono ${pos.profit >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                          {formatCurrency(pos.profit)}
                        </td>
                        <td className={`py-1.5 px-2 text-right font-mono ${pos.dailyProfit >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                          {formatCurrency(pos.dailyProfit)}
                        </td>
                        <td className={`py-1.5 pl-2 text-right font-mono ${pos.profitPct >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                          {formatPercent(pos.profitPct)}
                        </td>
                      </tr>
                    ))}
                    <tr className="bg-muted/20">
                      <td className="py-1.5 pr-2 text-muted-foreground">Cash</td>
                      <td className="py-1.5 px-2 text-right text-muted-foreground">-</td>
                      <td className="py-1.5 px-2 text-right text-muted-foreground">-</td>
                      <td className="py-1.5 px-2 text-right font-mono">{formatCurrency(dayPosition.cash)}</td>
                      <td className="py-1.5 px-2 text-right text-muted-foreground">0.00</td>
                      <td className="py-1.5 px-2 text-right text-muted-foreground">0.00</td>
                      <td className="py-1.5 pl-2 text-right text-muted-foreground">-</td>
                    </tr>
                    <tr className="bg-primary/5 font-medium">
                      <td className="py-1.5 pr-2 text-muted-foreground">总计</td>
                      <td className="py-1.5 px-2 text-right text-muted-foreground">-</td>
                      <td className="py-1.5 px-2 text-right text-muted-foreground">-</td>
                      <td className="py-1.5 px-2 text-right font-mono font-bold">
                        总共:{formatCurrency(dayPosition.totalValue)}
                      </td>
                      <td className={`py-1.5 px-2 text-right font-mono font-bold ${dayPosition.totalProfit >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                        {formatCurrency(dayPosition.totalProfit)}
                      </td>
                      <td className={`py-1.5 px-2 text-right font-mono font-bold ${dayPosition.totalDailyProfit >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                        {formatCurrency(dayPosition.totalDailyProfit)}
                      </td>
                      <td className="py-1.5 pl-2 text-right text-muted-foreground">-</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
