"""宏观数据 API 路由。

路由职责：
1. 参数接收与基础校验（由 FastAPI + Query 完成）
2. 调用 `MacroDataService` 执行业务
3. 统一异常映射为 HTTP 状态码
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..models import MacroAPIInfo, MacroDataResponse
from ..services.macro_data_service import MacroApiNotSupportedError, MacroDataService

router = APIRouter()


@router.get("/apis", response_model=List[MacroAPIInfo])
async def list_macro_apis():
    """返回已封装的宏观接口清单（含默认查询区间）。"""
    try:
        service = MacroDataService()
        return [MacroAPIInfo(**item) for item in service.list_supported_apis()]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{api_name}", response_model=MacroDataResponse)
async def query_macro_data(
    api_name: str,
    start: Optional[str] = Query(None, description="起始时间（按接口粒度：YYYY-MM-DD / YYYYMM / YYYYQn）"),
    end: Optional[str] = Query(None, description="结束时间（按接口粒度：YYYY-MM-DD / YYYYMM / YYYYQn）"),
    limit: int = Query(500, ge=1, le=5000, description="返回记录上限"),
    cache_only: bool = Query(False, description="仅从MySQL缓存读取，不请求Tushare"),
):
    """
    查询宏观数据（实时拉取或缓存读取）。

    参数说明：
    - `api_name`: 宏观接口名（必须在后端白名单中）
    - `start/end`: 起止时间（格式随接口粒度而变化）
    - `limit`: 返回记录上限，防止单次响应过大
    - `cache_only`: 是否只走缓存

    行为说明：
    - `cache_only=false`：调用 Tushare 并执行 MySQL upsert
    - `cache_only=true`：只查询 MySQL，不请求 Tushare
    """
    try:
        service = MacroDataService()
        result = (
            service.get_cached_macro(api_name=api_name, start=start, end=end, limit=limit)
            if cache_only
            else service.fetch_macro(api_name=api_name, start=start, end=end, limit=limit)
        )
        return MacroDataResponse(**result)
    except MacroApiNotSupportedError as exc:
        # 接口名不存在 -> 404 更符合“资源不存在”语义。
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        # 参数格式错误 -> 400。
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        # 其他异常统一按服务端错误返回。
        raise HTTPException(status_code=500, detail=str(exc))
