#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
ETF策略PDF报告生成器 - 优化版

功能：
1. 生成专业PDF报告
2. 支持中文字体
3. 策略逻辑和框架说明页
4. ETF轮动进程可视化
5. 收益贡献分析
6. 持仓变化追踪
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
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection
from matplotlib.lines import Line2D

plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti', 'Heiti TC', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


class ETFStrategyPDFReport:
    """
    ETF策略PDF报告生成器 - 优化版
    
    生成专业的PDF报告，包含策略说明和ETF轮动分析图表
    """
    
    COLORS = {
        'primary': '#1e40af',
        'secondary': '#3b82f6',
        'success': '#16a34a',
        'warning': '#ca8a04',
        'danger': '#dc2626',
        'purple': '#9333ea',
        'pink': '#db2777',
        'cyan': '#0891b2',
        'orange': '#ea580c',
        'gray': '#6b7280',
        'light': '#f3f4f6',
        'dark': '#1f2937',
        'gold': '#d97706',
        'teal': '#0d9488',
    }
    
    ETF_COLORS = {
        '159915': '#3b82f6',
        '518880': '#d97706',
        '513100': '#22c55e',
        '511220': '#6b7280',
        '511880': '#94a3b8',
        '159980': '#8b5cf6',
        '159985': '#ec4899',
        '501018': '#f59e0b',
        '513500': '#14b8a6',
        '513520': '#f97316',
        '513030': '#84cc16',
        '513080': '#06b6d4',
        '159920': '#a855f7',
        '510300': '#ef4444',
        '510500': '#f97316',
        '510050': '#22c55e',
        '510210': '#3b82f6',
        '588080': '#ec4899',
        '159995': '#8b5cf6',
        '513050': '#06b6d4',
        '159852': '#f59e0b',
        '159845': '#22c55e',
        '515030': '#3b82f6',
        '159806': '#fbbf24',
        '516160': '#a3e635',
        '159928': '#f472b6',
        '512670': '#c084fc',
        '511010': '#94a3b8',
    }
    
    ETF_NAMES = {
        "159915": "创业板ETF",
        "518880": "黄金ETF",
        "513100": "纳指ETF",
        "511220": "城投债ETF",
        "159980": "有色ETF",
        "159985": "豆粕ETF",
        "501018": "南方原油LOF",
        "513500": "标普500ETF",
        "513520": "日经ETF",
        "513030": "德国ETF",
        "513080": "法国ETF",
        "159920": "恒生ETF",
        "510300": "沪深300ETF",
        "510500": "中证500ETF",
        "510050": "上证50ETF",
        "510210": "上证指数ETF",
        "588080": "科创板50ETF",
        "159995": "芯片ETF",
        "513050": "中概互联ETF",
        "159852": "半导体ETF",
        "159845": "新能源ETF",
        "515030": "新能源车ETF",
        "159806": "光伏ETF",
        "516160": "新能源ETF",
        "159928": "消费ETF",
        "512670": "国防军工ETF",
        "511010": "国债ETF",
        "511880": "银华日利",
    }
    
    def __init__(self, strategy_name: str, daily_values: list,
                 trade_records: list = None,
                 start_date: str = None, end_date: str = None,
                 initial_cash: float = 100000.0,
                 etf_pool: list = None):
        """
        初始化报告生成器
        
        参数:
            strategy_name: 策略名称
            daily_values: 每日净值数据列表
            trade_records: 交易记录列表
            start_date: 回测开始日期
            end_date: 回测结束日期
            initial_cash: 初始资金
            etf_pool: ETF池列表
        """
        self.strategy_name = strategy_name
        self.daily_values = daily_values
        self.trade_records = trade_records or []
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash = initial_cash
        self.etf_pool = etf_pool or []
        
        self.df = None
        self.trades_df = None
        self.stats = {}
        self.etf_stats = {}
        self.holding_periods = []
        
        self._prepare_data()
    
    def _get_etf_name(self, code):
        """获取ETF名称"""
        return self.ETF_NAMES.get(str(code), str(code))
    
    def _get_etf_color(self, code):
        """获取ETF颜色"""
        return self.ETF_COLORS.get(str(code), self.COLORS['secondary'])
    
    def _prepare_data(self):
        """准备数据"""
        if len(self.daily_values) == 0:
            return
        
        self.df = pd.DataFrame(self.daily_values)
        
        if 'date' in self.df.columns:
            if not pd.api.types.is_datetime64_any_dtype(self.df['date']):
                self.df['date'] = pd.to_datetime(self.df['date'])
        elif self.df.columns[0] == 'date':
            self.df['date'] = pd.to_datetime(self.df.iloc[:, 0])
        
        self.df = self.df.sort_values('date').reset_index(drop=True)
        
        if 'total_value' in self.df.columns:
            value_col = 'total_value'
        elif 'value' in self.df.columns:
            value_col = 'value'
        else:
            value_col = self.df.columns[1] if len(self.df.columns) > 1 else self.df.columns[0]
        
        self.df['_value'] = self.df[value_col]
        
        if self.start_date is None:
            self.start_date = self.df['date'].iloc[0].strftime('%Y-%m-%d')
        if self.end_date is None:
            self.end_date = self.df['date'].iloc[-1].strftime('%Y-%m-%d')
        
        self._calculate_stats()
        
        if len(self.trade_records) > 0:
            self.trades_df = pd.DataFrame(self.trade_records)
            if 'date' in self.trades_df.columns:
                if not pd.api.types.is_datetime64_any_dtype(self.trades_df['date']):
                    self.trades_df['date'] = pd.to_datetime(self.trades_df['date'])
            self._calculate_etf_stats()
            self._calculate_holding_periods()
    
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
        sharpe_ratio = (annual_return - 0.03) / annual_volatility if annual_volatility > 0 else 0
        
        max_value = self.df['_value'].expanding().max()
        self.df['_drawdown'] = (self.df['_value'] - max_value) / max_value
        max_drawdown = self.df['_drawdown'].min()
        
        win_days = (self.df['daily_return'] > 0).sum()
        total_days = len(self.df['daily_return'].dropna())
        win_rate = win_days / total_days if total_days > 0 else 0
        
        returns = self.df['daily_return'].dropna()
        if len(returns) > 0:
            positive_returns = returns[returns > 0]
            negative_returns = returns[returns < 0]
            avg_win = positive_returns.mean() * 100 if len(positive_returns) > 0 else 0
            avg_loss = negative_returns.mean() * 100 if len(negative_returns) > 0 else 0
            profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        else:
            avg_win = 0
            avg_loss = 0
            profit_loss_ratio = 0
        
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
            'trade_count': len(self.trade_records),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_loss_ratio': profit_loss_ratio,
        }
    
    def _calculate_etf_stats(self):
        """计算各ETF的统计指标"""
        if self.trades_df is None or len(self.trades_df) == 0:
            return
        
        if 'code' not in self.trades_df.columns and 'etf' not in self.trades_df.columns:
            return
        
        code_col = 'code' if 'code' in self.trades_df.columns else 'etf'
        
        for code in self.trades_df[code_col].unique():
            etf_trades = self.trades_df[self.trades_df[code_col] == code]
            
            buys = etf_trades[etf_trades['action'] == 'buy'] if 'action' in etf_trades.columns else etf_trades
            sells = etf_trades[etf_trades['action'] == 'sell'] if 'action' in etf_trades.columns else pd.DataFrame()
            
            total_buy_value = buys['value'].sum() if 'value' in buys.columns and len(buys) > 0 else 0
            total_sell_value = sells['value'].sum() if 'value' in sells.columns and len(sells) > 0 else 0
            
            self.etf_stats[str(code)] = {
                'name': self._get_etf_name(code),
                'trade_count': len(etf_trades),
                'buy_count': len(buys),
                'sell_count': len(sells),
                'total_buy_value': total_buy_value,
                'total_sell_value': total_sell_value,
                'net_value': total_sell_value - total_buy_value,
            }
    
    def _calculate_holding_periods(self):
        """计算各ETF的持仓周期"""
        if self.trades_df is None or len(self.trades_df) == 0:
            return
        
        code_col = 'code' if 'code' in self.trades_df.columns else 'etf'
        
        for code in self.trades_df[code_col].unique():
            etf_trades = self.trades_df[self.trades_df[code_col] == code].sort_values('date')
            
            buys = etf_trades[etf_trades['action'] == 'buy']
            sells = etf_trades[etf_trades['action'] == 'sell']
            
            for i, buy in buys.iterrows():
                matching_sells = sells[sells['date'] > buy['date']]
                if len(matching_sells) > 0:
                    sell = matching_sells.iloc[0]
                    holding_days = (sell['date'] - buy['date']).days
                    self.holding_periods.append({
                        'etf': code,
                        'name': self._get_etf_name(code),
                        'start_date': buy['date'],
                        'end_date': sell['date'],
                        'holding_days': holding_days,
                        'buy_value': buy.get('value', 0),
                        'sell_value': sell.get('value', 0),
                        'profit': sell.get('value', 0) - buy.get('value', 0),
                    })
    
    def _create_cover_page(self, pdf):
        """创建封面页"""
        fig = plt.figure(figsize=(11.69, 8.27))
        ax = fig.add_subplot(111)
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        ax.add_patch(FancyBboxPatch((0, 0.5), 1, 0.5,
                                     boxstyle="square",
                                     facecolor=self.COLORS['primary'],
                                     edgecolor='none',
                                     transform=ax.transAxes, zorder=0))
        
        ax.text(0.5, 0.8, self.strategy_name, transform=ax.transAxes,
                fontsize=28, fontweight='bold', color='white',
                ha='center', va='center', zorder=1)
        
        ax.text(0.5, 0.68, 'ETF收益率稳定性轮动策略回测报告', transform=ax.transAxes,
                fontsize=16, color='white', alpha=0.9,
                ha='center', va='center', zorder=1)
        
        ax.add_patch(FancyBboxPatch((0.15, 0.12), 0.7, 0.35,
                                     boxstyle="round,pad=0.02",
                                     facecolor='white',
                                     edgecolor=self.COLORS['light'],
                                     linewidth=2,
                                     transform=ax.transAxes, zorder=1))
        
        info_items = [
            ('回测区间', f'{self.start_date} 至 {self.end_date}'),
            ('初始资金', f'¥{self.initial_cash:,.2f}'),
            ('交易次数', f'{self.stats.get("trade_count", 0)} 次'),
        ]
        
        y_pos = 0.42
        for label, value in info_items:
            ax.text(0.5, y_pos, f'{label}: {value}', transform=ax.transAxes,
                    fontsize=12, color=self.COLORS['dark'],
                    ha='center', va='center', zorder=2)
            y_pos -= 0.05
        
        total_return = self.stats.get('total_return', 0)
        return_color = self.COLORS['success'] if total_return >= 0 else self.COLORS['danger']
        ax.text(0.5, 0.20, f'总收益率: {total_return:+.2f}%',
                transform=ax.transAxes, fontsize=22, fontweight='bold',
                color=return_color, ha='center', va='center', zorder=2)
        
        ax.text(0.5, 0.05, f'报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                transform=ax.transAxes, fontsize=9, color=self.COLORS['gray'],
                ha='center', va='center', zorder=2)
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _create_strategy_logic_page(self, pdf):
        """创建策略逻辑说明页"""
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.suptitle('策略逻辑与框架', fontsize=20, fontweight='bold', y=0.98)
        
        gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.2,
                              left=0.06, right=0.94, top=0.90, bottom=0.06)
        
        ax1 = fig.add_subplot(gs[0, :])
        self._draw_strategy_overview(ax1)
        
        ax2 = fig.add_subplot(gs[1, 0])
        self._draw_scoring_logic(ax2)
        
        ax3 = fig.add_subplot(gs[1, 1])
        self._draw_filter_logic(ax3)
        
        ax4 = fig.add_subplot(gs[2, 0])
        self._draw_stop_loss_logic(ax4)
        
        ax5 = fig.add_subplot(gs[2, 1])
        self._draw_etf_pool_info(ax5)
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _draw_strategy_overview(self, ax):
        """绘制策略概述"""
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        ax.add_patch(FancyBboxPatch((0.02, 0.05), 0.96, 0.9,
                                     boxstyle="round,pad=0.02",
                                     facecolor=self.COLORS['light'],
                                     edgecolor=self.COLORS['primary'],
                                     linewidth=2,
                                     transform=ax.transAxes))
        
        ax.text(0.5, 0.88, '策略核心思想', fontsize=14, fontweight='bold',
                ha='center', va='center', color=self.COLORS['primary'],
                transform=ax.transAxes)
        
        strategy_desc = [
            "本策略基于动量轮动原理，通过加权线性回归计算ETF的收益率稳定性得分",
            "选择动量得分最高的ETF进行持仓，实现资产的动态配置",
            "结合多种过滤条件和止损机制，控制风险敞口"
        ]
        
        y_pos = 0.72
        for desc in strategy_desc:
            ax.text(0.08, y_pos, f"• {desc}", fontsize=10,
                    ha='left', va='center', color=self.COLORS['dark'],
                    transform=ax.transAxes)
            y_pos -= 0.12
        
        ax.text(0.5, 0.35, '策略流程', fontsize=12, fontweight='bold',
                ha='center', va='center', color=self.COLORS['primary'],
                transform=ax.transAxes)
        
        steps = [
            ("1. 数据获取", "获取ETF池中所有ETF的历史行情数据"),
            ("2. 指标计算", "计算动量得分、短期动量、技术指标等"),
            ("3. 过滤筛选", "应用短期动量、跌幅等过滤条件"),
            ("4. 排名选股", "选择得分最高的ETF"),
            ("5. 仓位调整", "卖出非目标ETF，买入目标ETF"),
            ("6. 风险控制", "执行止损检查，控制回撤")
        ]
        
        x_positions = [0.08, 0.25, 0.42, 0.59, 0.76, 0.93]
        for i, (title, desc) in enumerate(steps):
            x = (i % 3) * 0.32 + 0.16
            y = 0.22 if i < 3 else 0.08
            
            ax.add_patch(Circle((x, y), 0.025, facecolor=self.COLORS['secondary'],
                                 edgecolor='white', linewidth=1, transform=ax.transAxes))
            ax.text(x, y, str(i+1), fontsize=10, fontweight='bold', color='white',
                    ha='center', va='center', transform=ax.transAxes)
            ax.text(x + 0.04, y, title, fontsize=9, fontweight='bold',
                    ha='left', va='center', color=self.COLORS['dark'],
                    transform=ax.transAxes)
    
    def _draw_scoring_logic(self, ax):
        """绘制动量得分计算逻辑"""
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        ax.add_patch(FancyBboxPatch((0.02, 0.02), 0.96, 0.96,
                                     boxstyle="round,pad=0.02",
                                     facecolor='white',
                                     edgecolor=self.COLORS['secondary'],
                                     linewidth=2,
                                     transform=ax.transAxes))
        
        ax.text(0.5, 0.92, '动量得分计算', fontsize=12, fontweight='bold',
                ha='center', va='center', color=self.COLORS['secondary'],
                transform=ax.transAxes)
        
        formula_box = FancyBboxPatch((0.1, 0.65), 0.8, 0.2,
                                      boxstyle="round,pad=0.02",
                                      facecolor=self.COLORS['light'],
                                      edgecolor=self.COLORS['gray'],
                                      transform=ax.transAxes)
        ax.add_patch(formula_box)
        
        ax.text(0.5, 0.78, '得分 = 年化收益率 × R²', fontsize=14, fontweight='bold',
                ha='center', va='center', color=self.COLORS['primary'],
                transform=ax.transAxes)
        
        ax.text(0.5, 0.68, '(加权线性回归计算)', fontsize=10,
                ha='center', va='center', color=self.COLORS['gray'],
                transform=ax.transAxes)
        
        details = [
            "• 回看天数: 25天",
            "• 权重: 线性递增(近期权重更高)",
            "• 年化: slope × 250",
            "• R²: 拟合优度(稳定性)"
        ]
        
        y_pos = 0.52
        for detail in details:
            ax.text(0.1, y_pos, detail, fontsize=9,
                    ha='left', va='center', color=self.COLORS['dark'],
                    transform=ax.transAxes)
            y_pos -= 0.1
        
        ax.text(0.5, 0.12, '短期动量过滤: 近12日涨幅 ≥ 0',
                fontsize=9, ha='center', va='center',
                color=self.COLORS['warning'], style='italic',
                transform=ax.transAxes)
    
    def _draw_filter_logic(self, ax):
        """绘制过滤条件逻辑"""
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        ax.add_patch(FancyBboxPatch((0.02, 0.02), 0.96, 0.96,
                                     boxstyle="round,pad=0.02",
                                     facecolor='white',
                                     edgecolor=self.COLORS['warning'],
                                     linewidth=2,
                                     transform=ax.transAxes))
        
        ax.text(0.5, 0.92, '过滤条件', fontsize=12, fontweight='bold',
                ha='center', va='center', color=self.COLORS['warning'],
                transform=ax.transAxes)
        
        filters = [
            ("短期动量过滤", "近12日涨幅 < 0 → 排除", self.COLORS['danger']),
            ("跌幅过滤", "近3日任一单日跌幅 > 3% → 排除", self.COLORS['danger']),
            ("得分范围", "得分 ≤ 0 或 > 6 → 排除", self.COLORS['danger']),
            ("防御模式", "无合格ETF → 持有城投债ETF", self.COLORS['teal']),
        ]
        
        y_pos = 0.78
        for title, desc, color in filters:
            ax.add_patch(Circle((0.08, y_pos), 0.02, facecolor=color,
                                 edgecolor='white', linewidth=1, transform=ax.transAxes))
            ax.text(0.15, y_pos, title, fontsize=10, fontweight='bold',
                    ha='left', va='center', color=self.COLORS['dark'],
                    transform=ax.transAxes)
            ax.text(0.15, y_pos - 0.06, desc, fontsize=8,
                    ha='left', va='center', color=self.COLORS['gray'],
                    transform=ax.transAxes)
            y_pos -= 0.18
    
    def _draw_stop_loss_logic(self, ax):
        """绘制止损逻辑"""
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        ax.add_patch(FancyBboxPatch((0.02, 0.02), 0.96, 0.96,
                                     boxstyle="round,pad=0.02",
                                     facecolor='white',
                                     edgecolor=self.COLORS['danger'],
                                     linewidth=2,
                                     transform=ax.transAxes))
        
        ax.text(0.5, 0.92, '止损机制', fontsize=12, fontweight='bold',
                ha='center', va='center', color=self.COLORS['danger'],
                transform=ax.transAxes)
        
        stop_loss_items = [
            ("固定止损", "亏损 > 5% → 卖出", "成本价 × 0.95"),
            ("ATR止损", "价格 < 成本 - 2×ATR → 卖出", "动态跟踪止损"),
        ]
        
        y_pos = 0.75
        for title, desc, formula in stop_loss_items:
            ax.text(0.1, y_pos, f"● {title}", fontsize=10, fontweight='bold',
                    ha='left', va='center', color=self.COLORS['dark'],
                    transform=ax.transAxes)
            ax.text(0.15, y_pos - 0.08, desc, fontsize=9,
                    ha='left', va='center', color=self.COLORS['gray'],
                    transform=ax.transAxes)
            ax.text(0.15, y_pos - 0.15, f"公式: {formula}", fontsize=8,
                    ha='left', va='center', color=self.COLORS['primary'],
                    style='italic', transform=ax.transAxes)
            y_pos -= 0.28
        
        ax.text(0.5, 0.15, 'ATR周期: 14天 | ATR倍数: 2',
                fontsize=9, ha='center', va='center',
                color=self.COLORS['gray'], transform=ax.transAxes)
    
    def _draw_etf_pool_info(self, ax):
        """绘制ETF池信息"""
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        ax.add_patch(FancyBboxPatch((0.02, 0.02), 0.96, 0.96,
                                     boxstyle="round,pad=0.02",
                                     facecolor='white',
                                     edgecolor=self.COLORS['success'],
                                     linewidth=2,
                                     transform=ax.transAxes))
        
        ax.text(0.5, 0.92, 'ETF池配置', fontsize=12, fontweight='bold',
                ha='center', va='center', color=self.COLORS['success'],
                transform=ax.transAxes)
        
        etf_categories = {
            '商品类': ['518880(黄金)', '159980(有色)', '159985(豆粕)', '501018(原油)'],
            '海外类': ['513100(纳指)', '513500(标普)', '513520(日经)', '513030(德国)'],
            'A股类': ['159915(创业板)', '510300(沪深300)', '510500(中证500)', '588080(科创板)'],
            '债券类': ['511220(城投债)', '511880(银华日利)', '511010(国债)'],
        }
        
        y_pos = 0.78
        for category, etfs in etf_categories.items():
            ax.text(0.08, y_pos, f"● {category}:", fontsize=9, fontweight='bold',
                    ha='left', va='center', color=self.COLORS['dark'],
                    transform=ax.transAxes)
            etf_text = ' | '.join(etfs)
            ax.text(0.08, y_pos - 0.06, etf_text, fontsize=7,
                    ha='left', va='center', color=self.COLORS['gray'],
                    transform=ax.transAxes)
            y_pos -= 0.16
        
        ax.text(0.5, 0.12, f'ETF池总数: {len(self.etf_pool)} 只' if self.etf_pool else 'ETF池总数: 多只',
                fontsize=9, ha='center', va='center',
                color=self.COLORS['primary'], fontweight='bold',
                transform=ax.transAxes)
    
    def _create_summary_page(self, pdf):
        """创建摘要页"""
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.suptitle('策略表现摘要', fontsize=20, fontweight='bold', y=0.98)
        
        gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.25,
                              left=0.06, right=0.94, top=0.90, bottom=0.08)
        
        ax1 = fig.add_subplot(gs[0, 0])
        self._draw_metric_card(ax1, '总收益率', f"{self.stats.get('total_return', 0):.2f}%",
                               self.COLORS['success'] if self.stats.get('total_return', 0) >= 0 else self.COLORS['danger'])
        
        ax2 = fig.add_subplot(gs[0, 1])
        self._draw_metric_card(ax2, '年化收益率', f"{self.stats.get('annual_return', 0):.2f}%",
                               self.COLORS['success'] if self.stats.get('annual_return', 0) >= 0 else self.COLORS['danger'])
        
        ax3 = fig.add_subplot(gs[0, 2])
        self._draw_metric_card(ax3, '夏普比率', f"{self.stats.get('sharpe_ratio', 0):.2f}",
                               self.COLORS['success'] if self.stats.get('sharpe_ratio', 0) >= 1 else self.COLORS['warning'])
        
        ax4 = fig.add_subplot(gs[1, 0])
        self._draw_metric_card(ax4, '最大回撤', f"{self.stats.get('max_drawdown', 0):.2f}%", self.COLORS['danger'])
        
        ax5 = fig.add_subplot(gs[1, 1])
        self._draw_metric_card(ax5, '年化波动率', f"{self.stats.get('annual_volatility', 0):.2f}%", self.COLORS['dark'])
        
        ax6 = fig.add_subplot(gs[1, 2])
        self._draw_metric_card(ax6, '胜率', f"{self.stats.get('win_rate', 0):.1f}%", self.COLORS['dark'])
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _draw_metric_card(self, ax, title, value, color):
        """绘制指标卡片"""
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        rect = FancyBboxPatch((0.05, 0.1), 0.9, 0.8,
                               boxstyle="round,pad=0.03",
                               facecolor=self.COLORS['light'],
                               edgecolor=color,
                               linewidth=3,
                               transform=ax.transAxes)
        ax.add_patch(rect)
        
        ax.text(0.5, 0.7, title, transform=ax.transAxes,
                fontsize=12, color=self.COLORS['gray'],
                ha='center', va='center')
        
        ax.text(0.5, 0.4, value, transform=ax.transAxes,
                fontsize=20, fontweight='bold', color=color,
                ha='center', va='center')
    
    def _create_etf_rotation_page(self, pdf):
        """创建ETF轮动进程页"""
        fig, axes = plt.subplots(2, 1, figsize=(11.69, 8.27))
        fig.suptitle('ETF轮动进程', fontsize=18, fontweight='bold', y=0.98)
        
        ax1 = axes[0]
        self._draw_rotation_timeline(ax1)
        
        ax2 = axes[1]
        self._draw_holding_distribution(ax2)
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _draw_rotation_timeline(self, ax):
        """绘制ETF轮动时间线"""
        if len(self.holding_periods) == 0:
            ax.text(0.5, 0.5, '暂无持仓数据', ha='center', va='center',
                    fontsize=14, color=self.COLORS['gray'], transform=ax.transAxes)
            ax.set_title('持仓时间线', fontsize=12, fontweight='bold')
            ax.axis('off')
            return
        
        ax.plot(self.df['date'], self.df['_value'], color=self.COLORS['secondary'],
                linewidth=2, alpha=0.7, label='净值曲线')
        
        for period in self.holding_periods:
            etf_code = period['etf']
            color = self._get_etf_color(etf_code)
            
            ax.axvspan(period['start_date'], period['end_date'],
                       alpha=0.15, color=color)
            
            mid_date = period['start_date'] + (period['end_date'] - period['start_date']) / 2
            
            idx = self.df[self.df['date'] <= period['start_date']].index
            if len(idx) > 0:
                y_pos = self.df.loc[idx[-1], '_value']
            else:
                y_pos = self.initial_cash
            
            ax.annotate(self._get_etf_name(etf_code),
                        xy=(mid_date, y_pos),
                        fontsize=7, ha='center', va='bottom',
                        color=color, fontweight='bold',
                        rotation=0)
        
        ax.set_ylabel('账户价值 (¥)', fontsize=11)
        ax.set_title('持仓时间线 (背景色表示持仓ETF)', fontsize=12, fontweight='bold')
        ax.legend(loc='upper left', fontsize=9)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    def _draw_holding_distribution(self, ax):
        """绘制持仓分布"""
        if len(self.holding_periods) == 0:
            ax.text(0.5, 0.5, '暂无持仓数据', ha='center', va='center',
                    fontsize=14, color=self.COLORS['gray'], transform=ax.transAxes)
            ax.set_title('各ETF持仓时间分布', fontsize=12, fontweight='bold')
            ax.axis('off')
            return
        
        etf_holding_time = {}
        for period in self.holding_periods:
            etf = period['etf']
            if etf not in etf_holding_time:
                etf_holding_time[etf] = {'days': 0, 'count': 0, 'name': period['name']}
            etf_holding_time[etf]['days'] += period['holding_days']
            etf_holding_time[etf]['count'] += 1
        
        sorted_etfs = sorted(etf_holding_time.items(), key=lambda x: x[1]['days'], reverse=True)
        
        etf_names = [f"{v['name']}\n({k})" for k, v in sorted_etfs]
        holding_days = [v['days'] for k, v in sorted_etfs]
        colors = [self._get_etf_color(k) for k, v in sorted_etfs]
        
        bars = ax.barh(etf_names, holding_days, color=colors, edgecolor='white', linewidth=0.5)
        
        for bar, days in zip(bars, holding_days):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                    f'{days}天', va='center', fontsize=9)
        
        ax.set_xlabel('持仓天数', fontsize=11)
        ax.set_title('各ETF累计持仓时间', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--', axis='x')
    
    def _create_nav_chart_page(self, pdf):
        """创建净值曲线页"""
        fig, axes = plt.subplots(2, 1, figsize=(11.69, 8.27))
        fig.suptitle('净值曲线分析', fontsize=18, fontweight='bold', y=0.98)
        
        ax1 = axes[0]
        ax1.fill_between(self.df['date'], self.initial_cash, self.df['_value'],
                         alpha=0.3, color=self.COLORS['secondary'])
        ax1.plot(self.df['date'], self.df['_value'], color=self.COLORS['secondary'],
                 linewidth=2.5, label='策略净值')
        ax1.axhline(y=self.initial_cash, color=self.COLORS['gray'], linestyle='--',
                    linewidth=1.5, label='初始资金', alpha=0.7)
        
        ax1.set_ylabel('账户价值 (¥)', fontsize=11)
        ax1.legend(loc='upper left', fontsize=9)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        total_return = self.stats.get('total_return', 0)
        color = self.COLORS['success'] if total_return >= 0 else self.COLORS['danger']
        ax1.text(0.98, 0.95, f'总收益: {total_return:+.2f}%',
                 transform=ax1.transAxes, fontsize=14, fontweight='bold',
                 color=color, ha='right', va='top',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
        
        ax2 = axes[1]
        cumulative_return = (self.df['_value'] / self.initial_cash - 1) * 100
        ax2.fill_between(self.df['date'], 0, cumulative_return,
                         where=(cumulative_return >= 0), alpha=0.3, color=self.COLORS['success'])
        ax2.fill_between(self.df['date'], 0, cumulative_return,
                         where=(cumulative_return < 0), alpha=0.3, color=self.COLORS['danger'])
        ax2.plot(self.df['date'], cumulative_return, color=self.COLORS['primary'],
                 linewidth=2, label='累计收益率')
        ax2.axhline(y=0, color=self.COLORS['gray'], linestyle='-', linewidth=1)
        
        ax2.set_xlabel('日期', fontsize=11)
        ax2.set_ylabel('累计收益率 (%)', fontsize=11)
        ax2.legend(loc='upper left', fontsize=9)
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
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
                         color=self.COLORS['danger'], alpha=0.4)
        ax1.plot(self.df['date'], drawdown, color=self.COLORS['danger'],
                 linewidth=1.5)
        
        max_dd = self.stats.get('max_drawdown', 0)
        ax1.axhline(y=max_dd, color='darkred', linestyle='--', linewidth=2)
        ax1.text(0.98, 0.15, f'最大回撤: {max_dd:.2f}%',
                 transform=ax1.transAxes, fontsize=12, fontweight='bold',
                 color='darkred', ha='right', va='top',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
        
        ax1.set_ylabel('回撤 (%)', fontsize=11)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        ax2 = axes[1]
        ax2.fill_between(self.df['date'], 0, self.df['_value'] - self.initial_cash,
                         where=(self.df['_value'] >= self.initial_cash),
                         alpha=0.4, color=self.COLORS['success'], label='盈利')
        ax2.fill_between(self.df['date'], 0, self.df['_value'] - self.initial_cash,
                         where=(self.df['_value'] < self.initial_cash),
                         alpha=0.4, color=self.COLORS['danger'], label='亏损')
        ax2.plot(self.df['date'], self.df['_value'] - self.initial_cash,
                 color=self.COLORS['primary'], linewidth=1.5)
        ax2.axhline(y=0, color=self.COLORS['gray'], linestyle='-', linewidth=1)
        
        ax2.set_xlabel('日期', fontsize=11)
        ax2.set_ylabel('盈亏金额 (¥)', fontsize=11)
        ax2.legend(loc='upper left', fontsize=9)
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        final_profit = self.df['_value'].iloc[-1] - self.initial_cash
        profit_color = self.COLORS['success'] if final_profit >= 0 else self.COLORS['danger']
        ax2.text(0.98, 0.95, f'最终盈亏: ¥{final_profit:,.2f}',
                 transform=ax2.transAxes, fontsize=12, fontweight='bold',
                 color=profit_color, ha='right', va='top',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _create_distribution_chart_page(self, pdf):
        """创建收益分布分析页"""
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
        ax1.grid(True, alpha=0.3, linestyle='--')
        
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
            ax2.grid(True, alpha=0.3, linestyle='--')
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        else:
            ax2.text(0.5, 0.5, '暂无资金分布数据', ha='center', va='center',
                     fontsize=12, color=self.COLORS['gray'], transform=ax2.transAxes)
            ax2.set_title('资金分布', fontsize=12, fontweight='bold')
        
        ax3 = axes[1, 0]
        df_copy = self.df.copy()
        df_copy['year_month'] = df_copy['date'].dt.to_period('M')
        monthly_returns = df_copy.groupby('year_month')['daily_return'].apply(
            lambda x: (1 + x).prod() - 1
        ) * 100
        
        if len(monthly_returns) > 0:
            colors = [self.COLORS['success'] if r >= 0 else self.COLORS['danger']
                      for r in monthly_returns.values]
            
            bars = ax3.bar(range(len(monthly_returns)), monthly_returns.values, color=colors,
                           edgecolor='white', linewidth=0.5)
            ax3.set_xticks(range(len(monthly_returns)))
            ax3.set_xticklabels([str(m) for m in monthly_returns.index], rotation=45, ha='right', fontsize=7)
            ax3.axhline(y=0, color=self.COLORS['gray'], linestyle='-', linewidth=1)
            ax3.set_xlabel('月份', fontsize=10)
            ax3.set_ylabel('月收益率 (%)', fontsize=10)
            ax3.set_title('月度收益', fontsize=12, fontweight='bold')
            ax3.grid(True, alpha=0.3, linestyle='--', axis='y')
        else:
            ax3.text(0.5, 0.5, '暂无月度数据', ha='center', va='center',
                     fontsize=12, color=self.COLORS['gray'], transform=ax3.transAxes)
            ax3.set_title('月度收益', fontsize=12, fontweight='bold')
        
        ax4 = axes[1, 1]
        window = min(20, len(self.df) // 4)
        if window >= 5:
            rolling_return = self.df['daily_return'].rolling(window=window).mean() * 252 * 100
            rolling_vol = self.df['daily_return'].rolling(window=window).std() * np.sqrt(252) * 100
            rolling_sharpe = (rolling_return - 3) / rolling_vol
            
            ax4.plot(self.df['date'], rolling_sharpe, color=self.COLORS['purple'],
                     linewidth=1.5, label=f'滚动夏普({window}日)')
            ax4.axhline(y=0, color=self.COLORS['gray'], linestyle='--', linewidth=1)
            ax4.axhline(y=1, color=self.COLORS['success'], linestyle='--', linewidth=1, alpha=0.5)
            ax4.fill_between(self.df['date'], 0, rolling_sharpe,
                             where=(rolling_sharpe >= 0), alpha=0.3, color=self.COLORS['success'])
            ax4.fill_between(self.df['date'], 0, rolling_sharpe,
                             where=(rolling_sharpe < 0), alpha=0.3, color=self.COLORS['danger'])
            ax4.legend(fontsize=9, loc='upper left')
            ax4.set_xlabel('日期', fontsize=10)
            ax4.set_ylabel('夏普比率', fontsize=10)
            ax4.set_title('滚动夏普比率', fontsize=12, fontweight='bold')
            ax4.grid(True, alpha=0.3, linestyle='--')
            ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        else:
            ax4.text(0.5, 0.5, '数据不足', ha='center', va='center',
                     fontsize=12, color=self.COLORS['gray'], transform=ax4.transAxes)
            ax4.set_title('滚动夏普比率', fontsize=12, fontweight='bold')
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _create_etf_analysis_page(self, pdf):
        """创建ETF分析页"""
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.suptitle('ETF交易分析', fontsize=18, fontweight='bold', y=0.98)
        
        if len(self.etf_stats) == 0:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, '暂无ETF交易数据', ha='center', va='center',
                    fontsize=14, color=self.COLORS['gray'], transform=ax.transAxes)
            ax.axis('off')
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
            return
        
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.25,
                              left=0.08, right=0.92, top=0.90, bottom=0.10)
        
        ax1 = fig.add_subplot(gs[0, 0])
        etf_names = [self._get_etf_name(code) for code in self.etf_stats.keys()]
        trade_counts = [s['trade_count'] for s in self.etf_stats.values()]
        colors = [self._get_etf_color(code) for code in self.etf_stats.keys()]
        
        bars = ax1.barh(etf_names, trade_counts, color=colors, edgecolor='white')
        ax1.set_xlabel('交易次数', fontsize=10)
        ax1.set_title('各ETF交易次数', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3, linestyle='--', axis='x')
        
        for bar, val in zip(bars, trade_counts):
            ax1.text(val + 0.3, bar.get_y() + bar.get_height()/2, str(int(val)),
                     va='center', fontsize=9)
        
        ax2 = fig.add_subplot(gs[0, 1])
        buy_values = [s['total_buy_value'] for s in self.etf_stats.values()]
        
        if sum(buy_values) > 0:
            wedges, texts, autotexts = ax2.pie(buy_values, labels=etf_names, colors=colors,
                                                autopct='%1.1f%%', startangle=90,
                                                textprops={'fontsize': 8})
            for autotext in autotexts:
                autotext.set_fontsize(7)
            ax2.set_title('买入金额占比', fontsize=12, fontweight='bold')
        else:
            ax2.text(0.5, 0.5, '暂无数据', ha='center', va='center',
                     fontsize=12, color=self.COLORS['gray'], transform=ax2.transAxes)
            ax2.set_title('买入金额占比', fontsize=12, fontweight='bold')
        
        ax3 = fig.add_subplot(gs[1, :])
        ax3.axis('off')
        
        columns = ['ETF代码', 'ETF名称', '买入次数', '卖出次数', '买入金额', '卖出金额', '净买卖']
        cell_data = []
        for code, stats in self.etf_stats.items():
            row = [
                code,
                stats['name'],
                stats['buy_count'],
                stats['sell_count'],
                f"¥{stats['total_buy_value']:,.0f}",
                f"¥{stats['total_sell_value']:,.0f}",
                f"¥{stats['net_value']:,.0f}"
            ]
            cell_data.append(row)
        
        if len(cell_data) > 0:
            table = ax3.table(cellText=cell_data, colLabels=columns,
                              loc='center', cellLoc='center',
                              colColours=[self.COLORS['primary']] * len(columns))
            
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1.1, 1.6)
            
            for i in range(len(columns)):
                table[(0, i)].set_text_props(color='white', fontweight='bold')
            
            ax3.set_title('ETF交易明细', fontsize=12, fontweight='bold', y=0.95)
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def _create_statistics_page(self, pdf):
        """创建统计指标页"""
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.suptitle('详细统计指标', fontsize=18, fontweight='bold', y=0.98)
        
        ax = fig.add_subplot(111)
        ax.axis('off')
        
        stats_items = [
            ('回测区间', f"{self.stats.get('start_date', '-')} 至 {self.stats.get('end_date', '-')}"),
            ('初始资金', f"¥{self.stats.get('initial_cash', 0):,.2f}"),
            ('最终资金', f"¥{self.stats.get('final_value', 0):,.2f}"),
            ('总收益率', f"{self.stats.get('total_return', 0):.2f}%"),
            ('年化收益率', f"{self.stats.get('annual_return', 0):.2f}%"),
            ('年化波动率', f"{self.stats.get('annual_volatility', 0):.2f}%"),
            ('夏普比率', f"{self.stats.get('sharpe_ratio', 0):.2f}"),
            ('最大回撤', f"{self.stats.get('max_drawdown', 0):.2f}%"),
            ('胜率', f"{self.stats.get('win_rate', 0):.1f}%"),
            ('交易天数', f"{self.stats.get('trading_days', 0)}天"),
            ('交易次数', f"{self.stats.get('trade_count', 0)}次"),
            ('平均盈利', f"{self.stats.get('avg_win', 0):.3f}%"),
            ('平均亏损', f"{self.stats.get('avg_loss', 0):.3f}%"),
            ('盈亏比', f"{self.stats.get('profit_loss_ratio', 0):.2f}"),
        ]
        
        cell_data = []
        for i in range(0, len(stats_items), 2):
            row = []
            for j in range(2):
                if i + j < len(stats_items):
                    label, value = stats_items[i + j]
                    row.extend([label, value])
                else:
                    row.extend(['', ''])
            cell_data.append(row)
        
        columns = ['指标', '数值', '指标', '数值']
        
        table = ax.table(cellText=cell_data, colLabels=columns,
                         loc='center', cellLoc='center',
                         colColours=[self.COLORS['primary']] * 4)
        
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.2, 2.0)
        
        for i in range(4):
            table[(0, i)].set_text_props(color='white', fontweight='bold')
        
        for i in range(1, len(cell_data) + 1):
            for j in [0, 2]:
                table[(i, j)].set_text_props(fontweight='bold', color=self.COLORS['dark'])
        
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    
    def generate_pdf_report(self, output_path: str = 'etf_strategy_report.pdf') -> str:
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
            self._create_strategy_logic_page(pdf)
            self._create_summary_page(pdf)
            self._create_etf_rotation_page(pdf)
            self._create_nav_chart_page(pdf)
            self._create_drawdown_chart_page(pdf)
            self._create_distribution_chart_page(pdf)
            self._create_etf_analysis_page(pdf)
            self._create_statistics_page(pdf)
        
        print(f"\n📄 PDF报告已生成: {output_path}")
        return output_path


