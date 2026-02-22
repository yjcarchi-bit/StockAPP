import React, { useState } from 'react';
import { TrendingUp, BarChart3, Settings, Database, Target, Moon, Sun } from 'lucide-react';
import Home from './components/pages/Home';
import StrategyBacktest from './components/pages/StrategyBacktest';
import StrategyCompare from './components/pages/StrategyCompare';
import ParameterOptimization from './components/pages/ParameterOptimization';
import DataManagement from './components/pages/DataManagement';
import SettingsPage from './components/pages/SettingsPage';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import { usePersistentState } from './hooks';

type Page = 'home' | 'backtest' | 'compare' | 'optimization' | 'data' | 'settings';

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  
  return (
    <button
      onClick={toggleTheme}
      className="p-2 rounded-lg bg-secondary hover:bg-accent transition-colors"
      aria-label="切换主题"
    >
      {theme === 'light' ? (
        <Moon className="h-5 w-5 text-foreground" />
      ) : (
        <Sun className="h-5 w-5 text-foreground" />
      )}
    </button>
  );
}

function AppContent() {
  const [currentPage, setCurrentPage] = usePersistentState<Page>('current_page', 'home');

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
    <div className="min-h-screen bg-background text-foreground">
      <nav className="bg-card border-b border-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <div className="flex-shrink-0 flex items-center">
                <TrendingUp className="h-8 w-8 text-primary" />
                <span className="ml-2 text-xl font-bold text-foreground">StockAPP</span>
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
                          ? 'border-primary text-foreground'
                          : 'border-transparent text-muted-foreground hover:border-border hover:text-foreground'
                      }`}
                    >
                      <Icon className="h-4 w-4 mr-2" />
                      {item.label}
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="flex items-center">
              <ThemeToggle />
            </div>
          </div>
        </div>

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
                      ? 'bg-accent text-primary'
                      : 'text-muted-foreground hover:bg-accent hover:text-foreground'
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

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {renderPage()}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}
