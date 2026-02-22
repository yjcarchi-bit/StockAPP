import React from 'react';
import type { MonthlyReturn } from '../../utils/backtestEngine';

interface MonthlyHeatmapProps {
  monthlyReturns: MonthlyReturn[];
}

export default function MonthlyHeatmap({ monthlyReturns }: MonthlyHeatmapProps) {
  // 组织数据为年份和月份的矩阵
  const years = [...new Set(monthlyReturns.map(r => r.year))].sort();
  const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];

  const getColor = (value: number) => {
    if (value > 5) return 'bg-green-600 text-white';
    if (value > 2) return 'bg-green-400 text-white';
    if (value > 0) return 'bg-green-200 text-green-900';
    if (value > -2) return 'bg-red-200 text-red-900';
    if (value > -5) return 'bg-red-400 text-white';
    return 'bg-red-600 text-white';
  };

  const getReturnForMonth = (year: number, month: number) => {
    const entry = monthlyReturns.find(r => r.year === year && r.month === month);
    return entry ? entry.return : null;
  };

  return (
    <div>
      <h3 className="text-lg font-medium mb-4">月度收益热力图</h3>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="p-2 text-left border bg-gray-50 font-medium text-sm">年份</th>
              {months.map((month, i) => (
                <th key={i} className="p-2 text-center border bg-gray-50 font-medium text-sm">
                  {month}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {years.map(year => (
              <tr key={year}>
                <td className="p-2 border bg-gray-50 font-medium text-sm">{year}</td>
                {Array.from({ length: 12 }, (_, i) => i + 1).map(month => {
                  const returnValue = getReturnForMonth(year, month);
                  return (
                    <td
                      key={month}
                      className={`p-2 text-center border ${
                        returnValue !== null ? getColor(returnValue) : 'bg-gray-100'
                      }`}
                    >
                      {returnValue !== null ? (
                        <div className="text-sm">
                          {returnValue > 0 ? '+' : ''}
                          {returnValue.toFixed(1)}%
                        </div>
                      ) : (
                        <div className="text-gray-400 text-sm">-</div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex items-center justify-center space-x-4 text-sm">
        <span className="text-gray-600">颜色:</span>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-red-600 rounded"></div>
          <span>负收益</span>
        </div>
        <span className="text-gray-400">←────────→</span>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-green-600 rounded"></div>
          <span>正收益</span>
        </div>
      </div>
    </div>
  );
}
