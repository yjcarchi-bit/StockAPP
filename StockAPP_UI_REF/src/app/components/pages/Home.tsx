import React from 'react';
import { TrendingUp, BarChart3, FileText, Target } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';

interface HomeProps {
  onNavigate: (page: 'backtest' | 'compare' | 'optimization') => void;
}

export default function Home({ onNavigate }: HomeProps) {
  const features = [
    {
      icon: TrendingUp,
      title: '6种策略',
      description: '内置经典量化策略',
    },
    {
      icon: BarChart3,
      title: '专业回测',
      description: '完整交易模拟',
    },
    {
      icon: FileText,
      title: '详细报告',
      description: '多维度分析',
    },
  ];

  const marketData = [
    { name: '沪深300', change: '+1.2%', positive: true },
    { name: '上证50', change: '+0.8%', positive: true },
    { name: '中证500', change: '+1.5%', positive: true },
    { name: '创业板', change: '+2.1%', positive: true },
  ];

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-lg shadow-xl p-12 text-white">
        <div className="text-center">
          <h1 className="text-4xl md:text-5xl mb-4">欢迎使用 StockAPP</h1>
          <p className="text-xl md:text-2xl mb-8 text-blue-100">A股量化策略回测平台</p>
          <div className="flex flex-wrap justify-center gap-4">
            <Button
              size="lg"
              variant="secondary"
              onClick={() => onNavigate('backtest')}
              className="bg-white text-blue-600 hover:bg-blue-50"
            >
              <BarChart3 className="mr-2 h-5 w-5" />
              开始回测
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={() => onNavigate('compare')}
              className="border-white text-white hover:bg-white/10"
            >
              <Target className="mr-2 h-5 w-5" />
              策略对比
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={() => onNavigate('optimization')}
              className="border-white text-white hover:bg-white/10"
            >
              <TrendingUp className="mr-2 h-5 w-5" />
              参数优化
            </Button>
          </div>
        </div>
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {features.map((feature, index) => {
          const Icon = feature.icon;
          return (
            <Card key={index} className="text-center">
              <CardHeader>
                <div className="mx-auto w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                  <Icon className="h-6 w-6 text-blue-600" />
                </div>
                <CardTitle>{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>{feature.description}</CardDescription>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Market Overview */}
      <Card>
        <CardHeader>
          <CardTitle>市场概览</CardTitle>
          <CardDescription>主要指数实时行情</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {marketData.map((market, index) => (
              <div key={index} className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500">{market.name}</div>
                <div
                  className={`text-2xl mt-2 ${
                    market.positive ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {market.change}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Quick Info */}
      <Card>
        <CardHeader>
          <CardTitle>平台特色</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
              <span className="text-blue-600">1</span>
            </div>
            <div>
              <h3 className="font-medium">零代码操作</h3>
              <p className="text-sm text-gray-600">图形化界面，无需编程背景即可进行专业策略分析</p>
            </div>
          </div>
          <div className="flex items-start">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
              <span className="text-blue-600">2</span>
            </div>
            <div>
              <h3 className="font-medium">完整回测引擎</h3>
              <p className="text-sm text-gray-600">支持交易费用、滑点等真实市场因素模拟</p>
            </div>
          </div>
          <div className="flex items-start">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
              <span className="text-blue-600">3</span>
            </div>
            <div>
              <h3 className="font-medium">多维度分析</h3>
              <p className="text-sm text-gray-600">提供收益、风险、夏普比率等专业指标分析</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
