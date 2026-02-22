#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
回测结果可视化工具

功能：
1. 读取回测生成的CSV文件
2. 生成多种图表：净值曲线、回撤曲线、持仓变化、买卖点标记
3. 支持静态图片(matplotlib)和交互式HTML(plotly)两种输出

使用方法：
    python backtest_visualizer.py
    python backtest_visualizer.py --daily backtest_daily_values_strategy1.csv --trades backtest_trade_records_strategy1.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import argparse
import os
from datetime import datetime

plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class BacktestVisualizer:
    """
    回测可视化类
    
    支持生成多种图表展示回测结果
    """
    
    def __init__(self, daily_file: str = None, trades_file: str = None):
        """
        初始化可视化器
        
        参数:
            daily_file: 每日净值CSV文件路径
            trades_file: 交易记录CSV文件路径
        """
        self.daily_df = None
        self.trades_df = None
        
        if daily_file and os.path.exists(daily_file):
            self.daily_df = pd.read_csv(daily_file)
            self.daily_df['date'] = pd.to_datetime(self.daily_df['date'])
            print(f"已加载每日净值数据: {len(self.daily_df)} 条记录")
        
        if trades_file and os.path.exists(trades_file):
            self.trades_df = pd.read_csv(trades_file)
            self.trades_df['date'] = pd.to_datetime(self.trades_df['date'])
            print(f"已加载交易记录: {len(self.trades_df)} 条记录")
    
    def plot_matplotlib_static(self, save_path: str = 'backtest_chart.png'):
        """
        使用matplotlib生成静态图表
        
        参数:
            save_path: 图片保存路径
        """
        if self.daily_df is None:
            print("错误: 未加载每日净值数据")
            return
        
        fig = plt.figure(figsize=(16, 12))
        gs = GridSpec(4, 2, figure=fig, height_ratios=[2, 1, 1, 1])
        
        ax1 = fig.add_subplot(gs[0, :])
        ax2 = fig.add_subplot(gs[1, :])
        ax3 = fig.add_subplot(gs[2, 0])
        ax4 = fig.add_subplot(gs[2, 1])
        ax5 = fig.add_subplot(gs[3, :])
        
        self._plot_nav_curve(ax1)
        self._plot_drawdown(ax2)
        self._plot_position_count(ax3)
        self._plot_cash_vs_position(ax4)
        self._plot_daily_return_dist(ax5)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight', 
                    facecolor='white', edgecolor='none')
        print(f"静态图表已保存: {save_path}")
        plt.close()
    
    def _plot_nav_curve(self, ax):
        """绑制净值曲线"""
        dates = self.daily_df['date']
        nav = self.daily_df['total_value']
        
        ax.fill_between(dates, nav, alpha=0.3, color='steelblue')
        ax.plot(dates, nav, color='steelblue', linewidth=1.5, label='账户净值')
        
        if self.trades_df is not None and len(self.trades_df) > 0:
            buy_trades = self.trades_df[self.trades_df['action'] == 'buy']
            sell_trades = self.trades_df[self.trades_df['action'] == 'sell']
            
            for _, trade in buy_trades.iterrows():
                ax.axvline(x=trade['date'], color='green', alpha=0.3, linewidth=0.5)
            
            for _, trade in sell_trades.iterrows():
                ax.axvline(x=trade['date'], color='red', alpha=0.3, linewidth=0.5)
        
        ax.set_title('净值曲线', fontsize=14, fontweight='bold')
        ax.set_ylabel('账户价值 (元)')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')
        
        start_nav = nav.iloc[0]
        end_nav = nav.iloc[-1]
        total_return = (end_nav - start_nav) / start_nav * 100
        ax.annotate(f'总收益: {total_return:.2f}%', 
                    xy=(0.98, 0.95), xycoords='axes fraction',
                    ha='right', va='top', fontsize=12,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    def _plot_drawdown(self, ax):
        """绑制回撤曲线"""
        dates = self.daily_df['date']
        drawdown = self.daily_df['drawdown'] * 100
        
        ax.fill_between(dates, drawdown, 0, color='indianred', alpha=0.5)
        ax.plot(dates, drawdown, color='indianred', linewidth=1)
        
        ax.set_title('回撤曲线', fontsize=12, fontweight='bold')
        ax.set_ylabel('回撤 (%)')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        ax.grid(True, alpha=0.3)
        ax.invert_yaxis()
        
        max_dd = drawdown.max()
        ax.axhline(y=max_dd, color='darkred', linestyle='--', alpha=0.7)
        ax.annotate(f'最大回撤: {max_dd:.2f}%', 
                    xy=(0.98, max_dd), xycoords=('axes fraction', 'data'),
                    ha='right', va='bottom', fontsize=10,
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    def _plot_position_count(self, ax):
        """绑制持仓数量变化"""
        dates = self.daily_df['date']
        pos_count = self.daily_df['position_count']
        
        colors = ['green' if c > 0 else 'gray' for c in pos_count]
        ax.bar(dates, pos_count, color=colors, alpha=0.7, width=0.8)
        
        ax.set_title('持仓数量', fontsize=12, fontweight='bold')
        ax.set_ylabel('持仓股数')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        ax.grid(True, alpha=0.3, axis='y')
    
    def _plot_cash_vs_position(self, ax):
        """绑制现金与持仓市值对比"""
        dates = self.daily_df['date']
        cash = self.daily_df['cash']
        position_value = self.daily_df['position_value']
        
        ax.stackplot(dates, cash, position_value, 
                     labels=['现金', '持仓市值'],
                     colors=['lightgreen', 'steelblue'], alpha=0.7)
        
        ax.set_title('资金分布', fontsize=12, fontweight='bold')
        ax.set_ylabel('金额 (元)')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')
    
    def _plot_daily_return_dist(self, ax):
        """绑制日收益率分布"""
        self.daily_df['daily_return'] = self.daily_df['total_value'].pct_change()
        returns = self.daily_df['daily_return'].dropna() * 100
        
        ax.hist(returns, bins=30, color='steelblue', alpha=0.7, edgecolor='white')
        ax.axvline(x=0, color='red', linestyle='--', linewidth=1)
        
        mean_ret = returns.mean()
        ax.axvline(x=mean_ret, color='green', linestyle='-', linewidth=2)
        
        ax.set_title('日收益率分布', fontsize=12, fontweight='bold')
        ax.set_xlabel('日收益率 (%)')
        ax.set_ylabel('频次')
        ax.grid(True, alpha=0.3)
        
        ax.annotate(f'均值: {mean_ret:.3f}%\n标准差: {returns.std():.3f}%', 
                    xy=(0.98, 0.95), xycoords='axes fraction',
                    ha='right', va='top', fontsize=10,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    def generate_summary_stats(self) -> dict:
        """
        计算并返回回测统计指标
        
        返回:
            统计指标字典
        """
        if self.daily_df is None:
            return {}
        
        df = self.daily_df.copy()
        start_value = df['total_value'].iloc[0]
        end_value = df['total_value'].iloc[-1]
        total_return = (end_value - start_value) / start_value
        
        df['daily_return'] = df['total_value'].pct_change()
        annual_return = (1 + df['daily_return'].mean()) ** 252 - 1
        annual_volatility = df['daily_return'].std() * np.sqrt(252)
        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
        
        max_drawdown = df['drawdown'].max()
        
        win_days = (df['daily_return'] > 0).sum()
        total_days = len(df['daily_return'].dropna())
        win_rate = win_days / total_days if total_days > 0 else 0
        
        stats = {
            '初始资金': f'{start_value:,.2f}',
            '最终资金': f'{end_value:,.2f}',
            '总收益率': f'{total_return*100:.2f}%',
            '年化收益率': f'{annual_return*100:.2f}%',
            '年化波动率': f'{annual_volatility*100:.2f}%',
            '夏普比率': f'{sharpe_ratio:.2f}',
            '最大回撤': f'{max_drawdown*100:.2f}%',
            '胜率': f'{win_rate*100:.2f}%',
            '回测天数': total_days
        }
        
        if self.trades_df is not None and len(self.trades_df) > 0:
            stats['交易次数'] = len(self.trades_df)
            stats['买入次数'] = len(self.trades_df[self.trades_df['action'] == 'buy'])
            stats['卖出次数'] = len(self.trades_df[self.trades_df['action'] == 'sell'])
            stats['总手续费'] = f'{self.trades_df["commission"].sum():,.2f}'
        
        return stats


def main():
    parser = argparse.ArgumentParser(description='回测结果可视化工具')
    parser.add_argument('--daily', type=str, 
                        default='backtest_daily_values_strategy1.csv',
                        help='每日净值CSV文件路径')
    parser.add_argument('--trades', type=str,
                        default='backtest_trade_records_strategy1.csv',
                        help='交易记录CSV文件路径')
    parser.add_argument('--output', type=str,
                        default='backtest_chart.png',
                        help='输出图片路径')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("回测结果可视化")
    print("=" * 50)
    
    visualizer = BacktestVisualizer(args.daily, args.trades)
    
    print("\n统计指标:")
    print("-" * 30)
    stats = visualizer.generate_summary_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print("\n生成静态图表...")
    visualizer.plot_matplotlib_static(args.output)


if __name__ == '__main__':
    main()
