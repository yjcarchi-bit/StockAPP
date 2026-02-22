"""
数据更新服务
============
定时更新股票和ETF数据
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from typing import List, Optional, Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import DataSource


class DataUpdateService:
    """
    数据更新服务
    
    定时更新股票和ETF数据，支持每日自动更新
    
    Example:
        >>> service = DataUpdateService()
        >>> service.add_etf_codes(['510300', '510500'])
        >>> service.start()  # 启动定时更新
        >>> service.update_now()  # 立即更新
    """
    
    DEFAULT_ETF_CODES = [
        "518880",  # 黄金ETF
        "513100",  # 纳指ETF
        "510300",  # 沪深300ETF
        "510500",  # 中证500ETF
        "159915",  # 创业板ETF
        "511880",  # 银华日利
        "159941",  # 纳指ETF
        "513050",  # 中概互联ETF
        "512880",  # 证券ETF
        "512690",  # 酒ETF
    ]
    
    def __init__(
        self,
        update_time: str = "16:00",
        update_callback: Optional[Callable] = None
    ):
        """
        初始化数据更新服务
        
        Args:
            update_time: 每日更新时间，格式 "HH:MM"
            update_callback: 更新完成后的回调函数
        """
        self.data_source = DataSource()
        self.update_time = update_time
        self.update_callback = update_callback
        
        self.etf_codes: List[str] = self.DEFAULT_ETF_CODES.copy()
        self.stock_codes: List[str] = []
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_update: Optional[datetime] = None
    
    def add_etf_codes(self, codes: List[str]) -> None:
        """添加ETF代码"""
        for code in codes:
            if code not in self.etf_codes:
                self.etf_codes.append(code)
    
    def add_stock_codes(self, codes: List[str]) -> None:
        """添加股票代码"""
        for code in codes:
            if code not in self.stock_codes:
                self.stock_codes.append(code)
    
    def set_etf_codes(self, codes: List[str]) -> None:
        """设置ETF代码列表"""
        self.etf_codes = codes.copy()
    
    def set_stock_codes(self, codes: List[str]) -> None:
        """设置股票代码列表"""
        self.stock_codes = codes.copy()
    
    def _get_date_range(self) -> tuple:
        """获取数据日期范围"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 10)  # 10年数据
        return (
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
    
    def update_etf_data(self) -> dict:
        """
        更新ETF数据
        
        Returns:
            更新结果统计
        """
        start_date, end_date = self._get_date_range()
        
        results = {
            "total": len(self.etf_codes),
            "success": 0,
            "failed": 0,
            "errors": []
        }
        
        print(f"[{datetime.now()}] 开始更新ETF数据...")
        
        for code in self.etf_codes:
            try:
                df = self.data_source.get_etf_history(
                    code, start_date, end_date, use_cache=False
                )
                if df is not None and len(df) > 0:
                    results["success"] += 1
                    print(f"  ✓ {code}: {len(df)} 条记录")
                else:
                    results["failed"] += 1
                    results["errors"].append(f"{code}: 无数据")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{code}: {str(e)}")
                print(f"  ✗ {code}: {e}")
        
        print(f"[{datetime.now()}] ETF数据更新完成: 成功 {results['success']}, 失败 {results['failed']}")
        
        return results
    
    def update_stock_data(self) -> dict:
        """
        更新股票数据
        
        Returns:
            更新结果统计
        """
        if not self.stock_codes:
            return {"total": 0, "success": 0, "failed": 0, "errors": []}
        
        start_date, end_date = self._get_date_range()
        
        results = {
            "total": len(self.stock_codes),
            "success": 0,
            "failed": 0,
            "errors": []
        }
        
        print(f"[{datetime.now()}] 开始更新股票数据...")
        
        for code in self.stock_codes:
            try:
                df = self.data_source.get_stock_history(
                    code, start_date, end_date, use_cache=False
                )
                if df is not None and len(df) > 0:
                    results["success"] += 1
                    print(f"  ✓ {code}: {len(df)} 条记录")
                else:
                    results["failed"] += 1
                    results["errors"].append(f"{code}: 无数据")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{code}: {str(e)}")
                print(f"  ✗ {code}: {e}")
        
        print(f"[{datetime.now()}] 股票数据更新完成: 成功 {results['success']}, 失败 {results['failed']}")
        
        return results
    
    def update_now(self) -> dict:
        """
        立即更新所有数据
        
        Returns:
            更新结果统计
        """
        etf_results = self.update_etf_data()
        stock_results = self.update_stock_data()
        
        self._last_update = datetime.now()
        
        results = {
            "etf": etf_results,
            "stock": stock_results,
            "update_time": self._last_update.isoformat()
        }
        
        if self.update_callback:
            try:
                self.update_callback(results)
            except Exception as e:
                print(f"回调函数执行失败: {e}")
        
        return results
    
    def _schedule_loop(self) -> None:
        """定时更新循环"""
        while self._running:
            now = datetime.now()
            
            try:
                update_hour, update_minute = map(int, self.update_time.split(":"))
                next_update = now.replace(
                    hour=update_hour, 
                    minute=update_minute, 
                    second=0, 
                    microsecond=0
                )
                
                if next_update <= now:
                    next_update += timedelta(days=1)
                
                wait_seconds = (next_update - now).total_seconds()
                
                if self._last_update is None or self._last_update.date() < now.date():
                    if now.hour >= update_hour:
                        print(f"[{now}] 执行每日数据更新...")
                        self.update_now()
                
                time.sleep(min(wait_seconds, 60))
                
            except Exception as e:
                print(f"定时更新出错: {e}")
                time.sleep(60)
    
    def start(self) -> None:
        """启动定时更新服务"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._schedule_loop, daemon=True)
        self._thread.start()
        print(f"数据更新服务已启动，每日 {self.update_time} 更新")
    
    def stop(self) -> None:
        """停止定时更新服务"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        print("数据更新服务已停止")
    
    def get_status(self) -> dict:
        """获取服务状态"""
        return {
            "running": self._running,
            "update_time": self.update_time,
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "etf_codes_count": len(self.etf_codes),
            "stock_codes_count": len(self.stock_codes),
        }


_service_instance: Optional[DataUpdateService] = None


def get_update_service() -> DataUpdateService:
    """获取全局数据更新服务实例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = DataUpdateService()
    return _service_instance
