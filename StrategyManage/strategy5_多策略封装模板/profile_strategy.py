"""
性能分析脚本 - 找出 strategy5_多策略封装模板_本地.py 中运行最慢的部分
"""

import cProfile
import pstats
import io
from pstats import SortKey
import time
import functools
import pandas as pd
import numpy as np

# 导入原始模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategy5_多策略封装模板_本地 import (
    MultiStrategyBacktest, DataManager, 
    FMS_Strategy, Steal_Dog_Strategy, ETF_Rotation_Strategy,
    Context, Portfolio, SubPortfolio
)


class TimingDataManager(DataManager):
    """带计时的 DataManager 装饰器"""
    
    def __init__(self):
        super().__init__()
        self.timing_stats = {}
    
    def _time_it(self, method_name):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                
                if method_name not in self.timing_stats:
                    self.timing_stats[method_name] = {'total': 0, 'count': 0, 'max': 0}
                self.timing_stats[method_name]['total'] += elapsed
                self.timing_stats[method_name]['count'] += 1
                self.timing_stats[method_name]['max'] = max(self.timing_stats[method_name]['max'], elapsed)
                
                return result
            return wrapper
        return decorator
    
    def get_trade_days(self, start_date, end_date, index_code='000300'):
        return self._time_it('get_trade_days')(super().get_trade_days)(start_date, end_date, index_code)
    
    def get_stock_data(self, code, start_date=None, end_date=None, days=100):
        return self._time_it('get_stock_data')(super().get_stock_data)(code, start_date, end_date, days)
    
    def get_all_stocks(self):
        return self._time_it('get_all_stocks')(super().get_all_stocks)()
    
    def get_current_price(self, code, date):
        return self._time_it('get_current_price')(super().get_current_price)(code, date)
    
    def get_prices(self, codes, date, fields=None):
        return self._time_it('get_prices')(super().get_prices)(codes, date, fields)
    
    def get_financial_data(self, codes):
        return self._time_it('get_financial_data')(super().get_financial_data)(codes)
    
    def get_index_stocks(self, index_code, date=None):
        return self._time_it('get_index_stocks')(super().get_index_stocks)(index_code, date)
    
    def is_st_stock(self, code, date=None):
        return self._time_it('is_st_stock')(super().is_st_stock)(code, date)
    
    def is_paused(self, code, date):
        return self._time_it('is_paused')(super().is_paused)(code, date)
    
    def get_etf_data(self, code, start_date=None, end_date=None, days=100):
        return self._time_it('get_etf_data')(super().get_etf_data)(code, start_date, end_date, days)
    
    def print_timing_stats(self):
        print("\n" + "=" * 80)
        print("DataManager 方法耗时统计")
        print("=" * 80)
        print(f"{'方法名':<30} {'调用次数':>10} {'总耗时(s)':>12} {'平均耗时(s)':>12} {'最大耗时(s)':>12}")
        print("-" * 80)
        
        sorted_stats = sorted(self.timing_stats.items(), key=lambda x: x[1]['total'], reverse=True)
        
        for method_name, stats in sorted_stats:
            avg = stats['total'] / stats['count'] if stats['count'] > 0 else 0
            print(f"{method_name:<30} {stats['count']:>10} {stats['total']:>12.3f} {avg:>12.6f} {stats['max']:>12.6f}")


