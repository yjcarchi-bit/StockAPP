import React, { useState, useCallback } from 'react';
import { Search, X, Plus, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Badge } from '../ui/badge';

interface Stock {
  code: string;
  name: string;
  market?: string;
  industry?: string;
}

interface StockSelectorProps {
  selectedStocks: Stock[];
  onChange: (stocks: Stock[]) => void;
  maxStocks?: number;
}

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export default function StockSelector({ selectedStocks, onChange, maxStocks = 10 }: StockSelectorProps) {
  const [searchKeyword, setSearchKeyword] = useState('');
  const [searchResults, setSearchResults] = useState<Stock[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);

  const searchStocks = useCallback(async (keyword: string) => {
    if (!keyword.trim()) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    try {
      const response = await fetch(
        `${API_BASE}/data/stock/search?keyword=${encodeURIComponent(keyword)}&limit=20`
      );
      if (response.ok) {
        const data = await response.json();
        setSearchResults(data);
      } else {
        setSearchResults([]);
      }
    } catch (error) {
      console.error('搜索股票失败:', error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchKeyword(value);
    setShowResults(true);
    
    const timer = setTimeout(() => {
      searchStocks(value);
    }, 300);

    return () => clearTimeout(timer);
  };

  const addStock = (stock: Stock) => {
    if (selectedStocks.length >= maxStocks) {
      return;
    }
    if (!selectedStocks.find(s => s.code === stock.code)) {
      onChange([...selectedStocks, stock]);
    }
    setSearchKeyword('');
    setSearchResults([]);
    setShowResults(false);
  };

  const removeStock = (code: string) => {
    onChange(selectedStocks.filter(s => s.code !== code));
  };

  const getMarketColor = (market?: string) => {
    if (market === 'SH') return 'bg-red-100 text-red-700 border-red-300';
    if (market === 'SZ') return 'bg-blue-100 text-blue-700 border-blue-300';
    return 'bg-gray-100 text-gray-700 border-gray-300';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>📈 股票选择</CardTitle>
        <CardDescription>
          搜索并选择要回测的股票（最多 {maxStocks} 只，已选 {selectedStocks.length} 只）
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {selectedStocks.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {selectedStocks.map(stock => (
              <div
                key={stock.code}
                className="flex items-center gap-2 px-3 py-1.5 bg-primary/10 border border-primary/30 rounded-lg"
              >
                <span className="text-sm font-medium">{stock.name}</span>
                <span className="text-xs text-muted-foreground">{stock.code}</span>
                {stock.market && (
                  <Badge variant="outline" className={getMarketColor(stock.market)}>
                    {stock.market}
                  </Badge>
                )}
                <button
                  onClick={() => removeStock(stock.code)}
                  className="ml-1 p-0.5 hover:bg-primary/20 rounded-full transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="relative">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              value={searchKeyword}
              onChange={handleSearchChange}
              onFocus={() => setShowResults(true)}
              placeholder="输入股票代码或名称搜索..."
              className="w-full pl-10 pr-4 py-2.5 border border-input rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            {isSearching && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-muted-foreground" />
            )}
          </div>

          {showResults && searchResults.length > 0 && (
            <div className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto">
              {searchResults.map(stock => {
                const isSelected = selectedStocks.find(s => s.code === stock.code);
                return (
                  <button
                    key={stock.code}
                    onClick={() => addStock(stock)}
                    disabled={isSelected !== undefined || selectedStocks.length >= maxStocks}
                    className={`w-full flex items-center justify-between px-4 py-2.5 hover:bg-accent transition-colors ${
                      isSelected ? 'opacity-50 cursor-not-allowed' : ''
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="text-left">
                        <div className="font-medium">{stock.name}</div>
                        <div className="text-xs text-muted-foreground">{stock.code}</div>
                      </div>
                      {stock.market && (
                        <Badge variant="outline" className={getMarketColor(stock.market)}>
                          {stock.market}
                        </Badge>
                      )}
                      {stock.industry && (
                        <Badge variant="outline" className="bg-gray-100 text-gray-600 border-gray-300">
                          {stock.industry}
                        </Badge>
                      )}
                    </div>
                    {isSelected ? (
                      <Badge variant="outline" className="bg-green-100 text-green-700 border-green-300">
                        已选择
                      </Badge>
                    ) : (
                      <Plus className="w-4 h-4 text-muted-foreground" />
                    )}
                  </button>
                );
              })}
            </div>
          )}

          {showResults && searchKeyword && searchResults.length === 0 && !isSearching && (
            <div className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-lg p-4 text-center text-muted-foreground">
              未找到匹配的股票
            </div>
          )}
        </div>

        {selectedStocks.length === 0 && (
          <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              ⚠️ 请搜索并选择至少一只股票进行回测
            </p>
          </div>
        )}

        {selectedStocks.length >= maxStocks && (
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              ℹ️ 已达到最大选择数量（{maxStocks}只）
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
