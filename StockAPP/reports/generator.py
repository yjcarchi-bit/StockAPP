"""
报告生成器
==========
生成HTML和PDF格式的回测报告
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd

from core.backtest_engine import BacktestResult


class ReportGenerator:
    """
    报告生成器
    
    生成HTML和PDF格式的回测报告
    
    Example:
        >>> generator = ReportGenerator(result)
        >>> generator.generate_html("report.html")
        >>> generator.generate_pdf("report.pdf")
    """
    
    def __init__(self, result: BacktestResult):
        """
        初始化报告生成器
        
        Args:
            result: 回测结果
        """
        self.result = result
        self.metrics = result.metrics
        self.daily_values = result.daily_values
        self.trade_records = result.trade_records
    
    def generate_html(self, output_path: str) -> None:
        """
        生成HTML报告
        
        Args:
            output_path: 输出文件路径
        """
        html_content = self._generate_html_content()
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    
    def _generate_html_content(self) -> str:
        """生成HTML内容"""
        
        m = self.metrics
        
        trades_html = ""
        if not self.trade_records.empty:
            trades_html = self._generate_trades_table()
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>回测报告 - StockAPP</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #1f77b4, #2ca02c);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .header p {{
            opacity: 0.9;
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            font-size: 18px;
            margin-bottom: 15px;
            color: #1f77b4;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }}
        .metric-item {{
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #1f77b4;
        }}
        .metric-value.positive {{
            color: #2ca02c;
        }}
        .metric-value.negative {{
            color: #d62728;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .buy {{
            color: #2ca02c;
        }}
        .sell {{
            color: #d62728;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 回测报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="card">
            <h2>📈 收益指标</h2>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-value {'positive' if m.get('total_return', 0) > 0 else 'negative'}">{m.get('total_return', 0):.2f}%</div>
                    <div class="metric-label">总收益率</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value {'positive' if m.get('annual_return', 0) > 0 else 'negative'}">{m.get('annual_return', 0):.2f}%</div>
                    <div class="metric-label">年化收益率</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value {'positive' if m.get('benchmark_return', 0) > 0 else 'negative'}">{m.get('benchmark_return', 0):.2f}%</div>
                    <div class="metric-label">基准收益率</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value {'positive' if m.get('excess_return', 0) > 0 else 'negative'}">{m.get('excess_return', 0):.2f}%</div>
                    <div class="metric-label">超额收益</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>⚠️ 风险指标</h2>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-value negative">{m.get('max_drawdown', 0):.2f}%</div>
                    <div class="metric-label">最大回撤</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{m.get('annual_volatility', 0):.2f}%</div>
                    <div class="metric-label">年化波动率</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{m.get('sharpe_ratio', 0):.2f}</div>
                    <div class="metric-label">夏普比率</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{m.get('calmar_ratio', 0):.2f}</div>
                    <div class="metric-label">卡玛比率</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>📊 交易统计</h2>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-value">{m.get('total_trades', 0)}</div>
                    <div class="metric-label">交易次数</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{m.get('win_rate', 0):.1f}%</div>
                    <div class="metric-label">胜率</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{m.get('profit_factor', 0):.2f}</div>
                    <div class="metric-label">盈亏比</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{m.get('final_value', 0):,.0f}</div>
                    <div class="metric-label">最终资产</div>
                </div>
            </div>
        </div>
        
        {trades_html}
        
        <div class="footer">
            <p>StockAPP 量化回测平台 | 报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _generate_trades_table(self) -> str:
        """生成交易记录表格"""
        df = self.trade_records.copy()
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp', ascending=False)
        
        rows = ""
        for _, row in df.head(100).iterrows():
            side = row.get('side', '')
            side_class = 'buy' if side == 'buy' else 'sell'
            side_text = '买入' if side == 'buy' else '卖出'
            
            rows += f"""
                <tr>
                    <td>{row.get('timestamp', '')}</td>
                    <td>{row.get('code', '')}</td>
                    <td class="{side_class}">{side_text}</td>
                    <td>{row.get('price', 0):.3f}</td>
                    <td>{row.get('amount', 0)}</td>
                    <td>{row.get('value', 0):,.2f}</td>
                </tr>
            """
        
        return f"""
        <div class="card">
            <h2>📝 交易记录</h2>
            <table>
                <thead>
                    <tr>
                        <th>时间</th>
                        <th>代码</th>
                        <th>方向</th>
                        <th>价格</th>
                        <th>数量</th>
                        <th>金额</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """
    
    def generate_pdf(self, output_path: str) -> None:
        """
        生成PDF报告
        
        Args:
            output_path: 输出文件路径
        """
        try:
            from weasyprint import HTML
            
            html_content = self._generate_html_content()
            HTML(string=html_content).write_pdf(output_path)
        except ImportError:
            print("请安装weasyprint: pip install weasyprint")
        except Exception as e:
            print(f"生成PDF失败: {e}")


def generate_html_report(result: BacktestResult, output_path: str) -> None:
    """
    生成HTML报告
    
    Args:
        result: 回测结果
        output_path: 输出文件路径
    """
    generator = ReportGenerator(result)
    generator.generate_html(output_path)


def generate_pdf_report(result: BacktestResult, output_path: str) -> None:
    """
    生成PDF报告
    
    Args:
        result: 回测结果
        output_path: 输出文件路径
    """
    generator = ReportGenerator(result)
    generator.generate_pdf(output_path)
