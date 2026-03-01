import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Download, Database, Calendar, FileText, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Progress } from '../ui/progress';
import { Badge } from '../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { apiClient, type ApiUpdateStatus, type CacheInfo, type ETFDataResponse } from '../../utils/apiClient';
import { etfPool } from '../../utils/strategyConfig';

function dateToISO(date: Date): string {
  return date.toISOString().split('T')[0];
}

export default function DataManagement() {
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isMigrating, setIsMigrating] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedCode, setSelectedCode] = useState('510300');
  const [updateStatus, setUpdateStatus] = useState<ApiUpdateStatus | null>(null);
  const [cacheInfo, setCacheInfo] = useState<CacheInfo | null>(null);
  const [preview, setPreview] = useState<ETFDataResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const previewRange = useMemo(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 60);
    return {
      startDate: dateToISO(start),
      endDate: dateToISO(end),
    };
  }, []);

  const loadStatusAndCache = useCallback(async () => {
    setIsRefreshing(true);
    setError(null);
    try {
      const [status, cache] = await Promise.all([
        apiClient.getUpdateStatus(),
        apiClient.getCacheInfo(),
      ]);
      setUpdateStatus(status);
      setCacheInfo(cache);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载状态失败');
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  const loadPreview = useCallback(async () => {
    try {
      const data = await apiClient.getETFData(selectedCode, previewRange.startDate, previewRange.endDate);
      setPreview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载行情预览失败');
      setPreview(null);
    }
  }, [selectedCode, previewRange.endDate, previewRange.startDate]);

  useEffect(() => {
    void loadStatusAndCache();
  }, [loadStatusAndCache]);

  useEffect(() => {
    void loadPreview();
  }, [loadPreview]);

  const handleDownload = async () => {
    setIsDownloading(true);
    setDownloadProgress(10);
    setError(null);

    try {
      await apiClient.triggerUpdate();
      setDownloadProgress(60);
      await loadStatusAndCache();
      await loadPreview();
      setDownloadProgress(100);
    } catch (err) {
      setError(err instanceof Error ? err.message : '触发更新失败');
    } finally {
      setTimeout(() => {
        setIsDownloading(false);
        setDownloadProgress(0);
      }, 400);
    }
  };

  const handleMigratePkl = async () => {
    setIsMigrating(true);
    setError(null);
    try {
      await apiClient.triggerPklMigration();
      await loadStatusAndCache();
    } catch (err) {
      setError(err instanceof Error ? err.message : '触发PKL迁移失败');
    } finally {
      setIsMigrating(false);
    }
  };

  const latestRows = preview?.data?.slice(-5).reverse() || [];
  const cachedCount = cacheInfo?.file_count ?? 0;
  const totalSize = cacheInfo?.total_size_mb ?? 0;
  const symbolCount = cacheInfo?.symbol_count ?? 0;
  const rowCount = cacheInfo?.row_count ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl mb-2 text-foreground">📦 数据管理</h1>
        <p className="text-muted-foreground">管理历史行情数据和缓存</p>
      </div>

      {error && (
        <Card className="border-red-300 bg-red-50 dark:bg-red-900/20">
          <CardContent className="pt-6 text-sm text-red-700 dark:text-red-300">
            {error}
          </CardContent>
        </Card>
      )}

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
                <span className="text-muted-foreground">更新服务:</span>
                <span className={`font-medium ${updateStatus?.running ? 'text-green-600' : 'text-orange-600'}`}>
                  {updateStatus?.running ? '运行中' : '未运行'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">最后更新:</span>
                <span className="font-medium text-foreground">
                  {updateStatus?.last_update ? updateStatus.last_update.slice(0, 19).replace('T', ' ') : '-'}
                </span>
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
                <span className="font-medium text-foreground">{previewRange.startDate}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">结束日期:</span>
                <span className="font-medium text-foreground">{previewRange.endDate}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">可用记录:</span>
                <span className="font-medium text-foreground">{preview?.data?.length ?? 0} 条</span>
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
                <span className="text-muted-foreground">缓存文件:</span>
                <span className="font-medium text-foreground">{cachedCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">缓存大小:</span>
                <span className="font-medium text-foreground">{totalSize.toFixed(2)} MB</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">缓存目录:</span>
                <span className="font-medium text-foreground text-xs truncate max-w-[170px]">
                  {cacheInfo?.cache_dir ?? '-'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">存储后端:</span>
                <span className="font-medium text-foreground">{cacheInfo?.storage_backend ?? 'pkl'}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>数据下载</CardTitle>
          <CardDescription>触发后端数据更新任务</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-4 bg-primary/10 border border-primary/20 rounded-lg">
            <p className="text-sm text-foreground">
              更新会在后端后台执行。完成后请点击“刷新状态”查看缓存变化。
            </p>
          </div>

          {isDownloading ? (
            <div>
              <Progress value={downloadProgress} className="w-full" />
              <p className="text-sm text-muted-foreground mt-2 text-center">
                正在触发更新... {downloadProgress}%
              </p>
            </div>
          ) : (
            <div className="flex gap-3">
              <Button
                size="lg"
                onClick={handleDownload}
                className="flex-1 bg-primary hover:bg-primary/90"
              >
                <Download className="mr-2 h-5 w-5" />
                触发数据更新
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={() => void loadStatusAndCache()}
                disabled={isRefreshing}
              >
                {isRefreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : '刷新状态'}
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={handleMigratePkl}
                disabled={isMigrating}
              >
                {isMigrating ? <Loader2 className="h-4 w-4 animate-spin" /> : '迁移PKL到MySQL'}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>数据缓存列表</CardTitle>
          <CardDescription>更新任务配置与缓存快照</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-4 border border-border rounded-lg hover:bg-accent">
              <div className="flex items-center space-x-4">
                <Database className="h-8 w-8 text-muted-foreground" />
                <div>
                  <div className="font-medium text-foreground">ETF更新清单</div>
                  <div className="text-sm text-muted-foreground">
                    当前计划更新 {updateStatus?.etf_codes_count ?? 0} 个 ETF
                  </div>
                </div>
              </div>
              <Badge variant="outline" className="bg-blue-100 text-blue-700 border-blue-300">
                活跃
              </Badge>
            </div>

            <div className="flex items-center justify-between p-4 border border-border rounded-lg hover:bg-accent">
              <div className="flex items-center space-x-4">
                <FileText className="h-8 w-8 text-muted-foreground" />
                <div>
                  <div className="font-medium text-foreground">缓存文件</div>
                  <div className="text-sm text-muted-foreground">
                    共 {cachedCount} 个缓存文件，约 {totalSize.toFixed(2)} MB
                  </div>
                  <div className="text-sm text-muted-foreground">
                    MySQL已入库 {symbolCount} 个标的 / {rowCount.toLocaleString()} 条日线
                  </div>
                  <div className="text-sm text-muted-foreground">
                    最近同步: {cacheInfo?.last_sync_at ? cacheInfo.last_sync_at.slice(0, 19).replace('T', ' ') : '-'}
                  </div>
                </div>
              </div>
              <Badge
                variant={cachedCount > 0 ? 'default' : 'secondary'}
                className={cachedCount > 0 ? 'bg-green-100 text-green-700 border-green-300' : ''}
              >
                {cachedCount > 0 ? '已缓存' : '空'}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>数据预览</CardTitle>
          <CardDescription>查看最近行情数据（按 ETF 选择）</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="max-w-sm">
            <Select value={selectedCode} onValueChange={setSelectedCode}>
              <SelectTrigger>
                <SelectValue placeholder="选择ETF代码" />
              </SelectTrigger>
              <SelectContent>
                {etfPool.map((etf) => (
                  <SelectItem key={etf.code} value={etf.code}>
                    {etf.code} - {etf.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

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
                {latestRows.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-muted-foreground">
                      暂无可展示数据
                    </td>
                  </tr>
                ) : (
                  latestRows.map((row, index) => (
                    <tr key={index} className="border-b hover:bg-muted/50">
                      <td className="p-3 font-mono text-foreground">{row.date}</td>
                      <td className="p-3 text-right font-mono text-foreground">{row.open.toFixed(3)}</td>
                      <td className="p-3 text-right font-mono text-red-500">{row.high.toFixed(3)}</td>
                      <td className="p-3 text-right font-mono text-green-500">{row.low.toFixed(3)}</td>
                      <td className="p-3 text-right font-mono text-foreground">{row.close.toFixed(3)}</td>
                      <td className="p-3 text-right text-muted-foreground">{row.volume.toLocaleString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
