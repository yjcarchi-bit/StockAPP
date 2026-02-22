"""
数据源服务
==========
复用现有数据源，提供ETF和股票数据查询
"""

import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core import DataSource

try:
    import efinance as ef
except ImportError:
    ef = None


ETF_LIST = [
    {"code": "518880", "name": "黄金ETF", "type": "商品"},
    {"code": "159980", "name": "有色ETF", "type": "商品"},
    {"code": "159985", "name": "豆粕ETF", "type": "商品"},
    {"code": "501018", "name": "南方原油LOF", "type": "商品"},
    {"code": "513100", "name": "纳指ETF", "type": "海外"},
    {"code": "513500", "name": "标普500ETF", "type": "海外"},
    {"code": "513520", "name": "日经ETF", "type": "海外"},
    {"code": "513030", "name": "德国ETF", "type": "海外"},
    {"code": "513080", "name": "法国ETF", "type": "海外"},
    {"code": "159920", "name": "恒生ETF", "type": "海外"},
    {"code": "510300", "name": "沪深300ETF", "type": "宽基"},
    {"code": "510500", "name": "中证500ETF", "type": "宽基"},
    {"code": "510050", "name": "上证50ETF", "type": "宽基"},
    {"code": "510210", "name": "上证指数ETF", "type": "宽基"},
    {"code": "159915", "name": "创业板ETF", "type": "宽基"},
    {"code": "588080", "name": "科创板50ETF", "type": "宽基"},
    {"code": "159995", "name": "芯片ETF", "type": "行业"},
    {"code": "513050", "name": "中概互联ETF", "type": "行业"},
    {"code": "159852", "name": "半导体ETF", "type": "行业"},
    {"code": "159845", "name": "新能源ETF", "type": "行业"},
    {"code": "515030", "name": "新能源车ETF", "type": "行业"},
    {"code": "159806", "name": "光伏ETF", "type": "行业"},
    {"code": "159928", "name": "消费ETF", "type": "行业"},
    {"code": "512670", "name": "国防军工ETF", "type": "行业"},
    {"code": "511010", "name": "国债ETF", "type": "债券"},
    {"code": "511880", "name": "银华日利", "type": "货币"},
]