def generate_pdf_report_from_strategy(strategy, output_path: str = None):
    """
    从策略实例生成PDF报告
    
    参数:
        strategy: ETFStrategy实例
        output_path: 输出PDF路径
    """
    if output_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, 'backtest_report.pdf')
    
    daily_values = []
    for v in strategy.daily_values:
        daily_values.append({
            'date': v['date'],
            'value': v['value'],
            'cash': v.get('cash', 0),
        })
    
    trade_records = []
    for t in strategy.trade_history:
        trade_records.append({
            'date': t['date'],
            'action': t['action'],
            'code': t['etf'],
            'name': t.get('name', t['etf']),
            'price': t['price'],
            'amount': t['amount'],
            'value': t['value']
        })
    
    start_date = strategy.daily_values[0]['date'].strftime('%Y-%m-%d') if strategy.daily_values else None
    end_date = strategy.daily_values[-1]['date'].strftime('%Y-%m-%d') if strategy.daily_values else None
    
    report = ETFStrategyPDFReport(
        strategy_name='ETF收益率稳定性轮动策略',
        daily_values=daily_values,
        trade_records=trade_records,
        start_date=start_date,
        end_date=end_date,
        initial_cash=strategy.initial_capital,
        etf_pool=getattr(strategy, 'etf_pool', [])
    )
    
    return report.generate_pdf_report(output_path)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        df = pd.read_csv(csv_path)
        daily_values = df.to_dict('records')
        
        output_path = os.path.join(os.path.dirname(csv_path), 'backtest_report.pdf')
        
        report = ETFStrategyPDFReport(
            strategy_name='ETF策略',
            daily_values=daily_values,
            initial_cash=daily_values[0].get('value', 100000)
        )
        report.generate_pdf_report(output_path)
    else:
        print("用法: python etf_strategy_pdf_report.py <csv_path>")
