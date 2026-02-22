import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Badge } from '../ui/badge';
import type { ETF } from '../../utils/strategyConfig';

interface ETFSelectorProps {
  etfs: ETF[];
  selectedCodes: string[];
  onChange: (codes: string[]) => void;
}

export default function ETFSelector({ etfs, selectedCodes, onChange }: ETFSelectorProps) {
  const toggleETF = (code: string) => {
    if (selectedCodes.includes(code)) {
      onChange(selectedCodes.filter(c => c !== code));
    } else {
      onChange([...selectedCodes, code]);
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case '商品': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case '海外': return 'bg-purple-100 text-purple-800 border-purple-300';
      case '宽基': return 'bg-blue-100 text-blue-800 border-blue-300';
      case '行业': return 'bg-green-100 text-green-800 border-green-300';
      case '货币': return 'bg-gray-100 text-gray-800 border-gray-300';
      default: return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>📋 ETF池配置</CardTitle>
        <CardDescription>
          已选择 {selectedCodes.length} 只ETF
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          {etfs.map(etf => {
            const isSelected = selectedCodes.includes(etf.code);
            return (
              <button
                key={etf.code}
                onClick={() => toggleETF(etf.code)}
                className={`px-4 py-2 rounded-lg border-2 transition-all ${
                  isSelected
                    ? 'bg-blue-50 border-blue-500 shadow-sm'
                    : 'bg-white border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                    isSelected ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                  }`}>
                    {isSelected && (
                      <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 12 12">
                        <path d="M10 3L4.5 8.5L2 6" stroke="currentColor" strokeWidth="2" fill="none" />
                      </svg>
                    )}
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-medium">{etf.name}</div>
                    <div className="text-xs text-gray-500">{etf.code}</div>
                  </div>
                  <Badge variant="outline" className={getTypeColor(etf.type)}>
                    {etf.type}
                  </Badge>
                </div>
              </button>
            );
          })}
        </div>

        {selectedCodes.length === 0 && (
          <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              ⚠️ 请至少选择一只ETF进行回测
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
