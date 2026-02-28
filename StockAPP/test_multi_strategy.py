#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多策略组合策略测试脚本
测试搅屎棍+偷鸡摸狗+多ETF轮动组合策略
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from core.backtest_engine import BacktestEngine, BacktestConfig
from core.data_source import DataSource
from strategies.multi_factor.multi_strategy_portfolio import MultiStrategyPortfolio


ETF_CODES = [
    "518880", "513100", "159915", "513520", "513030",
    "161226", "159985", "511090", "159525", "513130", "159628"
]

STOCK_CODES = [
    "000001", "000002", "000063", "000333", "000651",
    "000725", "000858", "002415", "002594", "002714",
    "600000", "600009", "600016", "600019", "600028",
    "600030", "600036", "600048", "600050", "600104",
    "600276", "600309", "600346", "600438", "600519",
    "600585", "600690", "600887", "600900", "601012",
    "601088", "601166", "601288", "601318", "601328",
    "601398", "601668", "601688", "601818", "601899",
    "601919", "601939", "601988", "603259", "603288",
]


def test_multi_strategy_portfolio():
    print("=" * 60)
    print("多策略组合策略 - 回测测试")
    print("=" * 60)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    print(f"\n回测区间: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=1000000.0,
        commission_rate=0.0003,
        stamp_duty=0.001,
        min_commission=5.0,
        benchmark="000300"
    )
    
    data_source = DataSource()
    engine = BacktestEngine(config, data_source)
    
    print("\n正在加载指数数据...")
    index_data = data_source.get_index_history("000300", start_date - timedelta(days=100), end_date)
    if index_data is not None:
        engine.add_data("000300", index_data)
        print(f"  加载沪深300指数: {len(index_data)} 条")
    
    print("\n正在加载ETF数据...")
    etf_loaded = 0
    for i, code in enumerate(ETF_CODES):
        print(f"  加载ETF数据 [{i+1}/{len(ETF_CODES)}]: {code}")
        etf_data = data_source.get_etf_history(code, start_date - timedelta(days=60), end_date)
        if etf_data is not None and len(etf_data) > 0:
            engine.add_data(code, etf_data)
            etf_loaded += 1
    print(f"  成功加载 {etf_loaded} 只ETF数据")
    
    print("\n正在加载股票数据...")
    stock_loaded = 0
    for i, code in enumerate(STOCK_CODES[:20]):
        print(f"  加载股票数据 [{i+1}/{min(20, len(STOCK_CODES))}]: {code}")
        stock_data = data_source.get_stock_history(code, start_date - timedelta(days=60), end_date)
        if stock_data is not None and len(stock_data) > 0:
            engine.add_data(code, stock_data)
            stock_loaded += 1
    print(f"  成功加载 {stock_loaded} 只股票数据")
    
    if etf_loaded == 0 and stock_loaded == 0:
        print("错误: 没有加载到任何数据，无法进行回测")
        return None
    
    print("\n正在初始化多策略组合...")
    strategy = MultiStrategyPortfolio()
    strategy.set_params({
        "fms_pct": 0.43,
        "steal_dog_pct": 0.22,
        "multi_etf_pct": 0.35,
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


def test_single_strategies():
    """单独测试各子策略"""
    print("\n" + "=" * 60)
    print("单独测试各子策略")
    print("=" * 60)
    
    from strategies.multi_factor.fms_strategy import FMSStrategy
    from strategies.multi_factor.steal_dog_strategy import StealDogStrategy
    from strategies.multi_factor.multi_etf_rotation import MultiETFRotationStrategy
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000.0,
        commission_rate=0.0003,
        stamp_duty=0.001,
        min_commission=5.0,
    )
    
    data_source = DataSource()
    
    print("\n正在加载数据...")
    
    etf_data_map = {}
    for code in ETF_CODES:
        df = data_source.get_etf_history(code, start_date - timedelta(days=60), end_date)
        if df is not None and len(df) > 0:
            etf_data_map[code] = df
    
    stock_data_map = {}
    for code in STOCK_CODES[:20]:
        df = data_source.get_stock_history(code, start_date - timedelta(days=60), end_date)
        if df is not None and len(df) > 0:
            stock_data_map[code] = df
    
    print(f"加载ETF: {len(etf_data_map)} 只, 股票: {len(stock_data_map)} 只")
    
    results = {}
    
    if len(stock_data_map) > 0:
        print("\n--- 测试搅屎棍策略 ---")
        engine = BacktestEngine(config, data_source)
        for code, df in stock_data_map.items():
            engine.add_data(code, df)
        
        strategy = FMSStrategy()
        strategy.set_params({"max_positions": 2, "rebalance_days": 5})
        engine.add_strategy(strategy)
        
        try:
            result = engine.run(show_progress=False)
            results["搅屎棍"] = result.metrics
            print(f"  总收益率: {result.metrics.get('total_return', 0):.2f}%")
            print(f"  最大回撤: {result.metrics.get('max_drawdown', 0):.2f}%")
        except Exception as e:
            print(f"  测试失败: {e}")
    
    if len(etf_data_map) >= 3:
        print("\n--- 测试偷鸡摸狗策略 ---")
        engine = BacktestEngine(config, data_source)
        for code in ["518880", "513100", "159915"]:
            if code in etf_data_map:
                engine.add_data(code, etf_data_map[code])
        
        strategy = StealDogStrategy()
        strategy.set_params({"lookback_days": 25, "stop_loss_ratio": 0.08})
        engine.add_strategy(strategy)
        
        try:
            result = engine.run(show_progress=False)
            results["偷鸡摸狗"] = result.metrics
            print(f"  总收益率: {result.metrics.get('total_return', 0):.2f}%")
            print(f"  最大回撤: {result.metrics.get('max_drawdown', 0):.2f}%")
        except Exception as e:
            print(f"  测试失败: {e}")
    
    if len(etf_data_map) >= 5:
        print("\n--- 测试多ETF轮动策略 ---")
        engine = BacktestEngine(config, data_source)
        for code, df in list(etf_data_map.items())[:11]:
            engine.add_data(code, df)
        
        strategy = MultiETFRotationStrategy()
        strategy.set_params({"lookback_days": 25, "holdings_num": 1})
        engine.add_strategy(strategy)
        
        try:
            result = engine.run(show_progress=False)
            results["ETF轮动"] = result.metrics
            print(f"  总收益率: {result.metrics.get('total_return', 0):.2f}%")
            print(f"  最大回撤: {result.metrics.get('max_drawdown', 0):.2f}%")
        except Exception as e:
            print(f"  测试失败: {e}")
    
    return results


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("开始测试多策略组合策略")
    print("=" * 60)
    
    test_single_strategies()
    
    test_multi_strategy_portfolio()
    
    print("\n测试完成!")
