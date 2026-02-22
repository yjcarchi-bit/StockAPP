"""
报告生成模块
============
回测报告生成功能
"""

from .generator import ReportGenerator, generate_html_report, generate_pdf_report

__all__ = ["ReportGenerator", "generate_html_report", "generate_pdf_report"]
