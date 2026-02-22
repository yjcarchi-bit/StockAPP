#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略测试脚本
测试大市值低回撤策略
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from core.backtest_engine import BacktestEngine, BacktestConfig
from core.data_source import DataSource
from strategies.large_cap_low_drawdown import LargeCapLowDrawdownStrategy


def test_strategy():
    print("=" * 60)
    print("大市值低回撤策略 - 回测测试")
    print("=" * 60)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print(f"\n回测区间: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000.0,
        commission_rate=0.0003,
        stamp_duty=0.001,
        min_commission=5.0,
        benchmark="000300"
    )
    
    data_source = DataSource()
    engine = BacktestEngine(config, data_source)
    
    print("\n正在加载沪深300指数数据...")
    index_data = data_source.get_index_history("000300", start_date - timedelta(days=1500), end_date)
    if index_data is not None:
        engine.add_data("000300", index_data)
        print(f"  加载指数数据: {len(index_data)} 条")
    
    print("\n正在加载股票数据...")
    stock_codes = [
        "600519", "601318", "600036", "601166", "600887",
        "601398", "600030", "601288", "600276", "600000",
        "601888", "600016", "601012", "600048", "600900",
    ]
    
    loaded_count = 0
    for i, code in enumerate(stock_codes):
        print(f"  加载股票数据 [{i+1}/{len(stock_codes)}]: {code}")
        stock_data = data_source.get_stock_history(code, start_date - timedelta(days=100), end_date)
        if stock_data is not None and len(stock_data) > 0:
            engine.add_data(code, stock_data)
            loaded_count += 1
    
    print(f"\n成功加载 {loaded_count} 只股票数据")
    
    if loaded_count == 0:
        print("错误: 没有加载到任何股票数据，无法进行回测")
        return
    
    print("\n正在初始化策略...")
    strategy = LargeCapLowDrawdownStrategy()
    strategy.set_params({
        "max_positions": 3,
        "stop_loss_ratio": 0.05,
        "take_profit_ratio": 0.35,
        "drawdown_lock_threshold": 0.10,
        "use_rsrs_timing": True,
        "use_partial_unlock": True,
        "rsrs_buy_threshold": 0.7,
    })
    engine.add_strategy(strategy)
    
    print("\n开始运行回测...")
    print("-" * 60)
    
    try:
        result = engine.run(show_progress=True)
        
        print("\n" + "=" * 60)
        print("回测完成!")
        print("=" * 60)
        
        if result.metrics:
            print(f"\n关键指标:")
            print(f"  总收益率: {result.metrics.get('total_return', 0):.2f}%")
            print(f"  年化收益率: {result.metrics.get('annual_return', 0):.2f}%")
            print(f"  最大回撤: {result.metrics.get('max_drawdown', 0):.2f}%")
            print(f"  夏普比率: {result.metrics.get('sharpe_ratio', 0):.2f}")
            print(f"  交易次数: {result.metrics.get('total_trades', 0)}")
            print(f"  胜率: {result.metrics.get('win_rate', 0):.2f}%")
        
        return result
        
    except Exception as e:
        print(f"\n回测出错: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_strategy()
