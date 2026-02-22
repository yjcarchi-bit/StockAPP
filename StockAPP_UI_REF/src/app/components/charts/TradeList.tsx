import React from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import type { Trade } from '../../utils/backtestEngine';

interface TradeListProps {
  trades: Trade[];
}

export default function TradeList({ trades }: TradeListProps) {
  const formatCurrency = (num: number) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'CNY',
      minimumFractionDigits: 2,
    }).format(num);
  };

  return (
    <div>
      <div className="mb-4 text-sm text-gray-600">
        共 {trades.length} 条交易记录
      </div>
      <div className="border rounded-lg overflow-hidden">
        <div className="max-h-96 overflow-y-auto">
          <Table>
            <TableHeader className="sticky top-0 bg-gray-50">
              <TableRow>
                <TableHead>日期</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>代码</TableHead>
                <TableHead className="text-right">价格</TableHead>
                <TableHead className="text-right">数量</TableHead>
                <TableHead className="text-right">金额</TableHead>
                <TableHead className="text-right">手续费</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {trades.map((trade, index) => (
                <TableRow key={index}>
                  <TableCell className="font-mono text-sm">{trade.date}</TableCell>
                  <TableCell>
                    <Badge
                      variant={trade.type === 'buy' ? 'default' : 'secondary'}
                      className={
                        trade.type === 'buy'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-green-100 text-green-700'
                      }
                    >
                      {trade.type === 'buy' ? '买入' : '卖出'}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono">{trade.code}</TableCell>
                  <TableCell className="text-right font-mono">
                    {trade.price.toFixed(3)}
                  </TableCell>
                  <TableCell className="text-right">{trade.shares}</TableCell>
                  <TableCell className="text-right font-mono">
                    {formatCurrency(trade.amount)}
                  </TableCell>
                  <TableCell className="text-right text-gray-500 font-mono">
                    {formatCurrency(trade.commission)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
