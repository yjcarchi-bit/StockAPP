import React from 'react';
import { ScrollArea } from '../ui/scroll-area';
import type { MonthlyReturn } from '../../utils/backtestEngine';

interface MonthlyHeatmapProps {
  monthlyReturns: MonthlyReturn[];
}

export default function MonthlyHeatmap({ monthlyReturns }: MonthlyHeatmapProps) {
  const years = [...new Set(monthlyReturns.map(r => r.year))].sort();
  const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];

  const getColor = (value: number) => {
    if (value > 5) return 'bg-green-600 text-white dark:bg-green-500';
    if (value > 2) return 'bg-green-400 text-white dark:bg-green-600';
    if (value > 0) return 'bg-green-200 text-green-900 dark:bg-green-900/50 dark:text-green-300';
    if (value > -2) return 'bg-red-200 text-red-900 dark:bg-red-900/50 dark:text-red-300';
    if (value > -5) return 'bg-red-400 text-white dark:bg-red-700';
    return 'bg-red-600 text-white dark:bg-red-500';
  };

  const getReturnForMonth = (year: number, month: number) => {
    const entry = monthlyReturns.find(r => r.year === year && r.month === month);
    return entry ? entry.return : null;
  };

  return (
    <div>
      <h3 className="text-lg font-medium mb-4">月度收益热力图</h3>
      <ScrollArea className="w-full">
        <div className="min-w-[600px]">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="p-2 text-left border bg-muted/50 font-medium text-xs">年份</th>
                {months.map((month, i) => (
                  <th key={i} className="p-1.5 text-center border bg-muted/50 font-medium text-xs whitespace-nowrap">
                    {month}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {years.map(year => (
                <tr key={year}>
                  <td className="p-2 border bg-muted/50 font-medium text-xs">{year}</td>
                  {Array.from({ length: 12 }, (_, i) => i + 1).map(month => {
                    const returnValue = getReturnForMonth(year, month);
                    return (
                      <td
                        key={month}
                        className={`p-1.5 text-center border text-xs ${
                          returnValue !== null ? getColor(returnValue) : 'bg-muted/30'
                        }`}
                      >
                        {returnValue !== null ? (
                          <div className="whitespace-nowrap">
                            {returnValue > 0 ? '+' : ''}
                            {returnValue.toFixed(1)}%
                          </div>
                        ) : (
                          <div className="text-muted-foreground">-</div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ScrollArea>

      <div className="mt-4 flex flex-wrap items-center justify-center gap-3 text-xs">
        <span className="text-muted-foreground">颜色:</span>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-red-600 rounded"></div>
          <span>&lt;-5%</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-red-200 rounded"></div>
          <span>-2%~0</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-green-200 rounded"></div>
          <span>0~2%</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-green-600 rounded"></div>
          <span>&gt;5%</span>
        </div>
      </div>
    </div>
  );
}
