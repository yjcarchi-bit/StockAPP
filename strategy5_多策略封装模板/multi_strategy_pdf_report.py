#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
多策略PDF报告生成器

功能：
1. 生成专业PDF报告
2. 支持中文字体
3. 多策略净值对比
4. 各策略收益贡献分析
5. 策略表现统计表
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties
import matplotlib.patches as mpatches

plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti', 'Heiti TC', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


class MultiStrategyPDFReport:
    """
    多策略PDF报告生成器
    
    生成专业的PDF报告，包含多策略对比图表
    """
    
    COLORS = {
        'primary': '#1e3a8a',
        'secondary': '#3b82f6',
        'success': '#22c55e',
        'warning': '#f59e0b',
        'danger': '#ef4444',
        'purple': '#8b5cf6',
        'pink': '#ec4899',
        'gray': '#6b7280',
        'light': '#f1f5f9',
        'dark': '#1e293b',
    }
    
    STRATEGY_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
    
    def __init__(self, strategy_name: str, daily_values: list,
                 strategy_values: dict = None,
                 strategy_configs: list = None,
                 start_date: str = None, end_date: str = None,
                 initial_cash: float = 1000000.0):
        """
        初始化报告生成器
        
        参数:
            strategy_name: 策略组合名称
            daily_values: 总体每日净值数据列表
            strategy_values: 各策略每日净值 {策略名: DataFrame}
            strategy_configs: 策略配置列表
            start_date: 回测开始日期
            end_date: 回测结束日期
            initial_cash: 初始资金
        """
        self.strategy_name = strategy_name
        self.daily_values = daily_values
        self.strategy_values = strategy_values or {}
        self.strategy_configs = strategy_configs or []
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash = initial_cash
        
        self.df = None
        self.strategy_dfs = {}
        self.stats = {}
        self.strategy_stats = {}
        
        self._prepare_data()
    
    def _prepare_data(self):
        """准备数据"""
        if len(self.daily_values) == 0:
            return
        
        self.df = pd.DataFrame(self.daily_values)
        self.df['date'] = pd.to_datetime(self.df['date'])
        self.df = self.df.sort_values('date').reset_index(drop=True)
        
        if 'total_value' in self.df.columns:
            value_col = 'total_value'
        elif 'value' in self.df.columns:
            value_col = 'value'
        else:
            value_col = self.df.columns[1]
        
        self.df['_value'] = self.df[value_col]
        
        if self.start_date is None:
            self.start_date = self.df['date'].iloc[0].strftime('%Y-%m-%d')
        if self.end_date is None:
            self.end_date = self.df['date'].iloc[-1].strftime('%Y-%m-%d')
        
        self._calculate_stats()
        
        for name, values in self.strategy_values.items():
            if len(values) > 0:
                sdf = pd.DataFrame(values)
                sdf['date'] = pd.to_datetime(sdf['date'])
                sdf = sdf.sort_values('date').reset_index(drop=True)
                self.strategy_dfs[name] = sdf
                self._calculate_strategy_stats(name, sdf)
    
    def _calculate_stats(self):
        """计算总体统计指标"""
        if self.df is None or len(self.df) == 0:
            return
        
        start_value = self.df['_value'].iloc[0]
        end_value = self.df['_value'].iloc[-1]
        total_return = (end_value - start_value) / start_value
        
        self.df['daily_return'] = self.df['_value'].pct_change()
        
        trading_days = len(self.df)
        annual_return = (1 + total_return) ** (252 / trading_days) - 1 if trading_days > 0 else 0
        annual_volatility = self.df['daily_return'].std() * np.sqrt(252)
        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
        
        max_value = self.df['_value'].expanding().max()
        self.df['_drawdown'] = (self.df['_value'] - max_value) / max_value
        max_drawdown = self.df['_drawdown'].min()
        
        win_days = (self.df['daily_return'] > 0).sum()
        total_days = len(self.df['daily_return'].dropna())
        win_rate = win_days / total_days if total_days > 0 else 0
        
        self.stats = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_cash': start_value,
            'final_value': end_value,
            'total_return': total_return * 100,
            'annual_return': annual_return * 100,
            'annual_volatility': annual_volatility * 100,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown * 100,
            'win_rate': win_rate * 100,
            'trading_days': trading_days,
        }
    
    def _calculate_strategy_stats(self, name: str, sdf: pd.DataFrame):
        """计算单个策略的统计指标"""
        if len(sdf) == 0:
            return
        
        value_col = 'total_value' if 'total_value' in sdf.columns else sdf.columns[1]
        start_value = sdf[value_col].iloc[0]
        end_value = sdf[value_col].iloc[-1]
        total_return = (end_value - start_value) / start_value if start_value > 0 else 0
        
        sdf['daily_return'] = sdf[value_col].pct_change()
        
        trading_days = len(sdf)
        annual_return = (1 + total_return) ** (252 / trading_days) - 1 if trading_days > 0 and total_return > -1 else 0
        annual_volatility = sdf['daily_return'].std() * np.sqrt(252) if trading_days > 1 else 0
        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
        
        max_value = sdf[value_col].expanding().max()
        drawdown = (sdf[value_col] - max_value) / max_value
        max_drawdown = drawdown.min()
        
        self.strategy_stats[name] = {
            'initial_cash': start_value,
            'final_value': end_value,
            'total_return': total_return * 100,
            'annual_return': annual_return * 100,
            'annual_volatility': annual_volatility * 100,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown * 100,
        }
    
    def _create_cover_page(self, pdf):
        """创建封面页"""
        fig = plt.figure(figsize=(11.69, 8.27))
        ax = fig.add_subplot(111)
        ax.axis('off')
        
        ax.add_patch(plt.Rectangle((0, 0.5), 1, 0.5, transform=ax.transAxes,
                                    facecolor=self.COLORS['primary'], zorder=0))
        
        ax.text(0.5, 0.8, self.strategy_name, transform=ax.transAxes,
                fontsize=32, fontweight='bold', color='white',
                ha='center', va='center')
        
        ax.text(0.5, 0.68, '多策略组合回测报告', transform=ax.transAxes,
                fontsize=20, color='white', alpha=0.9,
                ha='center', va='center')
        
        ax.text(0.5, 0.35, f'回测区间: {self.start_date} 至 {self.end_date}',
                transform=ax.transAxes, fontsize=14, color=self.COLORS['dark'],
                ha='center', va='center')
        
        ax.text(0.5, 0.28, f'初始资金: ¥{self.initial_cash:,.2f}',
                transform=ax.transAxes, fontsize=14, color=self.COLORS['dark'],
                ha='center', va='center')
        
        total_return = self.stats.get('total_return', 0)
        return_color = self.COLORS['success'] if total_return >= 0 else self.COLORS['danger']
        ax.text(0.5, 0.18, f'总收益率: {total_return:.2f}%',
                transform=ax.transAxes, fontsize=24, fontweight='bold',
                color=return_color, ha='center', va='center')
        
        ax.text(0.5, 0.08, f'报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                transform=ax.transAxes, fontsize=10, color=self.COLORS['gray'],
                ha='center', va='center')
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _create_summary_page(self, pdf):
        """创建摘要页"""
        fig = plt.figure(figsize=(11.69, 8.27))
        
        fig.suptitle('组合表现摘要', fontsize=20, fontweight='bold', y=0.98)
        
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3,
                              left=0.08, right=0.92, top=0.88, bottom=0.12)
        
        ax1 = fig.add_subplot(gs[0, 0])
        self._draw_key_metrics(ax1)
        
        ax2 = fig.add_subplot(gs[0, 1])
        self._draw_return_contribution(ax2)
        
        ax3 = fig.add_subplot(gs[1, :])
        self._draw_strategy_table(ax3)
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _draw_key_metrics(self, ax):
        """绘制关键指标卡片"""
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        metrics = [
            ('总收益率', f"{self.stats.get('total_return', 0):.2f}%", 
             self.COLORS['success'] if self.stats.get('total_return', 0) >= 0 else self.COLORS['danger']),
            ('年化收益率', f"{self.stats.get('annual_return', 0):.2f}%",
             self.COLORS['success'] if self.stats.get('annual_return', 0) >= 0 else self.COLORS['danger']),
            ('夏普比率', f"{self.stats.get('sharpe_ratio', 0):.2f}",
             self.COLORS['success'] if self.stats.get('sharpe_ratio', 0) >= 1 else self.COLORS['dark']),
            ('最大回撤', f"{self.stats.get('max_drawdown', 0):.2f}%", self.COLORS['danger']),
            ('年化波动率', f"{self.stats.get('annual_volatility', 0):.2f}%", self.COLORS['dark']),
            ('胜率', f"{self.stats.get('win_rate', 0):.1f}%", self.COLORS['dark']),
        ]
        
        ax.text(0.5, 0.95, '关键指标', fontsize=14, fontweight='bold',
                ha='center', va='top', transform=ax.transAxes)
        
        for i, (label, value, color) in enumerate(metrics):
            row = i // 2
            col = i % 2
            x = 0.25 + col * 0.5
            y = 0.75 - row * 0.25
            
            rect = mpatches.FancyBboxPatch((x - 0.2, y - 0.08), 0.4, 0.18,
                                            boxstyle="round,pad=0.02",
                                            facecolor=self.COLORS['light'],
                                            edgecolor=self.COLORS['gray'],
                                            linewidth=0.5,
                                            transform=ax.transAxes)
            ax.add_patch(rect)
            
            ax.text(x, y + 0.04, label, fontsize=10, color=self.COLORS['gray'],
                    ha='center', va='center', transform=ax.transAxes)
            ax.text(x, y - 0.02, value, fontsize=14, fontweight='bold', color=color,
                    ha='center', va='center', transform=ax.transAxes)
    
    def _draw_return_contribution(self, ax):
        """绘制收益贡献饼图"""
        ax.set_aspect('equal')
        
        if len(self.strategy_stats) == 0:
            ax.text(0.5, 0.5, '暂无策略数据', ha='center', va='center',
                    fontsize=12, color=self.COLORS['gray'], transform=ax.transAxes)
            ax.set_title('收益贡献占比', fontsize=12, fontweight='bold', pad=10)
            return
        
        labels = []
        values = []
        colors = []
        
        for i, (name, stats) in enumerate(self.strategy_stats.items()):
            labels.append(name)
            contribution = stats.get('final_value', 0) - stats.get('initial_cash', 0)
            values.append(max(0, contribution))
            colors.append(self.STRATEGY_COLORS[i % len(self.STRATEGY_COLORS)])
        
        if sum(values) > 0:
            wedges, texts, autotexts = ax.pie(values, labels=labels, colors=colors,
                                               autopct='%1.1f%%', startangle=90,
                                               textprops={'fontsize': 9})
            for autotext in autotexts:
                autotext.set_fontsize(8)
                autotext.set_fontweight('bold')
            ax.set_title('收益贡献占比', fontsize=12, fontweight='bold', pad=10)
        else:
            ax.text(0.5, 0.5, '无收益数据', ha='center', va='center',
                    fontsize=12, color=self.COLORS['gray'], transform=ax.transAxes)
            ax.set_title('收益贡献占比', fontsize=12, fontweight='bold', pad=10)
    
    def _draw_strategy_table(self, ax):
        """绘制策略对比表格"""
        ax.axis('off')
        
        if len(self.strategy_stats) == 0:
            ax.text(0.5, 0.5, '暂无策略数据', ha='center', va='center',
                    fontsize=14, color=self.COLORS['gray'],
                    transform=ax.transAxes)
            ax.set_title('各策略表现对比', fontsize=12, fontweight='bold', y=0.95)
            return
        
        columns = ['策略名称', '资金占比', '初始资金', '最终资金', '总收益率', '年化收益', '夏普比率', '最大回撤']
        
        cell_data = []
        for name, stats in self.strategy_stats.items():
            config = next((c for c in self.strategy_configs if c.get('name') == name), {})
            pct = config.get('pct', 0) * 100
            
            row = [
                name,
                f"{pct:.0f}%",
                f"¥{stats.get('initial_cash', 0):,.0f}",
                f"¥{stats.get('final_value', 0):,.0f}",
                f"{stats.get('total_return', 0):.2f}%",
                f"{stats.get('annual_return', 0):.2f}%",
                f"{stats.get('sharpe_ratio', 0):.2f}",
                f"{stats.get('max_drawdown', 0):.2f}%"
            ]
            cell_data.append(row)
        
        if len(cell_data) == 0:
            ax.text(0.5, 0.5, '暂无策略数据', ha='center', va='center',
                    fontsize=14, color=self.COLORS['gray'],
                    transform=ax.transAxes)
            ax.set_title('各策略表现对比', fontsize=12, fontweight='bold', y=0.95)
            return
        
        table = ax.table(cellText=cell_data, colLabels=columns,
                         loc='center', cellLoc='center',
                         colColours=[self.COLORS['primary']] * len(columns))
        
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.2, 1.8)
        
        for i in range(len(columns)):
            table[(0, i)].set_text_props(color='white', fontweight='bold')
        
        for i in range(1, len(cell_data) + 1):
            for j in range(len(columns)):
                if j == 4:
                    val = cell_data[i-1][j]
                    if val.startswith('-'):
                        table[(i, j)].set_text_props(color=self.COLORS['danger'])
                    else:
                        table[(i, j)].set_text_props(color=self.COLORS['success'])
                if j == 7:
                    table[(i, j)].set_text_props(color=self.COLORS['danger'])
        
        ax.set_title('各策略表现对比', fontsize=12, fontweight='bold', y=0.95)
    
    def _create_nav_chart_page(self, pdf):
        """创建净值曲线页"""
        fig, axes = plt.subplots(2, 1, figsize=(11.69, 8.27))
        fig.suptitle('组合净值曲线', fontsize=18, fontweight='bold', y=0.98)
        
        ax1 = axes[0]
        ax1.fill_between(self.df['date'], self.initial_cash, self.df['_value'],
                         alpha=0.3, color=self.COLORS['secondary'])
        ax1.plot(self.df['date'], self.df['_value'], color=self.COLORS['secondary'],
                 linewidth=2, label='组合净值')
        ax1.axhline(y=self.initial_cash, color=self.COLORS['gray'], linestyle='--',
                    linewidth=1, label='初始资金')
        
        ax1.set_ylabel('账户价值 (¥)', fontsize=11)
        ax1.legend(loc='upper left', fontsize=9)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        
        total_return = self.stats.get('total_return', 0)
        color = self.COLORS['success'] if total_return >= 0 else self.COLORS['danger']
        ax1.text(0.98, 0.95, f'总收益: {total_return:.2f}%',
                 transform=ax1.transAxes, fontsize=12, fontweight='bold',
                 color=color, ha='right', va='top',
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax2 = axes[1]
        for i, (name, sdf) in enumerate(self.strategy_dfs.items()):
            value_col = 'total_value' if 'total_value' in sdf.columns else sdf.columns[1]
            start_value = sdf[value_col].iloc[0]
            if start_value > 0:
                normalized = (sdf[value_col] / start_value - 1) * 100
            else:
                normalized = pd.Series([0] * len(sdf))
            
            color = self.STRATEGY_COLORS[i % len(self.STRATEGY_COLORS)]
            ax2.plot(sdf['date'], normalized, color=color, linewidth=1.5, label=name)
        
        ax2.axhline(y=0, color=self.COLORS['gray'], linestyle='--', linewidth=1)
        ax2.set_xlabel('日期', fontsize=11)
        ax2.set_ylabel('累计收益率 (%)', fontsize=11)
        ax2.legend(loc='upper left', fontsize=9, ncol=3)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _create_drawdown_chart_page(self, pdf):
        """创建回撤分析页"""
        fig, axes = plt.subplots(2, 1, figsize=(11.69, 8.27))
        fig.suptitle('回撤分析', fontsize=18, fontweight='bold', y=0.98)
        
        ax1 = axes[0]
        drawdown = self.df['_drawdown'] * 100
        ax1.fill_between(self.df['date'], 0, drawdown,
                         color=self.COLORS['danger'], alpha=0.3)
        ax1.plot(self.df['date'], drawdown, color=self.COLORS['danger'],
                 linewidth=1.5, label='组合回撤')
        
        max_dd = self.stats.get('max_drawdown', 0)
        ax1.axhline(y=max_dd, color='darkred', linestyle='--', linewidth=2,
                    label=f'最大回撤: {max_dd:.2f}%')
        
        ax1.set_ylabel('回撤 (%)', fontsize=11)
        ax1.legend(loc='lower left', fontsize=9)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        ax1.set_ylim(min(drawdown.min() * 1.1, -15), 1)
        
        ax2 = axes[1]
        for i, (name, sdf) in enumerate(self.strategy_dfs.items()):
            value_col = 'total_value' if 'total_value' in sdf.columns else sdf.columns[1]
            max_value = sdf[value_col].expanding().max()
            dd = (sdf[value_col] - max_value) / max_value * 100
            
            color = self.STRATEGY_COLORS[i % len(self.STRATEGY_COLORS)]
            ax2.plot(sdf['date'], dd, color=color, linewidth=1, label=name, alpha=0.8)
        
        ax2.axhline(y=0, color=self.COLORS['gray'], linestyle='--', linewidth=1)
        ax2.set_xlabel('日期', fontsize=11)
        ax2.set_ylabel('回撤 (%)', fontsize=11)
        ax2.legend(loc='lower left', fontsize=9, ncol=3)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _create_distribution_chart_page(self, pdf):
        """创建分布分析页"""
        fig, axes = plt.subplots(2, 2, figsize=(11.69, 8.27))
        fig.suptitle('收益分布分析', fontsize=18, fontweight='bold', y=0.98)
        
        ax1 = axes[0, 0]
        returns = self.df['daily_return'].dropna() * 100
        n, bins, patches = ax1.hist(returns, bins=30, color=self.COLORS['secondary'],
                                     alpha=0.7, edgecolor='white', linewidth=0.5)
        
        for i, patch in enumerate(patches):
            if bins[i] < 0:
                patch.set_facecolor(self.COLORS['danger'])
            else:
                patch.set_facecolor(self.COLORS['success'])
        
        mean_ret = returns.mean()
        ax1.axvline(x=mean_ret, color=self.COLORS['warning'], linestyle='--',
                    linewidth=2, label=f'均值: {mean_ret:.3f}%')
        ax1.axvline(x=0, color=self.COLORS['gray'], linestyle='-', linewidth=1)
        ax1.set_xlabel('日收益率 (%)', fontsize=10)
        ax1.set_ylabel('频次', fontsize=10)
        ax1.set_title('日收益率分布', fontsize=12, fontweight='bold')
        ax1.legend(fontsize=9)
        ax1.grid(True, alpha=0.3)
        
        ax2 = axes[0, 1]
        if 'cash' in self.df.columns:
            cash = self.df['cash']
            position_value = self.df['_value'] - cash
            ax2.stackplot(self.df['date'], cash, position_value,
                          labels=['现金', '持仓市值'],
                          colors=[self.COLORS['success'], self.COLORS['secondary']],
                          alpha=0.8)
            ax2.legend(loc='upper left', fontsize=9)
            ax2.set_ylabel('金额 (¥)', fontsize=10)
            ax2.set_title('资金分布', fontsize=12, fontweight='bold')
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        ax3 = axes[1, 0]
        df_copy = self.df.copy()
        df_copy['year_month'] = df_copy['date'].dt.to_period('M')
        monthly_returns = df_copy.groupby('year_month')['daily_return'].apply(
            lambda x: (1 + x).prod() - 1
        ) * 100
        
        colors = [self.COLORS['success'] if r >= 0 else self.COLORS['danger']
                  for r in monthly_returns.values]
        
        bars = ax3.bar(range(len(monthly_returns)), monthly_returns.values, color=colors,
                       edgecolor='white', linewidth=0.5)
        ax3.set_xticks(range(len(monthly_returns)))
        ax3.set_xticklabels([str(m) for m in monthly_returns.index], rotation=45, ha='right', fontsize=8)
        ax3.axhline(y=0, color=self.COLORS['gray'], linestyle='-', linewidth=1)
        ax3.set_xlabel('月份', fontsize=10)
        ax3.set_ylabel('月收益率 (%)', fontsize=10)
        ax3.set_title('月度收益', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')
        
        ax4 = axes[1, 1]
        window = min(20, len(self.df) // 4)
        if window >= 5:
            rolling_return = self.df['daily_return'].rolling(window=window).mean() * 252
            rolling_vol = self.df['daily_return'].rolling(window=window).std() * np.sqrt(252)
            rolling_sharpe = rolling_return / rolling_vol
            
            ax4.plot(self.df['date'], rolling_sharpe, color=self.COLORS['purple'],
                     linewidth=1.5, label=f'滚动夏普({window}日)')
            ax4.axhline(y=0, color=self.COLORS['gray'], linestyle='--', linewidth=1)
            ax4.axhline(y=1, color=self.COLORS['success'], linestyle='--', linewidth=1, alpha=0.5)
            ax4.fill_between(self.df['date'], 0, rolling_sharpe,
                             where=(rolling_sharpe >= 0), alpha=0.3, color=self.COLORS['success'])
            ax4.fill_between(self.df['date'], 0, rolling_sharpe,
                             where=(rolling_sharpe < 0), alpha=0.3, color=self.COLORS['danger'])
            ax4.legend(fontsize=9)
            ax4.set_xlabel('日期', fontsize=10)
            ax4.set_ylabel('夏普比率', fontsize=10)
            ax4.set_title('滚动夏普比率', fontsize=12, fontweight='bold')
            ax4.grid(True, alpha=0.3)
            ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _create_risk_analysis_page(self, pdf):
        """创建风险分析页"""
        fig, axes = plt.subplots(2, 2, figsize=(11.69, 8.27))
        fig.suptitle('风险分析', fontsize=18, fontweight='bold', y=0.98)
        
        has_strategy_data = len(self.strategy_stats) > 0
        
        ax1 = axes[0, 0]
        if has_strategy_data:
            strategy_names = list(self.strategy_stats.keys())
            annual_returns = [self.strategy_stats[name].get('annual_return', 0) for name in strategy_names]
            annual_vols = [self.strategy_stats[name].get('annual_volatility', 0) for name in strategy_names]
            
            colors = [self.STRATEGY_COLORS[i % len(self.STRATEGY_COLORS)] for i in range(len(strategy_names))]
            scatter = ax1.scatter(annual_vols, annual_returns, c=colors, s=200, alpha=0.7, edgecolors='white')
            
            for i, name in enumerate(strategy_names):
                ax1.annotate(name, (annual_vols[i], annual_returns[i]),
                             textcoords="offset points", xytext=(5, 5), fontsize=8)
        else:
            ax1.text(0.5, 0.5, '暂无策略数据', ha='center', va='center',
                     fontsize=12, color=self.COLORS['gray'], transform=ax1.transAxes)
        
        ax1.axhline(y=0, color=self.COLORS['gray'], linestyle='--', linewidth=1)
        ax1.set_xlabel('年化波动率 (%)', fontsize=10)
        ax1.set_ylabel('年化收益率 (%)', fontsize=10)
        ax1.set_title('风险-收益散点图', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        ax2 = axes[0, 1]
        if has_strategy_data:
            sharpe_ratios = [self.strategy_stats[name].get('sharpe_ratio', 0) for name in strategy_names]
            colors = [self.COLORS['success'] if s >= 1 else self.COLORS['warning'] if s >= 0 else self.COLORS['danger']
                      for s in sharpe_ratios]
            
            bars = ax2.barh(strategy_names, sharpe_ratios, color=colors, edgecolor='white')
            
            for i, (bar, val) in enumerate(zip(bars, sharpe_ratios)):
                ax2.text(val + 0.02, bar.get_y() + bar.get_height()/2, f'{val:.2f}',
                         va='center', fontsize=9)
        else:
            ax2.text(0.5, 0.5, '暂无策略数据', ha='center', va='center',
                     fontsize=12, color=self.COLORS['gray'], transform=ax2.transAxes)
        
        ax2.axvline(x=0, color=self.COLORS['gray'], linestyle='-', linewidth=1)
        ax2.axvline(x=1, color=self.COLORS['success'], linestyle='--', linewidth=1, alpha=0.5)
        ax2.set_xlabel('夏普比率', fontsize=10)
        ax2.set_title('策略夏普比率对比', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='x')
        
        ax3 = axes[1, 0]
        if has_strategy_data:
            max_drawdowns = [abs(self.strategy_stats[name].get('max_drawdown', 0)) for name in strategy_names]
            colors = [self.COLORS['danger'] for _ in strategy_names]
            
            bars = ax3.barh(strategy_names, max_drawdowns, color=colors, alpha=0.7, edgecolor='white')
            
            for bar, val in zip(bars, max_drawdowns):
                ax3.text(val + 0.1, bar.get_y() + bar.get_height()/2, f'{val:.2f}%',
                         va='center', fontsize=9)
        else:
            ax3.text(0.5, 0.5, '暂无策略数据', ha='center', va='center',
                     fontsize=12, color=self.COLORS['gray'], transform=ax3.transAxes)
        
        ax3.set_xlabel('最大回撤 (%)', fontsize=10)
        ax3.set_title('策略最大回撤对比', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='x')
        
        ax4 = axes[1, 1]
        returns = self.df['daily_return'].dropna() * 100
        cumulative = (1 + self.df['daily_return'].dropna()).cumprod()
        
        ax4.plot(range(len(cumulative)), cumulative.values, color=self.COLORS['secondary'],
                 linewidth=1.5, label='累计收益')
        
        running_max = cumulative.expanding().max()
        drawdowns = (cumulative - running_max) / running_max * 100
        
        ax4_twin = ax4.twinx()
        ax4_twin.fill_between(range(len(drawdowns)), 0, drawdowns.values,
                              color=self.COLORS['danger'], alpha=0.3, label='回撤')
        ax4_twin.set_ylabel('回撤 (%)', fontsize=10, color=self.COLORS['danger'])
        
        ax4.set_xlabel('交易日', fontsize=10)
        ax4.set_ylabel('累计净值', fontsize=10)
        ax4.set_title('累计收益与回撤', fontsize=12, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        ax4.legend(loc='upper left', fontsize=9)
        ax4_twin.legend(loc='lower left', fontsize=9)
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def generate_pdf_report(self, output_path: str = 'multi_strategy_report.pdf') -> str:
        """
        生成PDF报告
        
        参数:
            output_path: 输出文件路径
        
        返回:
            生成的文件路径
        """
        if self.df is None or len(self.df) == 0:
            print("无数据，无法生成报告")
            return None
        
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with PdfPages(output_path) as pdf:
            self._create_cover_page(pdf)
            self._create_summary_page(pdf)
            self._create_nav_chart_page(pdf)
            self._create_drawdown_chart_page(pdf)
            self._create_distribution_chart_page(pdf)
            self._create_risk_analysis_page(pdf)
        
        print(f"\n📄 PDF报告已生成: {output_path}")
        return output_path


def generate_pdf_report_from_csv(csv_path: str, output_path: str = None,
                                  strategy_name: str = '多策略组合'):
    """
    从CSV文件生成PDF报告
    
    参数:
        csv_path: CSV文件路径
        output_path: 输出PDF路径
        strategy_name: 策略名称
    """
    df = pd.read_csv(csv_path)
    
    daily_values = df.to_dict('records')
    
    if output_path is None:
        base_dir = os.path.dirname(csv_path)
        output_path = os.path.join(base_dir, 'backtest_report.pdf')
    
    report = MultiStrategyPDFReport(
        strategy_name=strategy_name,
        daily_values=daily_values,
        initial_cash=daily_values[0].get('total_value', 1000000)
    )
    
    return report.generate_pdf_report(output_path)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        generate_pdf_report_from_csv(csv_path)
    else:
        print("用法: python multi_strategy_pdf_report.py <csv_path>")
