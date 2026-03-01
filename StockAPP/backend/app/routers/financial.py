"""财务数据 API 路由。"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..models import FinancialAPIInfo, FinancialDataResponse
from ..services.financial_data_service import FinancialApiNotSupportedError, FinancialDataService

router = APIRouter()


@router.get("/apis", response_model=List[FinancialAPIInfo])
async def list_financial_apis():
    """返回已封装的财务接口清单。"""
    try:
        service = FinancialDataService()
        return [FinancialAPIInfo(**item) for item in service.list_supported_apis()]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{api_name}", response_model=FinancialDataResponse)
async def query_financial_data(
    api_name: str,
    ts_code: str = Query(..., description="证券代码（支持 600519.SH 或 600519）"),
    start: Optional[str] = Query(None, description="起始日期（YYYY-MM-DD 或 YYYYMMDD）"),
    end: Optional[str] = Query(None, description="结束日期（YYYY-MM-DD 或 YYYYMMDD）"),
    limit: int = Query(500, ge=1, le=5000, description="返回记录上限"),
    cache_only: bool = Query(False, description="仅从 MySQL 缓存读取，不请求 Tushare"),
):
    """查询财务数据（实时拉取或缓存读取）。"""
    try:
        service = FinancialDataService()
        result = (
            service.get_cached_financial(api_name=api_name, ts_code=ts_code, start=start, end=end, limit=limit)
            if cache_only
            else service.fetch_financial(api_name=api_name, ts_code=ts_code, start=start, end=end, limit=limit)
        )
        return FinancialDataResponse(**result)
    except FinancialApiNotSupportedError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
