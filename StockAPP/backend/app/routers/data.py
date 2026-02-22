"""
数据 API 路由
==============

提供股票、ETF数据查询接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..models import ETFInfo, ETFData, StockInfo, APIResponse

router = APIRouter()


@router.get("/etf/list", response_model=List[ETFInfo])
async def get_etf_list():
    """
    获取ETF列表
    
    返回所有可用的ETF信息
    """
    try:
        from ..services.data_source import DataSourceService
        
        service = DataSourceService()
        etfs = service.get_etf_list()
        return [ETFInfo(**etf) for etf in etfs]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/etf/{code}", response_model=ETFData)
async def get_etf_data(
    code: str,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD")
):
    """
    获取ETF历史数据
    
    - **code**: ETF代码
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    """
    try:
        from ..services.data_source import DataSourceService
        
        service = DataSourceService()
        data = service.get_etf_history(code, start_date, end_date)
        info = service.get_etf_info(code)
        
        return ETFData(code=code, name=info.get("name", code), data=data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/etf/{code}/info", response_model=ETFInfo)
async def get_etf_info(code: str):
    """
    获取ETF信息
    
    - **code**: ETF代码
    """
    try:
        from ..services.data_source import DataSourceService
        
        service = DataSourceService()
        info = service.get_etf_info(code)
        return ETFInfo(**info)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/search", response_model=List[StockInfo])
async def search_stocks(
    keyword: str = Query(..., description="搜索关键词（股票代码或名称）", min_length=1),
    limit: int = Query(20, description="返回结果数量限制", ge=1, le=100)
):
    """
    搜索股票
    
    - **keyword**: 搜索关键词（股票代码或名称）
    - **limit**: 返回结果数量限制
    """
    try:
        from ..services.data_source import DataSourceService
        
        service = DataSourceService()
        stocks = service.search_stocks(keyword, limit)
        return [StockInfo(**stock) for stock in stocks]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/{code}", response_model=ETFData)
async def get_stock_data(
    code: str,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD")
):
    """
    获取股票历史数据
    
    - **code**: 股票代码
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    """
    try:
        from ..services.data_source import DataSourceService
        
        service = DataSourceService()
        data = service.get_stock_history(code, start_date, end_date)
        stocks = service.search_stocks(code, 1)
        name = stocks[0].get("name", code) if stocks else code
        
        return ETFData(code=code, name=name, data=data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hs300/stocks", response_model=List[StockInfo])
async def get_hs300_stocks():
    """
    获取沪深300成分股列表
    
    返回沪深300指数的成分股代码和名称
    """
    try:
        from ..services.data_source import DataSourceService
        
        service = DataSourceService()
        stocks = service.get_hs300_constituents()
        return [StockInfo(**stock) for stock in stocks]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/batch", response_model=List[ETFData])
async def get_stocks_batch(
    codes: str = Query(..., description="股票代码列表，逗号分隔"),
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD")
):
    """
    批量获取股票历史数据
    
    - **codes**: 股票代码列表，逗号分隔（最多50个）
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    """
    try:
        from ..services.data_source import DataSourceService
        
        code_list = [c.strip() for c in codes.split(',') if c.strip()]
        if len(code_list) > 50:
            code_list = code_list[:50]
        
        service = DataSourceService()
        results = []
        
        for code in code_list:
            try:
                data = service.get_stock_history(code, start_date, end_date)
                stocks = service.search_stocks(code, 1)
                name = stocks[0].get("name", code) if stocks else code
                results.append(ETFData(code=code, name=name, data=data))
            except Exception:
                pass
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
