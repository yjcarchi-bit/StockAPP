#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
多策略回测报告生成器

功能：
1. 生成交互式HTML报告
2. 支持多策略净值对比
3. 各策略收益贡献分析
4. 策略表现统计表
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


class MultiStrategyReportGenerator:
    """
    多策略回测报告生成器
    
    生成交互式HTML报告，包含多策略对比图表
    """
    
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
        if not HAS_PLOTLY:
            raise ImportError("需要安装 plotly: pip install plotly")
        
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
    
    def _create_total_nav_chart(self, fig, row, col):
        """创建总体净值曲线图"""
        dates = self.df['date']
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=self.df['_value'],
                mode='lines',
                name='组合净值',
                line=dict(color='#3b82f6', width=2.5),
                fill='tozeroy',
                fillcolor='rgba(59, 130, 246, 0.1)',
                hovertemplate='日期: %{x|%Y-%m-%d}<br>净值: %{y:,.2f}<extra></extra>'
            ),
            row=row, col=col
        )
        
        fig.add_hline(
            y=self.initial_cash,
            line=dict(color='gray', width=1, dash='dot'),
            row=row, col=col
        )
        
        total_return = self.stats.get('total_return', 0)
        color = '#22c55e' if total_return >= 0 else '#ef4444'
        fig.add_annotation(
            text=f'总收益: {total_return:.2f}%',
            xref=f'x{col}',
            yref=f'y{col}',
            x=0.98,
            y=0.95,
            xanchor='right',
            yanchor='top',
            showarrow=False,
            font=dict(size=14, color=color),
            bgcolor='rgba(255,255,255,0.9)',
            row=row, col=col
        )
    
    def _create_strategy_comparison_chart(self, fig, row, col):
        """创建策略净值对比图"""
        colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
        
        for i, (name, sdf) in enumerate(self.strategy_dfs.items()):
            value_col = 'total_value' if 'total_value' in sdf.columns else sdf.columns[1]
            start_value = sdf[value_col].iloc[0]
            if start_value > 0:
                normalized = (sdf[value_col] / start_value - 1) * 100
            else:
                normalized = pd.Series([0] * len(sdf))
            
            color = colors[i % len(colors)]
            fig.add_trace(
                go.Scatter(
                    x=sdf['date'],
                    y=normalized,
                    mode='lines',
                    name=name,
                    line=dict(color=color, width=1.5),
                    hovertemplate=f'{name}: %{{y:.2f}}%<extra></extra>'
                ),
                row=row, col=col
            )
        
        fig.add_hline(
            y=0,
            line=dict(color='gray', width=1, dash='dot'),
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
    
    def _create_contribution_chart(self, fig, row, col):
        """创建策略收益贡献柱状图"""
        labels = []
        values = []
        colors = []
        
        color_map = {
            '搅屎棍': '#3b82f6',
            '偷鸡摸狗': '#22c55e',
            'ETF轮动': '#f59e0b',
        }
        
        for name, stats in self.strategy_stats.items():
            labels.append(name)
            final_value = stats.get('final_value', 0)
            initial_value = stats.get('initial_cash', 0)
            contribution = final_value - initial_value
            values.append(contribution)
            colors.append(color_map.get(name, '#6b7280'))
        
        if len(values) > 0:
            fig.add_trace(
                go.Bar(
                    x=labels,
                    y=values,
                    name='收益贡献',
                    marker_color=colors,
                    text=[f'¥{v:,.0f}' for v in values],
                    textposition='outside',
                    hovertemplate='%{x}: ¥%{y:,.0f}<extra></extra>'
                ),
                row=row, col=col
            )
            
            fig.add_hline(
                y=0,
                line=dict(color='gray', width=1, dash='dot'),
                row=row, col=col
            )
    
    def _create_strategy_drawdown_chart(self, fig, row, col):
        """创建各策略回撤对比图"""
        colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
        
        for i, (name, sdf) in enumerate(self.strategy_dfs.items()):
            value_col = 'total_value' if 'total_value' in sdf.columns else sdf.columns[1]
            max_value = sdf[value_col].expanding().max()
            drawdown = (sdf[value_col] - max_value) / max_value * 100
            
            color = colors[i % len(colors)]
            fig.add_trace(
                go.Scatter(
                    x=sdf['date'],
                    y=drawdown,
                    mode='lines',
                    name=name,
                    line=dict(color=color, width=1),
                    hovertemplate=f'{name}: %{{y:.2f}}%<extra></extra>'
                ),
                row=row, col=col
            )
    
    def _create_cash_distribution_chart(self, fig, row, col):
        """创建资金分布图"""
        if 'cash' not in self.df.columns:
            return
        
        dates = self.df['date']
        cash = self.df['cash']
        position_value = self.df['_value'] - cash
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=cash,
                mode='lines',
                name='现金',
                stackgroup='one',
                line=dict(color='#22c55e'),
                hovertemplate='现金: ¥%{y:,.0f}<extra></extra>'
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
                hovertemplate='持仓: ¥%{y:,.0f}<extra></extra>'
            ),
            row=row, col=col
        )
    
    def _create_daily_return_dist_chart(self, fig, row, col):
        """创建日收益率分布图"""
        returns = self.df['daily_return'].dropna() * 100
        
        fig.add_trace(
            go.Histogram(
                x=returns,
                nbinsx=30,
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
    
    def _create_monthly_return_chart(self, fig, row, col):
        """创建月度收益柱状图"""
        df = self.df.copy()
        df['year_month'] = df['date'].dt.to_period('M')
        
        monthly_returns = df.groupby('year_month')['daily_return'].apply(
            lambda x: (1 + x).prod() - 1
        ) * 100
        
        colors = ['#22c55e' if r >= 0 else '#ef4444' for r in monthly_returns.values]
        
        fig.add_trace(
            go.Bar(
                x=[str(m) for m in monthly_returns.index],
                y=monthly_returns.values,
                name='月度收益',
                marker_color=colors,
                hovertemplate='%{x}: %{y:.2f}%<extra></extra>'
            ),
            row=row, col=col
        )
        
        fig.add_hline(
            y=0,
            line=dict(color='gray', width=1),
            row=row, col=col
        )
    
    def generate_html_report(self, output_path: str = 'multi_strategy_report.html') -> str:
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
            rows=5, cols=2,
            specs=[
                [{"colspan": 2}, None],
                [{"colspan": 2}, None],
                [{}, {}],
                [{}, {}],
                [{"colspan": 2}, None]
            ],
            row_heights=[0.2, 0.15, 0.2, 0.2, 0.15],
            subplot_titles=(
                '组合净值曲线',
                '策略收益对比 (归一化)',
                '回撤曲线', '收益贡献',
                '各策略回撤对比', '资金分布',
                '月度收益'
            ),
            vertical_spacing=0.08,
            horizontal_spacing=0.1
        )
        
        self._create_total_nav_chart(fig, 1, 1)
        self._create_strategy_comparison_chart(fig, 2, 1)
        self._create_drawdown_chart(fig, 3, 1)
        self._create_contribution_chart(fig, 3, 2)
        self._create_strategy_drawdown_chart(fig, 4, 1)
        self._create_cash_distribution_chart(fig, 4, 2)
        self._create_monthly_return_chart(fig, 5, 1)
        
        fig.update_layout(
            title=dict(
                text=f'<b>{self.strategy_name} - 多策略组合回测报告</b>',
                font=dict(size=22),
                x=0.5,
                xanchor='center'
            ),
            height=1400,
            showlegend=True,
            template='plotly_white',
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        fig.update_yaxes(title_text='账户价值', row=1, col=1)
        fig.update_yaxes(title_text='收益率 (%)', row=2, col=1)
        fig.update_yaxes(title_text='回撤 (%)', row=3, col=1)
        fig.update_yaxes(title_text='收益贡献 (¥)', row=3, col=2)
        fig.update_yaxes(title_text='回撤 (%)', row=4, col=1)
        fig.update_yaxes(title_text='金额', row=4, col=2)
        fig.update_yaxes(title_text='月收益 (%)', row=5, col=1)
        
        stats_html = self._generate_stats_html()
        strategy_table_html = self._generate_strategy_table_html()
        
        full_html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>多策略回测报告 - {self.strategy_name}</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8fafc;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .stats-container {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .stats-container h2 {{
            margin-top: 0;
            color: #1e293b;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
        }}
        .stat-item {{
            text-align: center;
            padding: 18px;
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            border-radius: 10px;
            border: 1px solid #e2e8f0;
        }}
        .stat-label {{
            font-size: 12px;
            color: #64748b;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stat-value {{
            font-size: 20px;
            font-weight: bold;
            color: #1e293b;
        }}
        .positive {{ color: #22c55e; }}
        .negative {{ color: #ef4444; }}
        .neutral {{ color: #6b7280; }}
        .chart-container {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }}
        .strategy-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        .strategy-table th {{
            background: #1e3a8a;
            color: white;
            padding: 12px 15px;
            text-align: center;
            font-weight: 600;
        }}
        .strategy-table td {{
            padding: 12px 15px;
            text-align: center;
            border-bottom: 1px solid #e2e8f0;
        }}
        .strategy-table tr:hover {{
            background-color: #f8fafc;
        }}
        .strategy-table tr:nth-child(even) {{
            background-color: #f8fafc;
        }}
        .footer {{
            text-align: center;
            color: #94a3b8;
            margin-top: 20px;
            padding: 20px;
            font-size: 14px;
        }}
        .highlight {{
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 4px solid #f59e0b;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 {self.strategy_name}</h1>
        <p>多策略组合回测报告 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="stats-container">
        <h2>📊 组合总体表现</h2>
        {stats_html}
    </div>
    
    <div class="stats-container">
        <h2>📈 各策略表现对比</h2>
        {strategy_table_html}
    </div>
    
    <div class="chart-container">
        {pio.to_html(fig, full_html=False, include_plotlyjs='cdn')}
    </div>
    
    <div class="footer">
        <p>💡 提示: 图表支持缩放、平移、悬停查看详情，点击图例可显示/隐藏数据系列</p>
        <p>📅 回测区间: {self.start_date} 至 {self.end_date}</p>
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
        """生成总体统计指标HTML"""
        stats = self.stats
        
        items = [
            ('回测区间', f"{stats.get('start_date', '-')} 至 {stats.get('end_date', '-')}", 'neutral'),
            ('初始资金', f"¥{stats.get('initial_cash', 0):,.2f}", ''),
            ('最终资金', f"¥{stats.get('final_value', 0):,.2f}", ''),
            ('总收益率', f"{stats.get('total_return', 0):.2f}%", 'positive' if stats.get('total_return', 0) >= 0 else 'negative'),
            ('年化收益率', f"{stats.get('annual_return', 0):.2f}%", 'positive' if stats.get('annual_return', 0) >= 0 else 'negative'),
            ('年化波动率', f"{stats.get('annual_volatility', 0):.2f}%", 'neutral'),
            ('夏普比率', f"{stats.get('sharpe_ratio', 0):.2f}", 'positive' if stats.get('sharpe_ratio', 0) >= 1 else ''),
            ('最大回撤', f"{stats.get('max_drawdown', 0):.2f}%", 'negative'),
            ('胜率', f"{stats.get('win_rate', 0):.1f}%", 'positive' if stats.get('win_rate', 0) >= 50 else ''),
            ('交易天数', f"{stats.get('trading_days', 0)}天", 'neutral'),
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
    
    def _generate_strategy_table_html(self) -> str:
        """生成策略对比表格HTML"""
        rows = []
        
        for name, stats in self.strategy_stats.items():
            return_class = 'positive' if stats.get('total_return', 0) >= 0 else 'negative'
            sharpe_class = 'positive' if stats.get('sharpe_ratio', 0) >= 1 else ''
            
            config = next((c for c in self.strategy_configs if c.get('name') == name), {})
            pct = config.get('pct', 0) * 100
            
            rows.append(f'''
            <tr>
                <td><strong>{name}</strong></td>
                <td>{pct:.0f}%</td>
                <td>¥{stats.get('initial_cash', 0):,.0f}</td>
                <td>¥{stats.get('final_value', 0):,.0f}</td>
                <td class="{return_class}">{stats.get('total_return', 0):.2f}%</td>
                <td class="{return_class}">{stats.get('annual_return', 0):.2f}%</td>
                <td class="{sharpe_class}">{stats.get('sharpe_ratio', 0):.2f}</td>
                <td class="negative">{stats.get('max_drawdown', 0):.2f}%</td>
            </tr>
            ''')
        
        return f'''
        <table class="strategy-table">
            <thead>
                <tr>
                    <th>策略名称</th>
                    <th>资金占比</th>
                    <th>初始资金</th>
                    <th>最终资金</th>
                    <th>总收益率</th>
                    <th>年化收益</th>
                    <th>夏普比率</th>
                    <th>最大回撤</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
        '''
    
    def print_stats(self):
        """打印统计指标"""
        print("\n" + "=" * 60)
        print("组合总体表现")
        print("=" * 60)
        for key, value in self.stats.items():
            if isinstance(value, float):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")
        
        print("\n" + "=" * 60)
        print("各策略表现")
        print("=" * 60)
        for name, stats in self.strategy_stats.items():
            print(f"\n[{name}]")
            for key, value in stats.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.2f}")
                else:
                    print(f"  {key}: {value}")