class DataSourceService:
    """数据源服务"""
    
    def __init__(self):
        self.data_source = DataSource()
        self._cache = {}
        self._stock_list_cache = None
        self._stock_list_cache_time = 0
    
    def get_etf_list(self) -> List[Dict[str, str]]:
        """获取ETF列表"""
        return ETF_LIST
    
    def get_etf_info(self, code: str) -> Dict[str, str]:
        """获取ETF信息"""
        for etf in ETF_LIST:
            if etf["code"] == code:
                return etf
        return {"code": code, "name": "未知", "type": "其他"}
    
    def get_etf_history(
        self,
        code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        获取ETF历史数据
        
        Args:
            code: ETF代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            历史数据列表
        """
        cache_key = f"etf_{code}_{start_date}_{end_date}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            df = self.data_source.get_etf_history(code, start_date, end_date)
            
            if df is None or df.empty:
                return []
            
            df = df.reset_index()
            
            result = []
            for _, row in df.iterrows():
                result.append({
                    "date": row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], 'strftime') else str(row["date"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]) if "volume" in row else 0
                })
            
            self._cache[cache_key] = result
            return result
            
        except Exception as e:
            print(f"获取数据失败: {e}")
            return []
    
    def get_stock_history(
        self,
        code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        获取股票历史数据
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            历史数据列表
        """
        cache_key = f"stock_{code}_{start_date}_{end_date}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            df = self.data_source.get_stock_history(code, start_date, end_date)
            
            if df is None or df.empty:
                return []
            
            df = df.reset_index()
            
            result = []
            for _, row in df.iterrows():
                result.append({
                    "date": row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], 'strftime') else str(row["date"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]) if "volume" in row else 0
                })
            
            self._cache[cache_key] = result
            return result
            
        except Exception as e:
            print(f"获取股票数据失败: {e}")
            return []
    
    def _get_all_stocks(self) -> List[Dict[str, str]]:
        """
        获取所有A股列表（带缓存）
        
        Returns:
            股票列表
        """
        import time
        
        cache_expire = 3600
        
        if self._stock_list_cache and (time.time() - self._stock_list_cache_time) < cache_expire:
            return self._stock_list_cache
        
        try:
            if ef is None:
                return self._get_default_stocks()
            
            df = ef.stock.get_base_info("A股")
            
            if df is None or df.empty:
                return self._get_default_stocks()
            
            result = []
            for _, row in df.iterrows():
                code = str(row.get("股票代码", ""))
                name = str(row.get("股票名称", ""))
                
                if code and name:
                    result.append({
                        "code": code,
                        "name": name,
                        "market": "SH" if code.startswith("6") else "SZ",
                        "industry": ""
                    })
            
            self._stock_list_cache = result
            self._stock_list_cache_time = time.time()
            return result
            
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return self._get_default_stocks()
    
    def _get_default_stocks(self) -> List[Dict[str, str]]:
        """获取默认热门股票列表"""
        return [
            {"code": "600519", "name": "贵州茅台", "market": "SH", "industry": "白酒"},
            {"code": "000858", "name": "五粮液", "market": "SZ", "industry": "白酒"},
            {"code": "601318", "name": "中国平安", "market": "SH", "industry": "保险"},
            {"code": "000333", "name": "美的集团", "market": "SZ", "industry": "家电"},
            {"code": "600036", "name": "招商银行", "market": "SH", "industry": "银行"},
            {"code": "601166", "name": "兴业银行", "market": "SH", "industry": "银行"},
            {"code": "000651", "name": "格力电器", "market": "SZ", "industry": "家电"},
            {"code": "600276", "name": "恒瑞医药", "market": "SH", "industry": "医药"},
            {"code": "000002", "name": "万科A", "market": "SZ", "industry": "房地产"},
            {"code": "601398", "name": "工商银行", "market": "SH", "industry": "银行"},
            {"code": "600000", "name": "浦发银行", "market": "SH", "industry": "银行"},
            {"code": "000001", "name": "平安银行", "market": "SZ", "industry": "银行"},
            {"code": "601288", "name": "农业银行", "market": "SH", "industry": "银行"},
            {"code": "600030", "name": "中信证券", "market": "SH", "industry": "证券"},
            {"code": "601888", "name": "中国中免", "market": "SH", "industry": "零售"},
            {"code": "002594", "name": "比亚迪", "market": "SZ", "industry": "汽车"},
            {"code": "300750", "name": "宁德时代", "market": "SZ", "industry": "电池"},
            {"code": "600900", "name": "长江电力", "market": "SH", "industry": "电力"},
            {"code": "601012", "name": "隆基绿能", "market": "SH", "industry": "光伏"},
            {"code": "002475", "name": "立讯精密", "market": "SZ", "industry": "电子"},
        ]
    
    def search_stocks(self, keyword: str, limit: int = 20) -> List[Dict[str, str]]:
        """
        搜索股票
        
        Args:
            keyword: 搜索关键词（股票代码或名称）
            limit: 返回结果数量限制
            
        Returns:
            匹配的股票列表
        """
        all_stocks = self._get_all_stocks()
        
        keyword = keyword.strip().lower()
        
        exact_matches = []
        code_prefix_matches = []
        name_contains_matches = []
        
        for stock in all_stocks:
            code = stock["code"].lower()
            name = stock["name"].lower()
            
            if code == keyword or name == keyword:
                exact_matches.append(stock)
            elif code.startswith(keyword):
                code_prefix_matches.append(stock)
            elif keyword in name:
                name_contains_matches.append(stock)
        
        results = exact_matches + code_prefix_matches + name_contains_matches
        
        return results[:limit]
    
    def get_hs300_constituents(self) -> List[Dict[str, str]]:
        """
        获取沪深300成分股列表
        
        Returns:
            沪深300成分股列表
        """
        try:
            if ef is None:
                return self._get_default_hs300()
            
            df = ef.stock.get_quote_history('000300', klt=101, fqt=1)
            if df is not None and len(df) > 0:
                pass
            
            realtime_df = ef.stock.get_realtime_quotes()
            if realtime_df is not None and len(realtime_df) > 0:
                codes = realtime_df['股票代码'].tolist()[:100]
                names = realtime_df['股票名称'].tolist()[:100]
                result = []
                for code, name in zip(codes, names):
                    code_str = str(code).zfill(6)
                    if code_str.startswith(('6', '0', '3')):
                        result.append({
                            "code": code_str,
                            "name": str(name),
                            "market": "SH" if code_str.startswith("6") else "SZ",
                            "industry": ""
                        })
                return result
            
        except Exception as e:
            print(f"获取沪深300成分股失败: {e}")
        
        return self._get_default_hs300()
    
    def _get_default_hs300(self) -> List[Dict[str, str]]:
        """获取默认沪深300成分股列表（部分代表性股票）"""
        return [
            {"code": "600519", "name": "贵州茅台", "market": "SH", "industry": "白酒"},
            {"code": "601318", "name": "中国平安", "market": "SH", "industry": "保险"},
            {"code": "600036", "name": "招商银行", "market": "SH", "industry": "银行"},
            {"code": "601166", "name": "兴业银行", "market": "SH", "industry": "银行"},
            {"code": "600887", "name": "伊利股份", "market": "SH", "industry": "食品"},
            {"code": "601398", "name": "工商银行", "market": "SH", "industry": "银行"},
            {"code": "600030", "name": "中信证券", "market": "SH", "industry": "证券"},
            {"code": "601288", "name": "农业银行", "market": "SH", "industry": "银行"},
            {"code": "600276", "name": "恒瑞医药", "market": "SH", "industry": "医药"},
            {"code": "600000", "name": "浦发银行", "market": "SH", "industry": "银行"},
            {"code": "601888", "name": "中国中免", "market": "SH", "industry": "零售"},
            {"code": "600016", "name": "民生银行", "market": "SH", "industry": "银行"},
            {"code": "601012", "name": "隆基绿能", "market": "SH", "industry": "光伏"},
            {"code": "600048", "name": "保利发展", "market": "SH", "industry": "房地产"},
            {"code": "600900", "name": "长江电力", "market": "SH", "industry": "电力"},
            {"code": "601328", "name": "交通银行", "market": "SH", "industry": "银行"},
            {"code": "601939", "name": "建设银行", "market": "SH", "industry": "银行"},
            {"code": "600028", "name": "中国石化", "market": "SH", "industry": "石化"},
            {"code": "601988", "name": "中国银行", "market": "SH", "industry": "银行"},
            {"code": "600585", "name": "海螺水泥", "market": "SH", "industry": "建材"},
            {"code": "601668", "name": "中国建筑", "market": "SH", "industry": "建筑"},
            {"code": "600346", "name": "恒力石化", "market": "SH", "industry": "石化"},
            {"code": "601818", "name": "光大银行", "market": "SH", "industry": "银行"},
            {"code": "600690", "name": "海尔智家", "market": "SH", "industry": "家电"},
            {"code": "000858", "name": "五粮液", "market": "SZ", "industry": "白酒"},
            {"code": "000333", "name": "美的集团", "market": "SZ", "industry": "家电"},
            {"code": "000651", "name": "格力电器", "market": "SZ", "industry": "家电"},
            {"code": "000002", "name": "万科A", "market": "SZ", "industry": "房地产"},
            {"code": "000001", "name": "平安银行", "market": "SZ", "industry": "银行"},
            {"code": "002594", "name": "比亚迪", "market": "SZ", "industry": "汽车"},
            {"code": "300750", "name": "宁德时代", "market": "SZ", "industry": "电池"},
            {"code": "002475", "name": "立讯精密", "market": "SZ", "industry": "电子"},
            {"code": "000725", "name": "京东方A", "market": "SZ", "industry": "电子"},
            {"code": "002415", "name": "海康威视", "market": "SZ", "industry": "电子"},
            {"code": "000063", "name": "中兴通讯", "market": "SZ", "industry": "通信"},
            {"code": "002352", "name": "顺丰控股", "market": "SZ", "industry": "物流"},
            {"code": "000568", "name": "泸州老窖", "market": "SZ", "industry": "白酒"},
            {"code": "002304", "name": "洋河股份", "market": "SZ", "industry": "白酒"},
            {"code": "000333", "name": "美的集团", "market": "SZ", "industry": "家电"},
        ]