class TimingBacktest(MultiStrategyBacktest):
    """带计时的回测类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_manager = TimingDataManager()
        self.method_timing = {}
    
    def _time_method(self, method_name):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                
                if method_name not in self.method_timing:
                    self.method_timing[method_name] = {'total': 0, 'count': 0, 'max': 0}
                self.method_timing[method_name]['total'] += elapsed
                self.method_timing[method_name]['count'] += 1
                self.method_timing[method_name]['max'] = max(self.method_timing[method_name]['max'], elapsed)
                
                return result
            return wrapper
        return decorator
    
    def run_backtest(self):
        print("=" * 60)
        print("开始性能分析...")
        print("=" * 60)
        
        total_start = time.perf_counter()
        
        self.initialize()
        
        init_time = time.perf_counter() - total_start
        print(f"\n初始化耗时: {init_time:.3f} 秒")
        
        backtest_start = time.perf_counter()
        
        print("\n" + "=" * 60)
        print("开始运行回测...")
        print(f"回测区间: {self.start_date} 至 {self.end_date}")
        print(f"初始资金: {self.initial_cash:,.2f}")
        print("=" * 60)
        
        strategy_times = {s.name: {'total': 0, 'prepare': 0, 'weekly': 0, 'trade': 0, 'stop_loss': 0} 
                         for s in self.g.strategys}
        
        for i, date in enumerate(self.trade_days):
            day_start = time.perf_counter()
            
            self.context.current_dt = pd.to_datetime(date)
            self.context.previous_date = self.trade_days[i-1] if i > 0 else date
            
            if i % 20 == 0:
                print(f"\n回测进度: {date} ({i+1}/{len(self.trade_days)})")
            
            for strategy in self.g.strategys:
                if hasattr(strategy, 'prepare_stock_list'):
                    start = time.perf_counter()
                    try:
                        strategy.prepare_stock_list(self.context, date)
                    except Exception as e:
                        print(f"[{strategy.name}] prepare_stock_list 错误: {e}")
                    strategy_times[strategy.name]['prepare'] += time.perf_counter() - start
            
            if i % 5 == 0:
                for strategy in self.g.strategys:
                    if hasattr(strategy, 'weekly_adjustment'):
                        start = time.perf_counter()
                        try:
                            strategy.weekly_adjustment(self.context, date)
                        except Exception as e:
                            print(f"[{strategy.name}] weekly_adjustment 错误: {e}")
                        strategy_times[strategy.name]['weekly'] += time.perf_counter() - start
            
            for strategy in self.g.strategys:
                if hasattr(strategy, 'trade'):
                    start = time.perf_counter()
                    try:
                        strategy.trade(self.context, date)
                    except Exception as e:
                        print(f"[{strategy.name}] trade 错误: {e}")
                    strategy_times[strategy.name]['trade'] += time.perf_counter() - start
            
            for strategy in self.g.strategys:
                if hasattr(strategy, 'stop_loss'):
                    start = time.perf_counter()
                    try:
                        strategy.stop_loss(self.context, date)
                    except Exception as e:
                        print(f"[{strategy.name}] stop_loss 错误: {e}")
                    strategy_times[strategy.name]['stop_loss'] += time.perf_counter() - start
            
            for strategy in self.g.strategys:
                try:
                    strategy.record_daily_value(self.context)
                except Exception as e:
                    pass
            
            self.context.portfolio.update_total_value()
            
            self.daily_values.append({
                'date': date,
                'total_value': self.context.portfolio.total_value,
                'cash': self.context.portfolio.cash,
            })
        
        backtest_time = time.perf_counter() - backtest_start
        total_time = time.perf_counter() - total_start
        
        self.print_results()
        self.save_results()
        
        print("\n" + "=" * 80)
        print("性能分析结果")
        print("=" * 80)
        
        print(f"\n总耗时: {total_time:.3f} 秒")
        print(f"初始化耗时: {init_time:.3f} 秒 ({init_time/total_time*100:.1f}%)")
        print(f"回测循环耗时: {backtest_time:.3f} 秒 ({backtest_time/total_time*100:.1f}%)")
        
        print("\n" + "-" * 80)
        print("各策略方法耗时统计:")
        print("-" * 80)
        print(f"{'策略名':<15} {'prepare_stock_list':>18} {'weekly_adjustment':>18} {'trade':>12} {'stop_loss':>12} {'总计':>12}")
        print("-" * 80)
        
        for name, times in strategy_times.items():
            total = times['prepare'] + times['weekly'] + times['trade'] + times['stop_loss']
            print(f"{name:<15} {times['prepare']:>18.3f}s {times['weekly']:>18.3f}s {times['trade']:>12.3f}s {times['stop_loss']:>12.3f}s {total:>12.3f}s")
        
        self.data_manager.print_timing_stats()


def run_cprofile():
    """使用 cProfile 进行详细分析"""
    print("\n" + "=" * 80)
    print("使用 cProfile 进行详细性能分析")
    print("=" * 80)
    
    profiler = cProfile.Profile()
    
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    backtest = MultiStrategyBacktest(
        start_date=start_date,
        end_date=end_date,
        initial_cash=1000000.0
    )
    
    profiler.enable()
    backtest.run_backtest()
    profiler.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(SortKey.CUMULATIVE)
    ps.print_stats(50)
    
    print("\n" + "=" * 80)
    print("cProfile 分析结果 (按累计耗时排序 Top 50)")
    print("=" * 80)
    print(s.getvalue())
    
    s2 = io.StringIO()
    ps2 = pstats.Stats(profiler, stream=s2).sort_stats(SortKey.TIME)
    ps2.print_stats(30)
    
    print("\n" + "=" * 80)
    print("cProfile 分析结果 (按单次耗时排序 Top 30)")
    print("=" * 80)
    print(s2.getvalue())


def main():
    global pd, np
    import pandas as pd
    import numpy as np
    
    print("=" * 80)
    print("性能分析模式")
    print("=" * 80)
    
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    print(f"\n分析时间段: {start_date} 至 {end_date} (约3个月)")
    
    backtest = TimingBacktest(
        start_date=start_date,
        end_date=end_date,
        initial_cash=1000000.0
    )
    
    backtest.run_backtest()
    
    print("\n" + "=" * 80)
    print("性能分析完成!")
    print("=" * 80)


if __name__ == '__main__':
    main()
