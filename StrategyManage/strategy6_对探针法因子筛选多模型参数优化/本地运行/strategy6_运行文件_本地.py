# -*- coding: utf-8 -*-
"""
================================================================================
策略名称：对探针法因子筛选多模型参数优化 - 本地回测版本
================================================================================

【策略概述】
本策略是一个基于机器学习的多因子量化选股策略，核心思想是：
1. 使用"探针法"筛选有效因子
2. 训练三个LightGBM模型（分类、回归、方向）
3. 根据模型预测结果进行选股
4. 动态调整进攻/防御模式

【策略流程】
┌─────────────────────────────────────────────────────────────────┐
│  第一步：数据准备                                                │
│  ├── 获取股票池（沪深300成分股）                                  │
│  ├── 过滤ST、停牌、涨跌停股票                                     │
│  └── 计算技术因子（49个筛选后因子）                                │
├─────────────────────────────────────────────────────────────────┤
│  第二步：模型预测                                                │
│  ├── 回归模型：预测股票收益排名                                   │
│  ├── 分类模型：预测是否跑赢中位数                                 │
│  └── 方向模型：预测涨跌方向                                       │
├─────────────────────────────────────────────────────────────────┤
│  第三步：综合评分                                                │
│  ├── AI得分 = 三个模型预测值的平均                                │
│  ├── 一致性 = 三个模型预测值的方差                                │
│  └── 动态阈值 = 历史一致性分布的80%分位数                          │
├─────────────────────────────────────────────────────────────────┤
│  第四步：选股决策                                                │
│  ├── 防御模式（一致性>阈值）：先选一致性高，再选AI得分高            │
│  └── 进攻模式（一致性≤阈值）：直接选AI得分高                       │
├─────────────────────────────────────────────────────────────────┤
│  第五步：组合构建                                                │
│  ├── 持仓数量：10只股票                                          │
│  ├── 调仓频率：月度                                              │
│  └── 权重分配：等权                                               │
└─────────────────────────────────────────────────────────────────┘

【因子分类】
- 趋势因子：momentum, ROC系列, TREND_STRENGTH, TRIX
- 波动因子：Kurtosis, Skewness, Variance, VOLATILITY_RATIO
- 成交量因子：VOSC, VMACD, VOLUME_RATIO, OBV, ADL, CMF
- 技术指标：RSI, MACD, KDJ, DMI, CCI, WR, UOS
- 价格位置：Rank1M, PRICE_POSITION, PRICE_MA_RATIO
- 风险收益：SHARPE_LIKE, SORTINO_LIKE, CALMAR_LIKE, MAX_DRAWDOWN

【风险控制】
- 涨跌停过滤：排除当日涨停/跌停股票
- 动态防御：市场分歧大时降低风险暴露
- 分散投资：持仓10只股票分散风险

原始来源：聚宽平台
本地化时间：2026-02-21
================================================================================
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import efinance as ef
import pickle
import os
import time
import warnings
import sys
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import hashlib
import json
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backtest_report_generator import BacktestReportGenerator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strategy6_前期准备步骤文件 import (
    FactorCalculator, 
    DataFetcher, 
    calculate_all_factors
)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("警告: reportlab未安装，PDF报告功能将不可用。安装命令: pip install reportlab")

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.font_manager import FontProperties
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("警告: matplotlib未安装，图表生成功能将不可用")


class ProgressTracker:
    """进度追踪器 - 提供实时进度反馈"""
    
    def __init__(self, total_steps, desc="进度"):
        self.total_steps = total_steps
        self.current_step = 0
        self.desc = desc
        self.start_time = time.time()
        self.last_update_time = 0
        self.update_interval = 1.0
    
    def update(self, step_name="", increment=1):
        self.current_step += increment
        elapsed = time.time() - self.start_time
        
        if time.time() - self.last_update_time >= self.update_interval or self.current_step >= self.total_steps:
            progress = self.current_step / self.total_steps * 100
            if self.current_step > 0:
                eta = elapsed / self.current_step * (self.total_steps - self.current_step)
                eta_str = self._format_time(eta)
            else:
                eta_str = "计算中..."
            
            bar_length = 30
            filled = int(bar_length * self.current_step / self.total_steps)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            print(f"\r  [{bar}] {progress:5.1f}% | {self.desc}: {self.current_step}/{self.total_steps} | 耗时: {self._format_time(elapsed)} | 剩余: {eta_str} | {step_name}", end='', flush=True)
            self.last_update_time = time.time()
    
    def finish(self):
        elapsed = time.time() - self.start_time
        bar = '█' * 30
        print(f"\r  [{bar}] 100.0% | {self.desc}: {self.total_steps}/{self.total_steps} | 总耗时: {self._format_time(elapsed)}" + " " * 30)
    
    def _format_time(self, seconds):
        if seconds < 60:
            return f"{seconds:.0f}秒"
        elif seconds < 3600:
            return f"{seconds/60:.1f}分钟"
        else:
            return f"{seconds/3600:.1f}小时"


class DataCache:
    """数据缓存管理器 - 提升数据获取性能"""
    
    def __init__(self, cache_dir=None, max_memory_cache=100):
        self.memory_cache = {}
        self.max_memory_cache = max_memory_cache
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), '.cache')
        self.hit_count = 0
        self.miss_count = 0
        
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _get_cache_key(self, stock_code, start_date, end_date):
        key_str = f"{stock_code}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, stock_code, start_date, end_date):
        cache_key = self._get_cache_key(stock_code, start_date, end_date)
        
        if cache_key in self.memory_cache:
            self.hit_count += 1
            return self.memory_cache[cache_key]
        
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                    if len(self.memory_cache) < self.max_memory_cache:
                        self.memory_cache[cache_key] = data
                    self.hit_count += 1
                    return data
            except:
                pass
        
        self.miss_count += 1
        return None
    
    def set(self, stock_code, start_date, end_date, data):
        cache_key = self._get_cache_key(stock_code, start_date, end_date)
        
        if len(self.memory_cache) < self.max_memory_cache:
            self.memory_cache[cache_key] = data
        
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
        except:
            pass
    
    def get_stats(self):
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total * 100 if total > 0 else 0
        return {
            'hits': self.hit_count,
            'misses': self.miss_count,
            'hit_rate': hit_rate
        }


class AIPortfolioStrategy:
    """
    AI多模型因子选股策略 - 本地回测版本
    
    该策略使用机器学习方法进行股票选股，核心步骤包括：
    1. 因子计算：计算49个技术因子
    2. 模型预测：使用三个LightGBM模型进行预测
    3. 综合评分：计算AI得分和一致性
    4. 动态选股：根据市场状态选择进攻或防御模式
    """
    
    def __init__(self, initial_capital=1000000, stock_num=10, use_cache=True, max_workers=5):
        """
        初始化策略
        
        参数:
            initial_capital: 初始资金
            stock_num: 持仓股票数量
            use_cache: 是否使用数据缓存
            max_workers: 并行处理的最大线程数
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.position_cost = {}
        self.trade_history = []
        self.daily_values = []
        
        self.stock_num = stock_num
        self.hold_list = []
        self.yesterday_HL_list = []
        
        self.avg_ai_score = 0
        self.avg_consistency = 0
        self.consistency_history = []
        
        self.data_fetcher = DataFetcher()
        self.cache = DataCache() if use_cache else None
        self.max_workers = max_workers
        
        self.backtest_stats = {
            'total_stocks_analyzed': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'avg_holding_days': 0,
            'mode_switches': {'attack': 0, 'defense': 0}
        }
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        print("\n" + "=" * 70)
        print("【策略初始化】")
        print("=" * 70)
        
        try:
            with open(os.path.join(script_dir, 'model_reg_final.pkl'), 'rb') as f:
                self.model_reg = pickle.load(f)
            print("  ✓ 回归模型加载成功")
            
            with open(os.path.join(script_dir, 'model_cls_final.pkl'), 'rb') as f:
                self.model_cls = pickle.load(f)
            print("  ✓ 分类模型加载成功")
            
            with open(os.path.join(script_dir, 'model_dir_final.pkl'), 'rb') as f:
                self.model_dir = pickle.load(f)
            print("  ✓ 方向模型加载成功")
            
            df_factors = pd.read_csv(os.path.join(script_dir, 'selected_factors.csv'))
            self.factor_list = list(df_factors['factor'])
            print(f"  ✓ 因子列表加载成功，共 {len(self.factor_list)} 个因子")
            
        except Exception as e:
            print(f"  ✗ 模型加载失败: {e}")
            self.model_reg = None
            self.model_cls = None
            self.model_dir = None
            self.factor_list = []
        
        print("=" * 70)
    
    def get_stock_pool(self, date):
        """
        获取股票池
        
        筛选条件：
        1. 沪深300成分股
        2. 非ST股票
        3. 非停牌股票
        4. 非涨停/跌停股票
        
        参数:
            date: 查询日期
            
        返回:
            有效股票代码列表
        """
        stock_list = self.data_fetcher.get_stock_list(date)
        valid_stocks = []
        
        progress = ProgressTracker(len(stock_list), "筛选股票池")
        
        for i, stock_code in enumerate(stock_list):
            try:
                df = self.data_fetcher.get_stock_data(
                    stock_code, 
                    date - timedelta(days=10), 
                    date
                )
                
                if df is None or len(df) < 5:
                    progress.update(f"跳过 {stock_code}")
                    continue
                
                last_row = df.iloc[-1]
                
                if last_row['pct_change'] >= 9.9:
                    progress.update(f"涨停 {stock_code}")
                    continue
                
                if last_row['pct_change'] <= -9.9:
                    progress.update(f"跌停 {stock_code}")
                    continue
                
                valid_stocks.append(stock_code)
                progress.update(f"保留 {stock_code}")
                
            except Exception as e:
                progress.update(f"错误 {stock_code}")
                continue
        
        progress.finish()
        
        return valid_stocks
    
    def _get_stock_data_cached(self, stock_code, start_date, end_date):
        """带缓存的数据获取"""
        if self.cache:
            cached_data = self.cache.get(stock_code, start_date, end_date)
            if cached_data is not None:
                return cached_data
        
        data = self.data_fetcher.get_stock_data(stock_code, start_date, end_date)
        
        if data is not None and self.cache:
            self.cache.set(stock_code, start_date, end_date, data)
        
        return data
    
    def _calculate_factors_for_stock(self, stock_code, start_date, end_date, min_data_days=60):
        """计算单只股票的因子"""
        try:
            df = self._get_stock_data_cached(stock_code, start_date, end_date)
            
            if df is None or len(df) < min_data_days:
                return None
            
            factors = calculate_all_factors(df)
            if factors is None:
                return None
            
            valid_factors = {k: v for k, v in factors.items() if k in self.factor_list}
            if len(valid_factors) == len(self.factor_list):
                return stock_code, valid_factors
            
            return None
        except Exception as e:
            return None
    
    def get_factor_data(self, stock_list, date):
        """
        获取因子数据（并行处理优化版）
        
        参数:
            stock_list: 股票列表
            date: 查询日期
            
        返回:
            因子数据DataFrame
        """
        lookback_days = 200
        start_date = date - timedelta(days=lookback_days)
        
        factor_data = {}
        
        print(f"\n  【因子计算】处理 {len(stock_list)} 只股票...")
        progress = ProgressTracker(len(stock_list), "计算因子")
        
        if self.max_workers > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(
                        self._calculate_factors_for_stock, 
                        stock_code, 
                        start_date, 
                        date
                    ): stock_code 
                    for stock_code in stock_list
                }
                
                for future in as_completed(futures):
                    result = future.result()
                    if result is not None:
                        stock_code, factors = result
                        factor_data[stock_code] = factors
                    progress.update()
        else:
            for stock_code in stock_list:
                result = self._calculate_factors_for_stock(stock_code, start_date, date)
                if result is not None:
                    stock_code, factors = result
                    factor_data[stock_code] = factors
                progress.update()
                time.sleep(0.02)
        
        progress.finish()
        
        if not factor_data:
            return None
        
        df_factors = pd.DataFrame(factor_data).T
        df_factors = df_factors[self.factor_list]
        df_factors = df_factors.fillna(0)
        
        self.backtest_stats['total_stocks_analyzed'] += len(factor_data)
        
        return df_factors
    
    def get_stock_predictions(self, stock_list, date):
        """
        获取股票预测结果
        
        使用三个模型进行预测：
        1. 回归模型：预测收益排名（0-1）
        2. 分类模型：预测是否跑赢中位数（概率）
        3. 方向模型：预测涨跌方向（概率）
        
        参数:
            stock_list: 股票列表
            date: 查询日期
            
        返回:
            包含预测结果的DataFrame
        """
        df_factors = self.get_factor_data(stock_list, date)
        
        if df_factors is None or len(df_factors) == 0:
            return None
        
        try:
            preds = np.column_stack([
                self.model_reg.predict(df_factors),
                self.model_cls.predict(df_factors),
                self.model_dir.predict(df_factors)
            ])
            
            ai_score = preds.mean(axis=1)
            consistency = preds.var(axis=1, ddof=0)
            
            df = df_factors.copy()
            df['AI_score'] = ai_score
            df['consistency'] = consistency
            df['pred_reg'] = preds[:, 0]
            df['pred_cls'] = preds[:, 1]
            df['pred_dir'] = preds[:, 2]
            
            self.avg_ai_score = df['AI_score'].mean()
            self.avg_consistency = df['consistency'].mean()
            
            return df
            
        except Exception as e:
            print(f"  预测失败: {e}")
            return None
    
    def select_stocks(self, date):
        """
        选股逻辑（动态自适应阈值）
        
        选股策略：
        1. 计算全市场一致性方差
        2. 根据动态阈值判断市场状态
        3. 防御模式：优先选择一致性高的股票
        4. 进攻模式：直接选择AI得分高的股票
        
        参数:
            date: 调仓日期
            
        返回:
            选中的股票列表
        """
        print(f"\n{'─' * 60}")
        print(f"【选股流程】{date.strftime('%Y-%m-%d')}")
        print(f"{'─' * 60}")
        
        print("\n  【步骤1】获取股票池...")
        stock_pool = self.get_stock_pool(date)
        print(f"  股票池数量: {len(stock_pool)}")
        
        if len(stock_pool) < self.stock_num:
            print("  股票池数量不足，无法选股")
            return []
        
        print("\n  【步骤2】模型预测...")
        df = self.get_stock_predictions(stock_pool, date)
        
        if df is None or len(df) == 0:
            print("  无法获取预测结果")
            return []
        
        print(f"\n  【步骤3】计算综合指标...")
        print(f"  ├─ 预测股票数: {len(df)}")
        print(f"  ├─ AI得分均值: {self.avg_ai_score:.4f}")
        print(f"  └─ 一致性方差: {self.avg_consistency:.6f}")
        
        self.consistency_history.append(self.avg_consistency)
        window_length = 24
        if len(self.consistency_history) > window_length:
            self.consistency_history.pop(0)
        
        if len(self.consistency_history) >= 5:
            dynamic_threshold = np.percentile(self.consistency_history, 80)
        else:
            dynamic_threshold = 0.005
        
        print(f"\n  【步骤4】市场状态判断...")
        print(f"  ├─ 动态防御阈值: {dynamic_threshold:.6f}")
        print(f"  └─ 历史一致性记录: {len(self.consistency_history)} 条")
        
        if self.avg_consistency > dynamic_threshold:
            print(f"\n  【防御模式】市场分歧过大 (方差 {self.avg_consistency:.6f} > 阈值 {dynamic_threshold:.6f})")
            print("  策略：优先选择模型预测一致性高的股票")
            
            df_sorted = df.sort_values(by='consistency', ascending=True)
            top_10_percent = max(int(0.1 * len(df_sorted)), self.stock_num)
            df_candidate = df_sorted.head(top_10_percent)
            
            df_candidate_sorted = df_candidate.sort_values(by='AI_score', ascending=False)
            top_20_percent = max(int(0.2 * len(df_candidate_sorted)), self.stock_num)
            df_selected = df_candidate_sorted.head(top_20_percent)
            
            self.backtest_stats['mode_switches']['defense'] += 1
        else:
            print(f"\n  【进攻模式】市场分歧正常 (方差 {self.avg_consistency:.6f} ≤ 阈值 {dynamic_threshold:.6f})")
            print("  策略：直接选择AI得分最高的股票")
            
            df_sorted = df.sort_values(by='AI_score', ascending=False)
            top_20_percent = max(int(0.2 * len(df_sorted)), self.stock_num)
            df_selected = df_sorted.head(top_20_percent)
            
            self.backtest_stats['mode_switches']['attack'] += 1
        
        selected_stocks = df_selected.index.tolist()[:self.stock_num]
        
        print(f"\n  【步骤5】选中股票:")
        for i, stock in enumerate(selected_stocks, 1):
            ai = df.loc[stock, 'AI_score']
            cons = df.loc[stock, 'consistency']
            print(f"    {i}. {stock} | AI得分: {ai:.4f} | 一致性: {cons:.6f}")
        
        return selected_stocks
    
    def get_current_price(self, stock_code, date):
        """获取当前价格"""
        try:
            df = self._get_stock_data_cached(
                stock_code, 
                date - timedelta(days=5), 
                date
            )
            if df is not None and len(df) > 0:
                return df['close'].iloc[-1]
        except:
            pass
        return None
    
    def buy_stock(self, stock_code, price, amount, date):
        """买入股票"""
        cost = price * amount
        if cost > self.cash:
            amount = int(self.cash / price / 100) * 100
            if amount <= 0:
                return False
            cost = price * amount
        
        self.cash -= cost
        
        if stock_code in self.positions:
            old_amount = self.positions[stock_code]
            old_cost = self.position_cost[stock_code] * old_amount
            self.positions[stock_code] += amount
            self.position_cost[stock_code] = (old_cost + cost) / self.positions[stock_code]
        else:
            self.positions[stock_code] = amount
            self.position_cost[stock_code] = price
        
        self.trade_history.append({
            'date': date,
            'action': 'buy',
            'stock': stock_code,
            'price': price,
            'amount': amount,
            'value': cost
        })
        
        self.backtest_stats['total_trades'] += 1
        
        print(f"    ✓ 买入 {stock_code}: 价格 {price:.2f}, 数量 {amount}, 金额 {cost:,.2f}")
        return True
    
    def sell_stock(self, stock_code, price, date):
        """卖出股票"""
        if stock_code not in self.positions or self.positions[stock_code] <= 0:
            return False
        
        amount = self.positions[stock_code]
        revenue = price * amount
        cost_price = self.position_cost.get(stock_code, price)
        
        self.cash += revenue
        self.positions[stock_code] = 0
        
        profit = (price - cost_price) * amount
        if profit > 0:
            self.backtest_stats['winning_trades'] += 1
        else:
            self.backtest_stats['losing_trades'] += 1
        
        self.trade_history.append({
            'date': date,
            'action': 'sell',
            'stock': stock_code,
            'price': price,
            'amount': amount,
            'value': revenue,
            'profit': profit
        })
        
        self.backtest_stats['total_trades'] += 1
        
        profit_pct = (price / cost_price - 1) * 100
        print(f"    ✓ 卖出 {stock_code}: 价格 {price:.2f}, 数量 {amount}, 金额 {revenue:,.2f}, 盈亏: {profit_pct:+.2f}%")
        return True
    
    def get_total_value(self, date):
        """计算总资产"""
        total = self.cash
        for stock_code, amount in self.positions.items():
            if amount > 0:
                price = self.get_current_price(stock_code, date)
                if price:
                    total += amount * price
        return total
    
    def run_backtest(self, start_date, end_date):
        """
        运行回测
        
        参数:
            start_date: 回测开始日期
            end_date: 回测结束日期
        """
        print("\n" + "=" * 70)
        print("【回测开始】AI多模型因子选股策略")
        print("=" * 70)
        print(f"  回测区间: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        print(f"  初始资金: {self.initial_capital:,.2f}")
        print(f"  持仓数量: {self.stock_num}")
        print(f"  调仓频率: 月度")
        print(f"  因子数量: {len(self.factor_list)}")
        print("=" * 70)
        
        if self.model_reg is None:
            print("错误: 模型未加载，无法运行回测")
            return
        
        trade_dates = pd.date_range(start=start_date, end=end_date, freq='MS')
        total_dates = len(trade_dates)
        
        main_progress = ProgressTracker(total_dates, "回测进度")
        
        for i, trade_date in enumerate(trade_dates):
            print(f"\n{'═' * 70}")
            print(f"【调仓 {i+1}/{total_dates}】{trade_date.strftime('%Y-%m-%d')}")
            print(f"{'═' * 70}")
            
            target_list = self.select_stocks(trade_date)
            
            if not target_list:
                print("  未选出股票，保持当前持仓")
                total_value = self.get_total_value(trade_date)
                self.daily_values.append({
                    'date': trade_date,
                    'value': total_value,
                    'cash': self.cash,
                    'positions': dict(self.positions)
                })
                main_progress.update(f"保持持仓")
                continue
            
            print(f"\n  【调仓执行】")
            print(f"  目标持仓: {target_list}")
            
            for stock_code in list(self.positions.keys()):
                if self.positions[stock_code] > 0 and stock_code not in target_list:
                    price = self.get_current_price(stock_code, trade_date)
                    if price:
                        self.sell_stock(stock_code, price, trade_date)
            
            current_position_count = sum(1 for v in self.positions.values() if v > 0)
            target_num = len(target_list)
            
            if target_num > current_position_count:
                buy_num = target_num - current_position_count
                value_per_stock = self.cash / buy_num if buy_num > 0 else 0
                
                for stock_code in target_list:
                    if self.positions.get(stock_code, 0) == 0:
                        price = self.get_current_price(stock_code, trade_date)
                        if price and value_per_stock > 0:
                            amount = int(value_per_stock / price / 100) * 100
                            if amount > 0:
                                self.buy_stock(stock_code, price, amount, trade_date)
            
            total_value = self.get_total_value(trade_date)
            self.daily_values.append({
                'date': trade_date,
                'value': total_value,
                'cash': self.cash,
                'positions': dict(self.positions)
            })
            
            pnl = total_value - self.initial_capital
            pnl_pct = pnl / self.initial_capital * 100
            
            print(f"\n  【账户状态】")
            print(f"  ├─ 总资产: {total_value:,.2f}")
            print(f"  ├─ 现金: {self.cash:,.2f}")
            print(f"  ├─ 持仓市值: {total_value - self.cash:,.2f}")
            print(f"  └─ 累计盈亏: {pnl:+,.2f} ({pnl_pct:+.2f}%)")
            
            main_progress.update(f"资产: {total_value:,.0f}")
            
            time.sleep(0.5)
        
        main_progress.finish()
        
        self.print_backtest_results()
    
    def print_backtest_results(self):
        """打印回测结果"""
        print("\n" + "=" * 70)
        print("【回测结果汇总】")
        print("=" * 70)
        
        if not self.daily_values:
            print("无回测数据")
            return
        
        df_values = pd.DataFrame(self.daily_values)
        df_values['date'] = pd.to_datetime(df_values['date'])
        df_values = df_values.set_index('date')
        
        final_value = df_values['value'].iloc[-1]
        total_return = (final_value / self.initial_capital - 1) * 100
        
        df_values['daily_return'] = df_values['value'].pct_change()
        annual_return = df_values['daily_return'].mean() * 12 * 100
        annual_volatility = df_values['daily_return'].std() * np.sqrt(12) * 100
        sharpe_ratio = (annual_return - 3) / annual_volatility if annual_volatility > 0 else 0
        
        max_value = df_values['value'].expanding().max()
        drawdown = (df_values['value'] - max_value) / max_value
        max_drawdown = drawdown.min() * 100
        
        winning_rate = self.backtest_stats['winning_trades'] / max(self.backtest_stats['winning_trades'] + self.backtest_stats['losing_trades'], 1) * 100
        
        print("\n【收益指标】")
        print(f"  ├─ 初始资金: {self.initial_capital:,.2f}")
        print(f"  ├─ 最终资金: {final_value:,.2f}")
        print(f"  ├─ 总收益率: {total_return:.2f}%")
        print(f"  └─ 年化收益率: {annual_return:.2f}%")
        
        print("\n【风险指标】")
        print(f"  ├─ 年化波动率: {annual_volatility:.2f}%")
        print(f"  ├─ 夏普比率: {sharpe_ratio:.2f}")
        print(f"  └─ 最大回撤: {max_drawdown:.2f}%")
        
        print("\n【交易统计】")
        print(f"  ├─ 总交易次数: {self.backtest_stats['total_trades']}")
        print(f"  ├─ 盈利交易: {self.backtest_stats['winning_trades']}")
        print(f"  ├─ 亏损交易: {self.backtest_stats['losing_trades']}")
        print(f"  ├─ 胜率: {winning_rate:.1f}%")
        print(f"  ├─ 进攻模式次数: {self.backtest_stats['mode_switches']['attack']}")
        print(f"  └─ 防御模式次数: {self.backtest_stats['mode_switches']['defense']}")
        
        if self.cache:
            stats = self.cache.get_stats()
            print("\n【性能统计】")
            print(f"  ├─ 缓存命中: {stats['hits']}")
            print(f"  ├─ 缓存未命中: {stats['misses']}")
            print(f"  └─ 命中率: {stats['hit_rate']:.1f}%")
        
        print("\n【交易记录】")
        df_trades = pd.DataFrame(self.trade_history)
        if not df_trades.empty:
            print(df_trades.to_string(index=False))
        
        return df_values, df_trades
    
    def generate_charts(self, output_dir):
        """生成图表"""
        if not MATPLOTLIB_AVAILABLE:
            print("matplotlib未安装，跳过图表生成")
            return []
        
        chart_files = []
        
        df_values = pd.DataFrame(self.daily_values)
        df_values['date'] = pd.to_datetime(df_values['date'])
        df_values = df_values.set_index('date')
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('AI多模型因子选股策略 - 回测分析', fontsize=14, fontweight='bold')
        
        ax1 = axes[0, 0]
        ax1.plot(df_values.index, df_values['value'], 'b-', linewidth=2, label='总资产')
        ax1.axhline(y=self.initial_capital, color='gray', linestyle='--', label='初始资金')
        ax1.fill_between(df_values.index, self.initial_capital, df_values['value'], 
                         where=df_values['value'] >= self.initial_capital, 
                         alpha=0.3, color='green', label='盈利区域')
        ax1.fill_between(df_values.index, self.initial_capital, df_values['value'], 
                         where=df_values['value'] < self.initial_capital, 
                         alpha=0.3, color='red', label='亏损区域')
        ax1.set_title('资产曲线', fontsize=12)
        ax1.set_xlabel('日期')
        ax1.set_ylabel('资产价值')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        ax2 = axes[0, 1]
        df_values['daily_return'] = df_values['value'].pct_change()
        max_value = df_values['value'].expanding().max()
        drawdown = (df_values['value'] - max_value) / max_value * 100
        ax2.fill_between(drawdown.index, 0, drawdown, color='red', alpha=0.5)
        ax2.plot(drawdown.index, drawdown, 'r-', linewidth=1)
        ax2.set_title('回撤曲线', fontsize=12)
        ax2.set_xlabel('日期')
        ax2.set_ylabel('回撤 (%)')
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        ax3 = axes[1, 0]
        position_values = df_values['value'] - df_values['cash']
        ax3.stackplot(df_values.index, 
                      df_values['cash'], 
                      position_values,
                      labels=['现金', '持仓市值'],
                      colors=['#2ecc71', '#3498db'],
                      alpha=0.8)
        ax3.set_title('资产构成', fontsize=12)
        ax3.set_xlabel('日期')
        ax3.set_ylabel('金额')
        ax3.legend(loc='upper left')
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
        
        ax4 = axes[1, 1]
        if self.trade_history:
            df_trades = pd.DataFrame(self.trade_history)
            sell_trades = df_trades[df_trades['action'] == 'sell'].copy()
            if len(sell_trades) > 0:
                sell_trades['profit'] = sell_trades.get('profit', 0)
                profits = sell_trades['profit'].values
                ax4.hist(profits, bins=20, color='steelblue', edgecolor='white', alpha=0.7)
                ax4.axvline(x=0, color='red', linestyle='--', linewidth=2)
                ax4.set_title('交易盈亏分布', fontsize=12)
                ax4.set_xlabel('盈亏金额')
                ax4.set_ylabel('交易次数')
                ax4.grid(True, alpha=0.3)
            else:
                ax4.text(0.5, 0.5, '暂无卖出交易', ha='center', va='center', fontsize=12)
                ax4.set_title('交易盈亏分布', fontsize=12)
        else:
            ax4.text(0.5, 0.5, '暂无交易记录', ha='center', va='center', fontsize=12)
            ax4.set_title('交易盈亏分布', fontsize=12)
        
        plt.tight_layout()
        
        chart_file = os.path.join(output_dir, 'backtest_charts.png')
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()
        chart_files.append(chart_file)
        
        return chart_files
    
    def generate_pdf_report(self, output_path=None):
        """生成PDF报告"""
        if not REPORTLAB_AVAILABLE:
            print("reportlab未安装，跳过PDF报告生成")
            return None
        
        if output_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(script_dir, 'backtest_report.pdf')
        
        output_dir = os.path.dirname(output_path)
        
        chart_files = self.generate_charts(output_dir)
        
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                rightMargin=1*cm, leftMargin=1*cm,
                                topMargin=1*cm, bottomMargin=1*cm)
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            leading=14
        )
        
        story = []
        
        story.append(Paragraph("AI多模型因子选股策略", title_style))
        story.append(Paragraph("回测分析报告", title_style))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("一、策略概述", heading_style))
        
        strategy_desc = """
        本策略是一个基于机器学习的多因子量化选股策略，使用"探针法"筛选有效因子，
        训练三个LightGBM模型（分类、回归、方向），根据模型预测结果进行选股，
        并动态调整进攻/防御模式。
        """
        story.append(Paragraph(strategy_desc, normal_style))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph("二、回测参数", heading_style))
        
        if self.daily_values:
            start_date = self.daily_values[0]['date'].strftime('%Y-%m-%d')
            end_date = self.daily_values[-1]['date'].strftime('%Y-%m-%d')
        else:
            start_date = "N/A"
            end_date = "N/A"
        
        params_data = [
            ['参数', '值'],
            ['回测区间', f'{start_date} 至 {end_date}'],
            ['初始资金', f'{self.initial_capital:,.2f}'],
            ['持仓数量', str(self.stock_num)],
            ['调仓频率', '月度'],
            ['因子数量', str(len(self.factor_list))],
        ]
        
        params_table = Table(params_data, colWidths=[4*cm, 8*cm])
        params_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(params_table)
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("三、收益指标", heading_style))
        
        if self.daily_values:
            df_values = pd.DataFrame(self.daily_values)
            df_values['date'] = pd.to_datetime(df_values['date'])
            df_values = df_values.set_index('date')
            
            final_value = df_values['value'].iloc[-1]
            total_return = (final_value / self.initial_capital - 1) * 100
            
            df_values['daily_return'] = df_values['value'].pct_change()
            annual_return = df_values['daily_return'].mean() * 12 * 100
            annual_volatility = df_values['daily_return'].std() * np.sqrt(12) * 100
            sharpe_ratio = (annual_return - 3) / annual_volatility if annual_volatility > 0 else 0
            
            max_value = df_values['value'].expanding().max()
            drawdown = (df_values['value'] - max_value) / max_value
            max_drawdown = drawdown.min() * 100
        else:
            final_value = self.initial_capital
            total_return = 0
            annual_return = 0
            annual_volatility = 0
            sharpe_ratio = 0
            max_drawdown = 0
        
        returns_data = [
            ['指标', '数值'],
            ['初始资金', f'{self.initial_capital:,.2f}'],
            ['最终资金', f'{final_value:,.2f}'],
            ['总收益率', f'{total_return:.2f}%'],
            ['年化收益率', f'{annual_return:.2f}%'],
            ['年化波动率', f'{annual_volatility:.2f}%'],
            ['夏普比率', f'{sharpe_ratio:.2f}'],
            ['最大回撤', f'{max_drawdown:.2f}%'],
        ]
        
        returns_table = Table(returns_data, colWidths=[4*cm, 8*cm])
        returns_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(returns_table)
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("四、交易统计", heading_style))
        
        winning_rate = self.backtest_stats['winning_trades'] / max(self.backtest_stats['winning_trades'] + self.backtest_stats['losing_trades'], 1) * 100
        
        trades_data = [
            ['指标', '数值'],
            ['总交易次数', str(self.backtest_stats['total_trades'])],
            ['盈利交易', str(self.backtest_stats['winning_trades'])],
            ['亏损交易', str(self.backtest_stats['losing_trades'])],
            ['胜率', f'{winning_rate:.1f}%'],
            ['进攻模式次数', str(self.backtest_stats['mode_switches']['attack'])],
            ['防御模式次数', str(self.backtest_stats['mode_switches']['defense'])],
        ]
        
        trades_table = Table(trades_data, colWidths=[4*cm, 8*cm])
        trades_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(trades_table)
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("五、回测图表", heading_style))
        
        if chart_files:
            for chart_file in chart_files:
                if os.path.exists(chart_file):
                    img = Image(chart_file, width=16*cm, height=11*cm)
                    story.append(img)
                    story.append(Spacer(1, 10))
        
        story.append(PageBreak())
        
        story.append(Paragraph("六、策略流程详解", heading_style))
        
        process_text = """
        <b>第一步：数据准备</b><br/>
        获取沪深300成分股作为股票池，过滤ST、停牌、涨跌停股票，
        计算每个股票的49个技术因子。<br/><br/>
        
        <b>第二步：模型预测</b><br/>
        使用三个LightGBM模型进行预测：<br/>
        - 回归模型：预测股票收益排名（0-1）<br/>
        - 分类模型：预测是否跑赢中位数（概率）<br/>
        - 方向模型：预测涨跌方向（概率）<br/><br/>
        
        <b>第三步：综合评分</b><br/>
        AI得分 = 三个模型预测值的平均<br/>
        一致性 = 三个模型预测值的方差<br/>
        动态阈值 = 历史一致性分布的80%分位数<br/><br/>
        
        <b>第四步：选股决策</b><br/>
        防御模式（一致性>阈值）：先选一致性高，再选AI得分高<br/>
        进攻模式（一致性≤阈值）：直接选AI得分高<br/><br/>
        
        <b>第五步：组合构建</b><br/>
        持仓数量：10只股票<br/>
        调仓频率：月度<br/>
        权重分配：等权
        """
        story.append(Paragraph(process_text, normal_style))
        
        story.append(Spacer(1, 15))
        story.append(Paragraph("七、风险提示", heading_style))
        
        risk_text = """
        1. 本策略基于历史数据回测，过往业绩不代表未来表现。<br/>
        2. 量化策略可能存在过拟合风险，实盘表现可能与回测存在差异。<br/>
        3. 策略未考虑交易成本、滑点等实际交易因素。<br/>
        4. 股票投资存在风险，投资者应根据自身情况谨慎决策。
        """
        story.append(Paragraph(risk_text, normal_style))
        
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        
        doc.build(story)
        
        print(f"\n  ✓ PDF报告已生成: {output_path}")
        
        return output_path
    
    def generate_html_report(self, output_path=None):
        """生成HTML报告"""
        if output_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(script_dir, 'backtest_report.html')
        
        try:
            generator = BacktestReportGenerator(
                strategy_name='AI多模型因子选股策略',
                daily_values=[{'date': v['date'], 'total_value': v['value'], 
                              'cash': v['cash'], 'position_value': v['value'] - v['cash']} 
                             for v in self.daily_values],
                trade_records=[{'date': t['date'], 'action': t['action'], 
                               'code': t['stock'], 'name': t['stock'],
                               'price': t['price'], 'amount': t['amount'],
                               'value': t['value']} 
                              for t in self.trade_history],
                start_date=self.daily_values[0]['date'].strftime('%Y-%m-%d') if self.daily_values else None,
                end_date=self.daily_values[-1]['date'].strftime('%Y-%m-%d') if self.daily_values else None,
                initial_cash=self.initial_capital
            )
            generator.generate_html_report(output_path)
            print(f"  ✓ HTML报告已生成: {output_path}")
        except Exception as e:
            print(f"  ✗ HTML报告生成失败: {e}")


def main():
    """主函数"""
    print("\n" + "═" * 70)
    print("  AI多模型因子选股策略 - 本地回测系统")
    print("═" * 70)
    
    strategy = AIPortfolioStrategy(
        initial_capital=1000000,
        stock_num=10,
        use_cache=True,
        max_workers=5
    )
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*2)
    
    strategy.run_backtest(start_date, end_date)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    strategy.generate_html_report(os.path.join(script_dir, 'backtest_report.html'))
    
    strategy.generate_pdf_report(os.path.join(script_dir, 'backtest_report.pdf'))
    
    print("\n" + "═" * 70)
    print("  回测完成！")
    print("═" * 70)


if __name__ == "__main__":
    main()
