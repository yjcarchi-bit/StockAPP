import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import type { ComparisonDataPoint } from '../../hooks/useComparePage';

interface CompareHighlightsProps {
  bestReturn: ComparisonDataPoint | null;
  bestSharpe: ComparisonDataPoint | null;
  minDrawdown: ComparisonDataPoint | null;
}

export default function CompareHighlights({
  bestReturn,
  bestSharpe,
  minDrawdown,
}: CompareHighlightsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card className="bg-gradient-to-br from-green-500/10 to-green-500/20">
        <CardHeader>
          <CardTitle className="text-lg">🏆 最高收益</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-green-600">{bestReturn?.name}</div>
          <div className="text-green-500">{bestReturn ? `${bestReturn.总收益率.toFixed(2)}%` : '0.00%'}</div>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-blue-500/10 to-blue-500/20">
        <CardHeader>
          <CardTitle className="text-lg">📈 最高夏普</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-blue-600">{bestSharpe?.name}</div>
          <div className="text-blue-500">{bestSharpe ? bestSharpe.夏普比率.toFixed(2) : '0.00'}</div>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-orange-500/10 to-orange-500/20">
        <CardHeader>
          <CardTitle className="text-lg">🛡️ 最小回撤</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-orange-600">{minDrawdown?.name}</div>
          <div className="text-orange-500">{minDrawdown ? `${minDrawdown.最大回撤.toFixed(2)}%` : '0.00%'}</div>
        </CardContent>
      </Card>
    </div>
  );
}
