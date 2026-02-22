#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
检查efinance财务数据字段
"""

import efinance as ef
import pandas as pd

print("检查efinance财务数据字段...")
print("=" * 60)

test_codes = ['600519', '000001', '600036', '601318', '000858']

for code in test_codes:
    print(f"\n股票: {code}")
    try:
        series = ef.stock.get_base_info(code)
        if series is not None:
            print(f"  类型: {type(series)}")
            if hasattr(series, 'to_dict'):
                data = series.to_dict()
                for key, value in data.items():
                    print(f"  {key}: {value}")
            else:
                print(f"  数据: {series}")
        else:
            print("  无数据")
    except Exception as e:
        print(f"  错误: {e}")

print("\n" + "=" * 60)
print("检查efinance其他财务数据接口...")
print("=" * 60)

try:
    df = ef.stock.get_financial_summary('600519')
    if df is not None:
        print(f"\n财务摘要数据 (600519):")
        print(df.head())
except Exception as e:
    print(f"get_financial_summary 错误: {e}")

try:
    df = ef.stock.get_main_financial_data('600519')
    if df is not None:
        print(f"\n主要财务数据 (600519):")
        print(df.head() if hasattr(df, 'head') else df)
except Exception as e:
    print(f"get_main_financial_data 错误: {e}")
