"""
策略 API 路由
==============

从策略代码文件中读取策略元信息
"""

from fastapi import APIRouter, HTTPException
from typing import List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..models import StrategyInfo, StrategyListItem

router = APIRouter()


def _get_strategy_meta(strategy_name: str) -> dict:
    """
    从策略代码文件中获取策略元信息
    
    Args:
        strategy_name: 策略名称（对应策略文件名）
        
    Returns:
        策略元信息字典
    """
    strategy_map = {
        "etf_rotation": ("strategies.etf_rotation", "ETFRotationStrategy"),
        "large_cap_low_drawdown": ("strategies.large_cap_low_drawdown", "LargeCapLowDrawdownStrategy"),
        "dual_ma": ("strategies.dual_ma", "DualMAStrategy"),
        "rsi": ("strategies.rsi_strategy", "RSIStrategy"),
        "macd": ("strategies.macd_strategy", "MACDStrategy"),
        "bollinger": ("strategies.bollinger_strategy", "BollingerStrategy"),
        "grid": ("strategies.grid_strategy", "GridTradingStrategy"),
        "fms": ("strategies.fms_strategy", "FMSStrategy"),
        "steal_dog": ("strategies.steal_dog_strategy", "StealDogStrategy"),
        "multi_etf_rotation": ("strategies.multi_etf_rotation", "MultiETFRotationStrategy"),
        "multi_strategy_portfolio": ("strategies.multi_strategy_portfolio", "MultiStrategyPortfolio"),
    }
    
    if strategy_name not in strategy_map:
        return None
    
    module_name, class_name = strategy_map[strategy_name]
    
    try:
        import importlib
        module = importlib.import_module(module_name)
        strategy_class = getattr(module, class_name)
        
        params_info = getattr(strategy_class, 'params_info', {})
        params_list = []
        for param_name, param_info in params_info.items():
            params_list.append({
                "name": param_name,
                **param_info
            })
        
        return {
            "name": strategy_name,
            "display_name": getattr(strategy_class, 'display_name', strategy_name),
            "category": strategy_class.category.value if hasattr(strategy_class, 'category') else "simple",
            "type": _get_strategy_type(strategy_name),
            "icon": _get_strategy_icon(strategy_name),
            "description": getattr(strategy_class, 'description', ''),
            "logic": getattr(strategy_class, 'logic', []),
            "suitable": getattr(strategy_class, 'suitable', ''),
            "risk": getattr(strategy_class, 'risk', ''),
            "params": params_list,
        }
    except Exception as e:
        print(f"获取策略元信息失败: {e}")
        return None


def _get_strategy_type(strategy_name: str) -> str:
    """获取策略类型"""
    type_map = {
        "etf_rotation": "动量策略",
        "large_cap_low_drawdown": "动量策略",
        "dual_ma": "趋势跟踪",
        "rsi": "均值回归",
        "macd": "趋势跟踪",
        "bollinger": "均值回归",
        "grid": "震荡套利",
        "fms": "多因子选股",
        "steal_dog": "动量策略",
        "multi_etf_rotation": "动量策略",
        "multi_strategy_portfolio": "组合策略",
    }
    return type_map.get(strategy_name, "其他")


def _get_strategy_icon(strategy_name: str) -> str:
    """获取策略图标"""
    icon_map = {
        "etf_rotation": "🔄",
        "large_cap_low_drawdown": "🛡️",
        "dual_ma": "📈",
        "rsi": "📊",
        "macd": "📉",
        "bollinger": "📏",
        "grid": "🔲",
        "fms": "🎯",
        "steal_dog": "🐕",
        "multi_etf_rotation": "🌐",
        "multi_strategy_portfolio": "📦",
    }
    return icon_map.get(strategy_name, "📊")


STRATEGY_NAMES = [
    "etf_rotation", "large_cap_low_drawdown", "dual_ma", "rsi", "macd", "bollinger", "grid",
    "fms", "steal_dog", "multi_etf_rotation", "multi_strategy_portfolio"
]


@router.get("", response_model=List[StrategyListItem])
async def get_strategies():
    """
    获取策略列表
    
    返回所有可用的策略信息，从策略代码文件中读取元信息
    """
    result = []
    
    for name in STRATEGY_NAMES:
        meta = _get_strategy_meta(name)
        if meta:
            result.append(StrategyListItem(
                name=meta["name"],
                display_name=meta["display_name"],
                category=meta["category"],
                type=meta["type"],
                description=meta["description"],
                params=meta["params"]
            ))
    
    return result


@router.get("/{strategy_name}", response_model=StrategyInfo)
async def get_strategy(strategy_name: str):
    """
    获取策略详情
    
    - **strategy_name**: 策略名称
    """
    meta = _get_strategy_meta(strategy_name)
    
    if not meta:
        raise HTTPException(status_code=404, detail=f"策略 {strategy_name} 不存在")
    
    return StrategyInfo(
        name=meta["name"],
        display_name=meta["display_name"],
        category=meta["category"],
        type=meta["type"],
        icon=meta["icon"],
        description=meta["description"],
        logic=meta["logic"],
        suitable=meta["suitable"],
        risk=meta["risk"],
        params=meta["params"]
    )
