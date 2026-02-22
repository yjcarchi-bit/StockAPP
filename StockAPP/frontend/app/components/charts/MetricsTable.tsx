import React from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import type { BacktestResult } from '../../utils/backtestEngine';

interface MetricsTableProps {
  result: BacktestResult;
}

export default function MetricsTable({ result }: MetricsTableProps) {
  const formatNumber = (num: number, decimals: number = 2) => num.toFixed(decimals);
  const formatPercent = (num: number) => `${formatNumber(num)}%`;
  const formatCurrency = (num: number) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'CNY',
      minimumFractionDigits: 0,
    }).format(num);
  };

  const metricsGroups = [
    {
      title: '收益指标',
      metrics: [
        { label: '总收益率', value: formatPercent(result.totalReturn) },
        { label: '年化收益率', value: formatPercent(result.annualReturn) },
        { label: '最终资产', value: formatCurrency(result.finalAsset) },
      ],
    },
    {
      title: '风险指标',
      metrics: [
        { label: '最大回撤', value: formatPercent(result.maxDrawdown) },
        { label: '夏普比率', value: formatNumber(result.sharpeRatio) },
        { label: '索提诺比率', value: formatNumber(result.sortinoRatio) },
        { label: '卡玛比率', value: formatNumber(result.calmarRatio) },
      ],
    },
    {
      title: '交易指标',
      metrics: [
        { label: '总交易次数', value: result.totalTrades.toString() },
        { label: '胜率', value: formatPercent(result.winRate) },
        { label: '盈亏比', value: formatNumber(result.profitFactor) },
      ],
    },
  ];

  return (
    <div className="space-y-6">
      {metricsGroups.map((group, groupIndex) => (
        <div key={groupIndex}>
          <h3 className="text-lg font-medium mb-3">{group.title}</h3>
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-1/2">指标名称</TableHead>
                  <TableHead className="text-right">数值</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {group.metrics.map((metric, index) => (
                  <TableRow key={index}>
                    <TableCell className="font-medium">{metric.label}</TableCell>
                    <TableCell className="text-right font-mono">{metric.value}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      ))}

      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h4 className="font-medium text-blue-900 mb-2">📌 指标说明</h4>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• <strong>夏普比率</strong>: 衡量每单位风险获得的超额回报，大于1为优秀</li>
          <li>• <strong>索提诺比率</strong>: 类似夏普比率，但只考虑下行风险</li>
          <li>• <strong>卡玛比率</strong>: 年化收益与最大回撤的比值，越大越好</li>
          <li>• <strong>盈亏比</strong>: 平均盈利与平均亏损的比值，大于1表示盈利大于亏损</li>
        </ul>
      </div>
    </div>
  );
}
