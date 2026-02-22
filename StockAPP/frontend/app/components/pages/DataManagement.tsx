import React, { useState } from 'react';
import { Download, Database, Calendar, FileText } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Progress } from '../ui/progress';
import { Badge } from '../ui/badge';

export default function DataManagement() {
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [isDownloading, setIsDownloading] = useState(false);

  const dataInfo = [
    { name: '沪深300ETF (510300)', status: '已缓存', lastUpdate: '2024-02-20', size: '2.3 MB' },
    { name: '中证500ETF (510500)', status: '已缓存', lastUpdate: '2024-02-20', size: '2.1 MB' },
    { name: '创业板ETF (159915)', status: '已缓存', lastUpdate: '2024-02-20', size: '1.8 MB' },
    { name: '黄金ETF (518880)', status: '已缓存', lastUpdate: '2024-02-20', size: '1.5 MB' },
    { name: '纳指ETF (513100)', status: '未缓存', lastUpdate: '-', size: '-' },
  ];

  const handleDownload = async () => {
    setIsDownloading(true);
    for (let i = 0; i <= 100; i += 10) {
      await new Promise(resolve => setTimeout(resolve, 200));
      setDownloadProgress(i);
    }
    setIsDownloading(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl mb-2 text-foreground">📦 数据管理</h1>
        <p className="text-muted-foreground">管理历史行情数据和缓存</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Database className="h-5 w-5" />
              <span>数据源</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">来源:</span>
                <span className="font-medium text-foreground">efinance</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">更新频率:</span>
                <span className="font-medium text-foreground">日级别</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">数据类型:</span>
                <span className="font-medium text-foreground">OHLCV</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Calendar className="h-5 w-5" />
              <span>覆盖范围</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">开始日期:</span>
                <span className="font-medium text-foreground">2020-01-01</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">结束日期:</span>
                <span className="font-medium text-foreground">2024-02-20</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">交易日数:</span>
                <span className="font-medium text-foreground">976 天</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <FileText className="h-5 w-5" />
              <span>缓存状态</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">已缓存:</span>
                <span className="font-medium text-green-500">4 个ETF</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">未缓存:</span>
                <span className="font-medium text-orange-500">1 个ETF</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">总大小:</span>
                <span className="font-medium text-foreground">7.7 MB</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>数据下载</CardTitle>
          <CardDescription>下载或更新历史行情数据</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-4 bg-primary/10 border border-primary/20 rounded-lg">
            <p className="text-sm text-foreground">
              💡 提示: 首次使用需要下载历史数据，之后会自动使用缓存数据。建议定期更新数据以保持最新。
            </p>
          </div>

          {isDownloading ? (
            <div>
              <Progress value={downloadProgress} className="w-full" />
              <p className="text-sm text-muted-foreground mt-2 text-center">
                正在下载数据... {downloadProgress}%
              </p>
            </div>
          ) : (
            <Button
              size="lg"
              onClick={handleDownload}
              className="w-full bg-primary hover:bg-primary/90"
            >
              <Download className="mr-2 h-5 w-5" />
              下载/更新所有数据
            </Button>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>数据缓存列表</CardTitle>
          <CardDescription>查看已缓存的数据详情</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {dataInfo.map((item, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-4 border border-border rounded-lg hover:bg-accent"
              >
                <div className="flex items-center space-x-4">
                  <Database className="h-8 w-8 text-muted-foreground" />
                  <div>
                    <div className="font-medium text-foreground">{item.name}</div>
                    <div className="text-sm text-muted-foreground">
                      最后更新: {item.lastUpdate} · 大小: {item.size}
                    </div>
                  </div>
                </div>
                <Badge
                  variant={item.status === '已缓存' ? 'default' : 'secondary'}
                  className={
                    item.status === '已缓存'
                      ? 'bg-green-500/10 text-green-500'
                      : 'bg-muted text-muted-foreground'
                  }
                >
                  {item.status}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>数据预览</CardTitle>
          <CardDescription>查看最近的行情数据</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted border-b">
                <tr>
                  <th className="p-3 text-left text-foreground">日期</th>
                  <th className="p-3 text-right text-foreground">开盘</th>
                  <th className="p-3 text-right text-foreground">最高</th>
                  <th className="p-3 text-right text-foreground">最低</th>
                  <th className="p-3 text-right text-foreground">收盘</th>
                  <th className="p-3 text-right text-foreground">成交量</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { date: '2024-02-20', open: 3.125, high: 3.156, low: 3.102, close: 3.145, volume: '1.2亿' },
                  { date: '2024-02-19', open: 3.098, high: 3.134, low: 3.089, close: 3.120, volume: '1.0亿' },
                  { date: '2024-02-18', open: 3.110, high: 3.128, low: 3.095, close: 3.102, volume: '0.9亿' },
                  { date: '2024-02-17', open: 3.095, high: 3.125, low: 3.087, close: 3.115, volume: '1.1亿' },
                  { date: '2024-02-16', open: 3.089, high: 3.102, low: 3.075, close: 3.092, volume: '0.8亿' },
                ].map((row, index) => (
                  <tr key={index} className="border-b hover:bg-muted/50">
                    <td className="p-3 font-mono text-foreground">{row.date}</td>
                    <td className="p-3 text-right font-mono text-foreground">{row.open}</td>
                    <td className="p-3 text-right font-mono text-red-500">{row.high}</td>
                    <td className="p-3 text-right font-mono text-green-500">{row.low}</td>
                    <td className="p-3 text-right font-mono text-foreground">{row.close}</td>
                    <td className="p-3 text-right text-muted-foreground">{row.volume}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
