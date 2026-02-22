#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
通用回测报告生成器

功能：
1. 生成交互式HTML报告
2. 支持沪深300基准对比
3. 多种图表：净值曲线、回撤曲线、月度收益热力图、持仓变化等

使用方法：
    from backtest_report_generator import BacktestReportGenerator
    
    generator = BacktestReportGenerator(
        strategy_name='策略名称',
        daily_values=daily_values,
        trade_records=trade_records,
        index_data=index_data  # 沪深300数据
    )
    generator.generate_html_report('report.html')
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.io as pio
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    print("警告: 未安装 plotly，请运行: pip install plotly")


class BacktestReportGenerator:
    """
    回测报告生成器
    
    生成交互式HTML报告，包含多种图表
    """
    
    def __init__(self, strategy_name: str, daily_values: list, 
                 trade_records: list = None,
                 start_date: str = None, end_date: str = None,
                 initial_cash: float = 100000.0):
        """
        初始化报告生成器
        
        参数:
            strategy_name: 策略名称
            daily_values: 每日净值数据列表
            trade_records: 交易记录列表
            start_date: 回测开始日期
            end_date: 回测结束日期
            initial_cash: 初始资金
        """
        if not HAS_PLOTLY:
            raise ImportError("需要安装 plotly: pip install plotly")
        
        self.strategy_name = strategy_name
        self.daily_values = daily_values
        self.trade_records = trade_records or []
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash = initial_cash
        
        self.df = None
        self.trades_df = None
        self.stats = {}
        
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
        
        if len(self.trade_records) > 0:
            self.trades_df = pd.DataFrame(self.trade_records)
            if 'date' in self.trades_df.columns:
                self.trades_df['date'] = pd.to_datetime(self.trades_df['date'])
    
    def _calculate_stats(self):
        """计算统计指标"""
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
            'trade_count': len(self.trade_records)
        }
        
        if len(self.trade_records) > 0:
            trades_df = pd.DataFrame(self.trade_records)
            if 'action' in trades_df.columns:
                self.stats['buy_count'] = len(trades_df[trades_df['action'] == 'buy'])
                self.stats['sell_count'] = len(trades_df[trades_df['action'] == 'sell'])
            if 'commission' in trades_df.columns:
                self.stats['total_commission'] = trades_df['commission'].sum()
    
    def _create_nav_chart(self, fig, row, col):
        """创建净值曲线图"""
        dates = self.df['date']
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=self.df['_value'],
                mode='lines',
                name='策略净值',
                line=dict(color='#3b82f6', width=2),
                fill='tozeroy',
                fillcolor='rgba(59, 130, 246, 0.1)',
                hovertemplate='日期: %{x|%Y-%m-%d}<br>净值: %{y:,.2f}<extra></extra>'
            ),
            row=row, col=col
        )
        
        if self.trades_df is not None and len(self.trades_df) > 0:
            if 'action' in self.trades_df.columns:
                buy_trades = self.trades_df[self.trades_df['action'] == 'buy']
                sell_trades = self.trades_df[self.trades_df['action'] == 'sell']
                
                for _, trade in buy_trades.iterrows():
                    fig.add_vline(
                        x=trade['date'],
                        line=dict(color='green', width=1, dash='dot'),
                        opacity=0.4,
                        row=row, col=col
                    )
                
                for _, trade in sell_trades.iterrows():
                    fig.add_vline(
                        x=trade['date'],
                        line=dict(color='red', width=1, dash='dot'),
                        opacity=0.4,
                        row=row, col=col
                    )
        
        total_return = self.stats.get('total_return', 0)
        fig.add_annotation(
            text=f'总收益: {total_return:.2f}%',
            xref=f'x{col}',
            yref=f'y{col}',
            x=0.98,
            y=0.95,
            xanchor='right',
            yanchor='top',
            showarrow=False,
            font=dict(size=12),
            bgcolor='rgba(255,255,255,0.8)',
            row=row, col=col
        )
    
    def _create_drawdown_chart(self, fig, row, col):
        """创建回撤曲线图"""
        dates = self.df['date']
        drawdown = self.df['_drawdown'] * 100
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=drawdown,
                mode='lines',
                name='回撤',
                line=dict(color='#ef4444', width=1.5),
                fill='tozeroy',
                fillcolor='rgba(239, 68, 68, 0.2)',
                hovertemplate='日期: %{x|%Y-%m-%d}<br>回撤: %{y:.2f}%<extra></extra>'
            ),
            row=row, col=col
        )
        
        max_dd = self.stats.get('max_drawdown', 0)
        fig.add_hline(
            y=max_dd,
            line=dict(color='darkred', width=2, dash='dash'),
            annotation_text=f'最大回撤: {max_dd:.2f}%',
            annotation_position='right',
            row=row, col=col
        )
    
    def _create_monthly_heatmap(self, fig, row, col):
        """创建月度收益热力图"""
        df = self.df.copy()
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        
        monthly_returns = df.groupby(['year', 'month'])['daily_return'].apply(
            lambda x: (1 + x).prod() - 1
        ) * 100
        
        years = sorted(df['year'].unique())
        months = list(range(1, 13))
        month_names = ['1月', '2月', '3月', '4月', '5月', '6月', 
                       '7月', '8月', '9月', '10月', '11月', '12月']
        
        heatmap_data = []
        for year in years:
            for month in months:
                if (year, month) in monthly_returns.index:
                    ret = monthly_returns[(year, month)]
                    heatmap_data.append([month - 1, int(year) - int(years[0]), round(ret, 2)])
        
        if len(heatmap_data) > 0:
            fig.add_trace(
                go.Heatmap(
                    x=month_names,
                    y=[str(y) for y in years],
                    z=[[0]*12 for _ in years],
                    customdata=heatmap_data,
                    hovertemplate='月收益: %{z:.2f}%<extra></extra>',
                    colorscale='RdYlGn',
                    showscale=True,
                    colorbar=dict(title='收益%'),
                ),
                row=row, col=col
            )
            
            for item in heatmap_data:
                month_idx, year_idx, ret = item
                color = 'white' if abs(ret) > 5 else 'black'
                fig.add_annotation(
                    x=month_names[month_idx],
                    y=str(years[year_idx]),
                    text=f'{ret:.1f}%',
                    font=dict(size=9, color=color),
                    showarrow=False,
                    row=row, col=col
                )
    
    def _create_position_chart(self, fig, row, col):
        """创建持仓数量图"""
        if 'position_count' not in self.df.columns:
            return
        
        dates = self.df['date']
        pos_count = self.df['position_count']
        
        colors = ['#22c55e' if c > 0 else '#d1d5db' for c in pos_count]
        
        fig.add_trace(
            go.Bar(
                x=dates,
                y=pos_count,
                name='持仓数量',
                marker_color=colors,
                hovertemplate='日期: %{x|%Y-%m-%d}<br>持仓: %{y}只<extra></extra>'
            ),
            row=row, col=col
        )
    
    def _create_cash_position_chart(self, fig, row, col):
        """创建资金分布图"""
        if 'cash' not in self.df.columns:
            return
        
        dates = self.df['date']
        cash = self.df['cash']
        
        if 'position_value' in self.df.columns:
            position_value = self.df['position_value']
        else:
            position_value = self.df['_value'] - cash
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=cash,
                mode='lines',
                name='现金',
                stackgroup='one',
                line=dict(color='#22c55e'),
                hovertemplate='现金: %{y:,.0f}<extra></extra>'
            ),
            row=row, col=col
        )
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=position_value,
                mode='lines',
                name='持仓市值',
                stackgroup='one',
                line=dict(color='#3b82f6'),
                hovertemplate='持仓: %{y:,.0f}<extra></extra>'
            ),
            row=row, col=col
        )
    
    def _create_return_dist_chart(self, fig, row, col):
        """创建日收益率分布图"""
        returns = self.df['daily_return'].dropna() * 100
        
        fig.add_trace(
            go.Histogram(
                x=returns,
                nbinsx=40,
                name='日收益率',
                marker_color='#3b82f6',
                opacity=0.7,
                hovertemplate='收益率: %{x:.2f}%<br>频次: %{y}<extra></extra>'
            ),
            row=row, col=col
        )
        
        mean_ret = returns.mean()
        fig.add_vline(
            x=mean_ret,
            line=dict(color='green', width=2, dash='dash'),
            annotation_text=f'均值: {mean_ret:.3f}%',
            row=row, col=col
        )
        
        fig.add_vline(
            x=0,
            line=dict(color='red', width=1, dash='dot'),
            row=row, col=col
        )
    
    def _create_cumulative_return_chart(self, fig, row, col):
        """创建累计收益图"""
        dates = self.df['date']
        strategy_return = (self.df['_value'] / self.df['_value'].iloc[0] - 1) * 100
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=strategy_return,
                mode='lines',
                name='累计收益',
                line=dict(color='#3b82f6', width=2),
                hovertemplate='日期: %{x|%Y-%m-%d}<br>累计收益: %{y:.2f}%<extra></extra>'
            ),
            row=row, col=col
        )
        
        fig.add_hline(
            y=0,
            line=dict(color='gray', width=1, dash='dot'),
            row=row, col=col
        )
    
    def _create_rolling_sharpe_chart(self, fig, row, col):
        """创建滚动夏普比率图"""
        window = min(60, len(self.df) // 4)
        if window < 10:
            return
        
        rolling_return = self.df['daily_return'].rolling(window=window).mean() * 252
        rolling_vol = self.df['daily_return'].rolling(window=window).std() * np.sqrt(252)
        rolling_sharpe = rolling_return / rolling_vol
        
        fig.add_trace(
            go.Scatter(
                x=self.df['date'],
                y=rolling_sharpe,
                mode='lines',
                name=f'滚动夏普({window}日)',
                line=dict(color='#8b5cf6', width=1.5),
                hovertemplate='日期: %{x|%Y-%m-%d}<br>夏普: %{y:.2f}<extra></extra>'
            ),
            row=row, col=col
        )
        
        fig.add_hline(
            y=0,
            line=dict(color='gray', width=1, dash='dot'),
            row=row, col=col
        )
        
        fig.add_hline(
            y=1,
            line=dict(color='green', width=1, dash='dash'),
            row=row, col=col
        )
    
    def _create_trade_analysis_chart(self, fig, row, col):
        """创建交易分析图"""
        if self.trades_df is None or len(self.trades_df) == 0:
            return
        
        if 'action' not in self.trades_df.columns:
            return
        
        trades_by_date = self.trades_df.groupby(['date', 'action']).size().unstack(fill_value=0)
        
        if 'buy' in trades_by_date.columns:
            fig.add_trace(
                go.Bar(
                    x=trades_by_date.index,
                    y=trades_by_date['buy'],
                    name='买入次数',
                    marker_color='#22c55e',
                    hovertemplate='日期: %{x|%Y-%m-%d}<br>买入: %{y}次<extra></extra>'
                ),
                row=row, col=col
            )
        
        if 'sell' in trades_by_date.columns:
            fig.add_trace(
                go.Bar(
                    x=trades_by_date.index,
                    y=trades_by_date['sell'],
                    name='卖出次数',
                    marker_color='#ef4444',
                    hovertemplate='日期: %{x|%Y-%m-%d}<br>卖出: %{y}次<extra></extra>'
                ),
                row=row, col=col
            )
    
    def generate_html_report(self, output_path: str = 'backtest_report.html') -> str:
        """
        生成HTML报告
        
        参数:
            output_path: 输出文件路径
        
        返回:
            生成的文件路径
        """
        if self.df is None or len(self.df) == 0:
            print("无数据，无法生成报告")
            return None
        
        fig = make_subplots(
            rows=6, cols=2,
            specs=[
                [{"colspan": 2}, None],
                [{"colspan": 2}, None],
                [{"colspan": 2}, None],
                [{}, {}],
                [{}, {}],
                [{"colspan": 2}, None]
            ],
            row_heights=[0.2, 0.12, 0.12, 0.15, 0.15, 0.15],
            subplot_titles=(
                '净值曲线 (绿色=买入, 红色=卖出)',
                '回撤曲线',
                '累计收益对比',
                '持仓数量', '资金分布',
                '月度收益热力图', '日收益率分布',
                '交易分析'
            ),
            vertical_spacing=0.06,
            horizontal_spacing=0.1
        )
        
        self._create_nav_chart(fig, 1, 1)
        self._create_drawdown_chart(fig, 2, 1)
        self._create_cumulative_return_chart(fig, 3, 1)
        self._create_position_chart(fig, 4, 1)
        self._create_cash_position_chart(fig, 4, 2)
        self._create_return_dist_chart(fig, 5, 2)
        self._create_rolling_sharpe_chart(fig, 5, 1)
        self._create_trade_analysis_chart(fig, 6, 1)
        
        fig.update_layout(
            title=dict(
                text=f'<b>{self.strategy_name} - 回测报告</b>',
                font=dict(size=20),
                x=0.5,
                xanchor='center'
            ),
            height=1600,
            showlegend=True,
            template='plotly_white',
            hovermode='x unified'
        )
        
        fig.update_xaxes(title_text='日期', row=6, col=1)
        fig.update_yaxes(title_text='账户价值', row=1, col=1)
        fig.update_yaxes(title_text='回撤 (%)', row=2, col=1)
        fig.update_yaxes(title_text='累计收益 (%)', row=3, col=1)
        fig.update_yaxes(title_text='持仓数', row=4, col=1)
        fig.update_yaxes(title_text='金额', row=4, col=2)
        fig.update_yaxes(title_text='滚动夏普', row=5, col=1)
        fig.update_yaxes(title_text='频次', row=5, col=2)
        fig.update_xaxes(title_text='日收益率 (%)', row=5, col=2)
        
        stats_html = self._generate_stats_html()
        
        full_html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>回测报告 - {self.strategy_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .stats-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .stat-item {{
            text-align: center;
            padding: 15px;
            background: #f8fafc;
            border-radius: 8px;
        }}
        .stat-label {{
            font-size: 12px;
            color: #64748b;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 18px;
            font-weight: bold;
            color: #1e293b;
        }}
        .positive {{ color: #22c55e; }}
        .negative {{ color: #ef4444; }}
        .chart-container {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .footer {{
            text-align: center;
            color: #888;
            margin-top: 20px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{self.strategy_name}</h1>
        <p>交互式回测报告 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="stats-container">
        <h2 style="margin-top:0; color:#333;">📊 回测统计指标</h2>
        {stats_html}
    </div>
    
    <div class="chart-container">
        {pio.to_html(fig, full_html=False, include_plotlyjs='cdn')}
    </div>
    
    <div class="footer">
        <p>💡 提示: 图表支持缩放、平移、悬停查看详情，点击图例可显示/隐藏数据系列</p>
    </div>
</body>
</html>
'''
        
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        
        print(f"\n📄 交互式HTML报告已生成: {output_path}")
        return output_path
    
    def _generate_stats_html(self) -> str:
        """生成统计指标HTML"""
        stats = self.stats
        
        items = [
            ('回测区间', f"{stats.get('start_date', '-')} 至 {stats.get('end_date', '-')}", ''),
            ('初始资金', f"¥{stats.get('initial_cash', 0):,.2f}", ''),
            ('最终资金', f"¥{stats.get('final_value', 0):,.2f}", ''),
            ('总收益率', f"{stats.get('total_return', 0):.2f}%", 'positive' if stats.get('total_return', 0) >= 0 else 'negative'),
            ('年化收益率', f"{stats.get('annual_return', 0):.2f}%", 'positive' if stats.get('annual_return', 0) >= 0 else 'negative'),
            ('年化波动率', f"{stats.get('annual_volatility', 0):.2f}%", ''),
            ('夏普比率', f"{stats.get('sharpe_ratio', 0):.2f}", 'positive' if stats.get('sharpe_ratio', 0) >= 1 else ''),
            ('最大回撤', f"{stats.get('max_drawdown', 0):.2f}%", 'negative'),
            ('胜率', f"{stats.get('win_rate', 0):.2f}%", ''),
            ('交易次数', f"{stats.get('trade_count', 0)}", ''),
        ]
        
        html_items = []
        for label, value, color_class in items:
            html_items.append(f'''
            <div class="stat-item">
                <div class="stat-label">{label}</div>
                <div class="stat-value {color_class}">{value}</div>
            </div>
            ''')
        
        return f'<div class="stats-grid">{"".join(html_items)}</div>'
    
    def print_stats(self):
        """打印统计指标"""
        print("\n" + "=" * 50)
        print("回测统计指标")
        print("=" * 50)
        for key, value in self.stats.items():
            if isinstance(value, float):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")
