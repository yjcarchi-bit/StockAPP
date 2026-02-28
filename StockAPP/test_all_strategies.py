#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略测试脚本
测试所有策略
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from core.backtest_engine import BacktestEngine, BacktestConfig
from core.data_source import DataSource

from strategies.simple.bollinger_strategy import BollingerStrategy
from strategies.simple.dual_ma import DualMAStrategy
from strategies.simple.rsi_strategy import RSIStrategy
from strategies.simple.macd_strategy import MACDStrategy
from strategies.simple.grid_strategy import GridTradingStrategy
from strategies.multi_factor.etf_rotation import ETFRotationStrategy
from strategies.multi_factor.large_cap_low_drawdown import LargeCapLowDrawdownStrategy


def get_test_data(data_source, start_date, end_date):
    """获取测试数据"""
    data = {}
    
    print("正在加载ETF数据...")
    etf_codes = [
        "518880", "513100", "513520", "159915", "510300",
        "510500", "512880", "512690", "511090", "159985"
    ]
    
    for code in etf_codes:
        df = data_source.get_etf_history(code, start_date - timedelta(days=100), end_date)
        if df is not None and len(df) > 0:
            data[code] = df
    
    print(f"  加载ETF数据: {len(data)} 只")
    
    print("正在加载股票数据...")
    stock_codes = [
        "600519", "601318", "600036", "601166", "600887",
        "601398", "600030", "601288", "600276", "600000"
    ]
    
    stock_count = 0
    for code in stock_codes:
        df = data_source.get_stock_history(code, start_date - timedelta(days=100), end_date)
        if df is not None and len(df) > 0:
            data[code] = df
            stock_count += 1
    
    print(f"  加载股票数据: {stock_count} 只")
    
    return data


def test_strategy(strategy_class, strategy_name, data, start_date, end_date, params=None):
    """测试单个策略"""
    print(f"\n{'='*60}")
    print(f"测试策略: {strategy_name}")
    print(f"{'='*60}")
    
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000.0,
        commission_rate=0.0003,
        stamp_duty=0.001,
        min_commission=5.0,
    )
    
    data_source = DataSource()
    engine = BacktestEngine(config, data_source)
    
    for code, df in data.items():
        engine.add_data(code, df)
    
    strategy = strategy_class()
    if params:
        strategy.set_params(params)
    
    engine.add_strategy(strategy)
    
    try:
        result = engine.run(show_progress=False)
        
        if result.metrics:
            print(f"  总收益率: {result.metrics.get('total_return', 0):.2f}%")
            print(f"  年化收益率: {result.metrics.get('annual_return', 0):.2f}%")
            print(f"  最大回撤: {result.metrics.get('max_drawdown', 0):.2f}%")
            print(f"  夏普比率: {result.metrics.get('sharpe_ratio', 0):.2f}")
            print(f"  交易次数: {result.metrics.get('total_trades', 0)}")
            print(f"  胜率: {result.metrics.get('win_rate', 0):.2f}%")
        
        return result
        
    except Exception as e:
        print(f"  测试出错: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("="*60)
    print("策略测试 - 测试所有策略")
    print("="*60)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print(f"\n回测区间: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    data_source = DataSource()
    data = get_test_data(data_source, start_date, end_date)
    
    if not data:
        print("错误: 没有加载到任何数据")
        return
    
    results = {}
    
    simple_strategies = [
        (BollingerStrategy, "布林带策略", {"period": 20, "std_dev": 2}),
        (DualMAStrategy, "双均线策略", {"fast_period": 10, "slow_period": 30}),
        (RSIStrategy, "RSI策略", {"rsi_period": 14, "oversold": 30, "overbought": 70}),
        (MACDStrategy, "MACD策略", {"fast_period": 12, "slow_period": 26, "signal_period": 9}),
        (GridTradingStrategy, "网格交易策略", {"grid_num": 10, "grid_range_pct": 0.2}),
    ]
    
    print("\n" + "="*60)
    print("测试简单策略")
    print("="*60)
    
    for strategy_class, name, params in simple_strategies:
        result = test_strategy(strategy_class, name, data, start_date, end_date, params)
        if result:
            results[name] = result.metrics
    
    multi_factor_strategies = [
        (ETFRotationStrategy, "ETF轮动策略", {"lookback_days": 25, "holdings_num": 1}),
        (LargeCapLowDrawdownStrategy, "大市值低回撤策略", {"max_positions": 3}),
    ]
    
    print("\n" + "="*60)
    print("测试多因子策略")
    print("="*60)
    
    for strategy_class, name, params in multi_factor_strategies:
        result = test_strategy(strategy_class, name, data, start_date, end_date, params)
        if result:
            results[name] = result.metrics
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    print(f"\n{'策略名称':<20} {'总收益率':>10} {'年化收益':>10} {'最大回撤':>10} {'夏普比率':>10} {'交易次数':>8}")
    print("-"*70)
    
    for name, metrics in results.items():
        if metrics:
            print(f"{name:<20} {metrics.get('total_return', 0):>9.2f}% {metrics.get('annual_return', 0):>9.2f}% {metrics.get('max_drawdown', 0):>9.2f}% {metrics.get('sharpe_ratio', 0):>10.2f} {metrics.get('total_trades', 0):>8}")
    
    print("\n测试完成!")


if __name__ == "__main__":
    main()
