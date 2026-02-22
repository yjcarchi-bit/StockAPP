import React from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import type { Trade } from '../../utils/backtestEngine';

interface TradeListProps {
  trades: Trade[];
}

export default function TradeList({ trades }: TradeListProps) {
  const formatCurrency = (num: number) => {
    if (num >= 10000) {
      return `¥${(num / 10000).toFixed(2)}万`;
    }
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'CNY',
      minimumFractionDigits: 2,
    }).format(num);
  };

  return (
    <div>
      <div className="mb-4 text-sm text-muted-foreground">
        共 {trades.length} 条交易记录
      </div>
      <div className="border rounded-lg overflow-hidden">
        <ScrollArea className="h-[400px]">
          <Table>
            <TableHeader className="sticky top-0 bg-muted/50 backdrop-blur">
              <TableRow>
                <TableHead className="text-xs">日期</TableHead>
                <TableHead className="text-xs">类型</TableHead>
                <TableHead className="text-xs">代码</TableHead>
                <TableHead className="text-xs">名称</TableHead>
                <TableHead className="text-xs text-right">价格</TableHead>
                <TableHead className="text-xs text-right">数量</TableHead>
                <TableHead className="text-xs text-right">金额</TableHead>
                <TableHead className="text-xs text-right">手续费</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {trades.map((trade, index) => (
                <TableRow key={index}>
                  <TableCell className="font-mono text-xs">{trade.date}</TableCell>
                  <TableCell>
                    <Badge
                      variant={trade.type === 'buy' ? 'default' : 'secondary'}
                      className={
                        trade.type === 'buy'
                          ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                          : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      }
                    >
                      {trade.type === 'buy' ? '买入' : '卖出'}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{trade.code}</TableCell>
                  <TableCell className="text-xs">{trade.name || trade.code}</TableCell>
                  <TableCell className="text-right font-mono text-xs">
                    {trade.price.toFixed(3)}
                  </TableCell>
                  <TableCell className="text-right text-xs">{trade.shares}</TableCell>
                  <TableCell className="text-right font-mono text-xs">
                    {formatCurrency(trade.amount)}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground font-mono text-xs">
                    {formatCurrency(trade.commission)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ScrollArea>
      </div>
    </div>
  );
}
