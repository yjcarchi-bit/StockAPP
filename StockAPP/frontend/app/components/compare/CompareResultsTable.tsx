import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import type { ComparisonDataPoint } from '../../hooks/useComparePage';

interface CompareResultsTableProps {
  comparisonData: ComparisonDataPoint[];
}

export default function CompareResultsTable({ comparisonData }: CompareResultsTableProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>📊 对比结果</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted">
                <th className="p-3 text-left font-medium text-foreground">策略</th>
                <th className="p-3 text-right font-medium text-foreground">总收益率</th>
                <th className="p-3 text-right font-medium text-foreground">年化收益</th>
                <th className="p-3 text-right font-medium text-foreground">最大回撤</th>
                <th className="p-3 text-right font-medium text-foreground">夏普比率</th>
              </tr>
            </thead>
            <tbody>
              {comparisonData.map((data, index) => (
                <tr key={index} className="border-b hover:bg-muted/50">
                  <td className="p-3 font-medium text-foreground">{data.name}</td>
                  <td className={`p-3 text-right ${data.总收益率 > 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {data.总收益率.toFixed(2)}%
                  </td>
                  <td className={`p-3 text-right ${data.年化收益 > 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {data.年化收益.toFixed(2)}%
                  </td>
                  <td className="p-3 text-right text-red-500">{data.最大回撤.toFixed(2)}%</td>
                  <td className={`p-3 text-right ${data.夏普比率 > 1 ? 'text-green-500' : 'text-orange-500'}`}>
                    {data.夏普比率.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
