#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
搅屎棍策略调试脚本
分析为什么策略没有进行交易
"""

import numpy as np
import pandas as pd
import efinance as ef
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import warnings
import concurrent.futures

warnings.filterwarnings('ignore')


def format_date_for_efinance(date_str: str) -> str:
    if '-' in date_str:
        return date_str.replace('-', '')
    return date_str


def get_all_stocks() -> List[str]:
    try:
        df = ef.stock.get_realtime_quotes()
        if df is not None and len(df) > 0:
            codes = df['股票代码'].tolist()
            codes = [c for c in codes if c.startswith(('6', '0', '3')) and not c.startswith('68')]
            return codes
    except Exception as e:
        print(f"获取股票列表失败: {e}")
    return []


def filter_kcbj_stock(stock_list: List[str]) -> List[str]:
    out = []
    for stock in stock_list:
        stock_clean = stock.split('.')[0] if '.' in stock else stock
        if stock_clean[0] in ['4', '8'] or stock_clean[:2] in ['68', '30']:
            continue
        out.append(stock)
    return out


def get_stock_data(code: str, end_date: str, days: int = 100) -> Optional[pd.DataFrame]:
    try:
        stock_code = code.split('.')[0] if '.' in code else code
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days*2)).strftime('%Y-%m-%d')
        
        beg = format_date_for_efinance(start_date)
        end = format_date_for_efinance(end_date)
        
        df = ef.stock.get_quote_history(stock_code, beg=beg, end=end, klt=101, fqt=1)
        if df is not None and len(df) > 0:
            return df
    except Exception:
        pass
    return None


def get_financial_data(codes: List[str]) -> pd.DataFrame:
    result_data = []
    
    def get_single(code: str) -> Optional[Dict]:
        try:
            series = ef.stock.get_base_info(code)
            if series is not None and len(series) > 0:
                row = {'code': code}
                row['market_cap'] = series.get('总市值', 0)
                row['roe'] = series.get('ROE', 0)
                row['eps'] = series.get('每股收益', 0)
                name = str(series.get('股票名称', ''))
                row['name'] = name
                row['is_st'] = 'ST' in name or '*' in name or '退' in name
                return row
        except Exception:
            pass
        return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_single, code): code for code in codes}
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result is not None:
                    result_data.append(result)
            except Exception:
                continue
    
    return pd.DataFrame(result_data)


def analyze_fms_strategy():
    print("=" * 60)
    print("搅屎棍策略调试分析")
    print("=" * 60)
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    print(f"\n回测区间: {start_date} 至 {end_date}")
    
    print("\n步骤1: 获取所有股票列表...")
    all_stocks = get_all_stocks()
    print(f"  获取到 {len(all_stocks)} 只股票")
    
    print("\n步骤2: 过滤科创板和北交所...")
    filtered_stocks = filter_kcbj_stock(all_stocks)
    print(f"  过滤后剩余 {len(filtered_stocks)} 只股票")
    
    print("\n步骤3: 过滤ST股票...")
    sample_for_st = filtered_stocks[:200]
    financial_sample = get_financial_data(sample_for_st)
    
    if not financial_sample.empty:
        non_st_stocks = financial_sample[~financial_sample['is_st']]['code'].tolist()
        print(f"  过滤后剩余 {len(non_st_stocks)} 只非ST股票")
    else:
        non_st_stocks = filtered_stocks
        print("  无法获取财务数据，跳过ST过滤")
    
    print("\n步骤4: 过滤新股（需要200天数据）...")
    new_stock_days = 200
    min_data_days = 180
    
    valid_stocks = []
    test_sample = non_st_stocks[:50]
    
    for stock in test_sample:
        try:
            data = get_stock_data(stock, end_date, new_stock_days)
            if data is not None and len(data) > min_data_days:
                valid_stocks.append(stock)
        except Exception:
            continue
    
    print(f"  测试 {len(test_sample)} 只股票，{len(valid_stocks)} 只通过新股过滤")
    print(f"  通过率: {len(valid_stocks)/len(test_sample)*100:.1f}%")
    
    print("\n步骤5: 获取财务数据并筛选...")
    if len(valid_stocks) > 0:
        financial_df = get_financial_data(valid_stocks)
        
        if not financial_df.empty:
            print(f"  获取到 {len(financial_df)} 只股票的财务数据")
            
            print("\n  财务数据统计:")
            print(f"    ROE > 0.15: {(financial_df['roe'] > 0.15).sum()} 只")
            print(f"    EPS > 0: {(financial_df['eps'] > 0).sum()} 只")
            print(f"    ROE > 0.15 且 EPS > 0: {((financial_df['roe'] > 0.15) & (financial_df['eps'] > 0)).sum()} 只")
            
            filtered = financial_df[
                (financial_df['roe'] > 0.15) & 
                (financial_df['eps'] > 0)
            ]
            
            if not filtered.empty:
                filtered = filtered.sort_values('market_cap')
                print(f"\n  筛选后剩余 {len(filtered)} 只股票")
                
                print("\n  前5只股票（按市值排序）:")
                for _, row in filtered.head(5).iterrows():
                    print(f"    {row['code']} {row['name']}: ROE={row['roe']:.2f}, EPS={row['eps']:.2f}, 市值={row['market_cap']:.0f}亿")
            else:
                print("\n  ⚠️ 没有股票满足筛选条件！")
        else:
            print("  ⚠️ 无法获取财务数据！")
    else:
        print("  ⚠️ 没有股票通过新股过滤！")
    
    print("\n" + "=" * 60)
    print("问题分析")
    print("=" * 60)
    
    print("""
1. 新股过滤条件太严格:
   - 需要200天的历史数据
   - 至少180个交易日
   - 3个月回测期间，很多股票可能数据不足

2. 财务数据筛选条件:
   - ROE > 0.15 (15%)
   - EPS > 0
   - 条件较为严格

3. 建议优化:
   - 降低新股过滤天数（如100天）
   - 放宽ROE条件（如 > 0.10）
   - 使用更广泛的股票池
""")


if __name__ == '__main__':
    analyze_fms_strategy()
