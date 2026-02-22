"""
ETF池配置模块
=============
常用ETF的定义和分类

特性:
- ETF分类管理
- ETF信息查询
- 自定义ETF池
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class ETFCategory(Enum):
    """ETF分类"""
    STOCK = "股票型"
    BOND = "债券型"
    COMMODITY = "商品型"
    CROSS_BORDER = "跨境型"
    MONEY = "货币型"
    OTHER = "其他"


@dataclass
class ETFInfo:
    """
    ETF信息
    
    Attributes:
        code: ETF代码
        name: ETF名称
        category: ETF分类
        exchange: 交易所
        track_index: 跟踪指数
    """
    
    code: str
    name: str
    category: ETFCategory = ETFCategory.OTHER
    exchange: str = ""
    track_index: str = ""
    
    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "category": self.category.value,
            "exchange": self.exchange,
            "track_index": self.track_index,
        }


class ETFPool:
    """
    ETF池管理类
    
    Example:
        >>> pool = ETFPool()
        >>> pool.get_by_category(ETFCategory.STOCK)
        >>> pool.get_info("510300")
    """
    
    DEFAULT_ETF_POOL = {
        "518880": ETFInfo("518880", "黄金ETF", ETFCategory.COMMODITY, "SH", "黄金现货"),
        "513100": ETFInfo("513100", "纳指ETF", ETFCategory.CROSS_BORDER, "SH", "纳斯达克100"),
        "513500": ETFInfo("513500", "标普500ETF", ETFCategory.CROSS_BORDER, "SH", "标普500"),
        "513520": ETFInfo("513520", "日经ETF", ETFCategory.CROSS_BORDER, "SH", "日经225"),
        "513030": ETFInfo("513030", "德国ETF", ETFCategory.CROSS_BORDER, "SH", "德国DAX"),
        "513080": ETFInfo("513080", "法国ETF", ETFCategory.CROSS_BORDER, "SH", "法国CAC40"),
        "159920": ETFInfo("159920", "恒生ETF", ETFCategory.CROSS_BORDER, "SZ", "恒生指数"),
        
        "510300": ETFInfo("510300", "沪深300ETF", ETFCategory.STOCK, "SH", "沪深300"),
        "510500": ETFInfo("510500", "中证500ETF", ETFCategory.STOCK, "SH", "中证500"),
        "510050": ETFInfo("510050", "上证50ETF", ETFCategory.STOCK, "SH", "上证50"),
        "510210": ETFInfo("510210", "上证指数ETF", ETFCategory.STOCK, "SH", "上证指数"),
        "159915": ETFInfo("159915", "创业板ETF", ETFCategory.STOCK, "SZ", "创业板指"),
        "588080": ETFInfo("588080", "科创板50ETF", ETFCategory.STOCK, "SH", "科创50"),
        
        "159980": ETFInfo("159980", "有色ETF", ETFCategory.COMMODITY, "SZ", "有色金属"),
        "159985": ETFInfo("159985", "豆粕ETF", ETFCategory.COMMODITY, "SZ", "豆粕期货"),
        "501018": ETFInfo("501018", "南方原油LOF", ETFCategory.COMMODITY, "SH", "原油"),
        
        "159995": ETFInfo("159995", "芯片ETF", ETFCategory.STOCK, "SZ", "国证芯片"),
        "159852": ETFInfo("159852", "半导体ETF", ETFCategory.STOCK, "SZ", "中证半导体"),
        "159845": ETFInfo("159845", "新能源ETF", ETFCategory.STOCK, "SZ", "中证新能源"),
        "515030": ETFInfo("515030", "新能源车ETF", ETFCategory.STOCK, "SH", "中证新能源汽车"),
        "159806": ETFInfo("159806", "光伏ETF", ETFCategory.STOCK, "SZ", "中证光伏产业"),
        "516160": ETFInfo("516160", "新能源ETF", ETFCategory.STOCK, "SH", "中证新能源"),
        "159928": ETFInfo("159928", "消费ETF", ETFCategory.STOCK, "SZ", "中证主要消费"),
        "512670": ETFInfo("512670", "国防军工ETF", ETFCategory.STOCK, "SH", "中证国防军工"),
        
        "511010": ETFInfo("511010", "国债ETF", ETFCategory.BOND, "SH", "国债指数"),
        "511220": ETFInfo("511220", "城投债ETF", ETFCategory.BOND, "SH", "城投债"),
        "511880": ETFInfo("511880", "银华日利", ETFCategory.MONEY, "SH", "货币基金"),
    }
    
    def __init__(self):
        self._etfs: Dict[str, ETFInfo] = dict(self.DEFAULT_ETF_POOL)
    
    def get_info(self, code: str) -> Optional[ETFInfo]:
        """获取ETF信息"""
        return self._etfs.get(code)
    
    def get_name(self, code: str) -> str:
        """获取ETF名称"""
        info = self.get_info(code)
        return info.name if info else code
    
    def get_all_codes(self) -> List[str]:
        """获取所有ETF代码"""
        return list(self._etfs.keys())
    
    def get_all_etfs(self) -> List[ETFInfo]:
        """获取所有ETF信息"""
        return list(self._etfs.values())
    
    def get_by_category(self, category: ETFCategory) -> List[ETFInfo]:
        """按分类获取ETF"""
        return [etf for etf in self._etfs.values() if etf.category == category]
    
    def get_categories(self) -> List[ETFCategory]:
        """获取所有分类"""
        return list(set(etf.category for etf in self._etfs.values()))
    
    def add_etf(self, etf: ETFInfo) -> None:
        """添加ETF"""
        self._etfs[etf.code] = etf
    
    def remove_etf(self, code: str) -> bool:
        """移除ETF"""
        if code in self._etfs:
            del self._etfs[code]
            return True
        return False
    
    def get_default_pool(self) -> List[str]:
        """获取默认ETF池（用于策略）"""
        return [
            "518880", "159980", "159985", "501018",
            "513100", "513500", "513520", "513030", "513080",
            "159920",
            "510300", "510500", "510050", "510210", "159915",
            "588080", "159995", "513050", "159852", "159845",
            "515030", "159806", "516160", "159928", "512670",
            "511010", "511880",
        ]
    
    def get_defensive_pool(self) -> List[str]:
        """获取防御性ETF池"""
        return ["511880", "511010", "511220"]
    
    def to_dict(self) -> Dict[str, dict]:
        """转换为字典"""
        return {code: etf.to_dict() for code, etf in self._etfs.items()}
    
    @classmethod
    def from_dict(cls, data: Dict[str, dict]) -> "ETFPool":
        """从字典创建"""
        pool = cls()
        pool._etfs = {}
        
        for code, info in data.items():
            pool._etfs[code] = ETFInfo(
                code=info["code"],
                name=info["name"],
                category=ETFCategory(info.get("category", "其他")),
                exchange=info.get("exchange", ""),
                track_index=info.get("track_index", ""),
            )
        
        return pool
