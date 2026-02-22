import React, { useState } from 'react';
import { TrendingUp, BarChart3, Settings, Database, Target } from 'lucide-react';
import Home from './components/pages/Home';
import StrategyBacktest from './components/pages/StrategyBacktest';
import StrategyCompare from './components/pages/StrategyCompare';
import ParameterOptimization from './components/pages/ParameterOptimization';
import DataManagement from './components/pages/DataManagement';
import SettingsPage from './components/pages/SettingsPage';

type Page = 'home' | 'backtest' | 'compare' | 'optimization' | 'data' | 'settings';

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>('home');

  const navItems = [
    { id: 'home' as Page, label: '首页', icon: TrendingUp },
    { id: 'backtest' as Page, label: '策略回测', icon: BarChart3 },
    { id: 'compare' as Page, label: '策略对比', icon: Target },
    { id: 'optimization' as Page, label: '参数优化', icon: Settings },
    { id: 'data' as Page, label: '数据管理', icon: Database },
    { id: 'settings' as Page, label: '设置', icon: Settings },
  ];

  const renderPage = () => {
    switch (currentPage) {
      case 'home':
        return <Home onNavigate={setCurrentPage} />;
      case 'backtest':
        return <StrategyBacktest />;
      case 'compare':
        return <StrategyCompare />;
      case 'optimization':
        return <ParameterOptimization />;
      case 'data':
        return <DataManagement />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <Home onNavigate={setCurrentPage} />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航栏 */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <div className="flex-shrink-0 flex items-center">
                <TrendingUp className="h-8 w-8 text-blue-600" />
                <span className="ml-2 text-xl font-bold text-gray-900">StockAPP</span>
              </div>
              <div className="hidden md:ml-10 md:flex md:space-x-8">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.id}
                      onClick={() => setCurrentPage(item.id)}
                      className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors ${
                        currentPage === item.id
                          ? 'border-blue-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`}
                    >
                      <Icon className="h-4 w-4 mr-2" />
                      {item.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* 移动端导航 */}
        <div className="md:hidden">
          <div className="px-2 pt-2 pb-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => setCurrentPage(item.id)}
                  className={`w-full flex items-center px-3 py-2 rounded-md text-base font-medium ${
                    currentPage === item.id
                      ? 'bg-blue-50 text-blue-600'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <Icon className="h-5 w-5 mr-3" />
                  {item.label}
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* 主内容区域 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {renderPage()}
      </main>
    </div>
  );
}
