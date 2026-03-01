"""Data update APIs with MySQL-aware storage stats and migration endpoints."""

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..models import APIResponse
from ..services.data_source import DataSourceService
from ..services.data_update_service import get_update_service
from ..services.pkl_migration import migrate_pkl_cache

router = APIRouter()


@router.get("/status")
async def get_update_status():
    try:
        service = get_update_service()
        return service.get_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/trigger", response_model=APIResponse)
async def trigger_update(background_tasks: BackgroundTasks):
    try:
        service = get_update_service()
        background_tasks.add_task(service.update_now)
        return APIResponse(success=True, message="数据更新任务已启动")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/update-now")
async def update_now():
    try:
        service = get_update_service()
        return service.update_now()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/start", response_model=APIResponse)
async def start_service():
    try:
        service = get_update_service()
        service.start()
        return APIResponse(success=True, message="数据更新服务已启动")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/stop", response_model=APIResponse)
async def stop_service():
    try:
        service = get_update_service()
        service.stop()
        return APIResponse(success=True, message="数据更新服务已停止")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/set-codes", response_model=APIResponse)
async def set_codes(etf_codes: Optional[List[str]] = None, stock_codes: Optional[List[str]] = None):
    try:
        service = get_update_service()
        if etf_codes:
            service.set_etf_codes(etf_codes)
        if stock_codes:
            service.set_stock_codes(stock_codes)
        return APIResponse(
            success=True,
            message=f"已设置 {len(etf_codes or [])} 个ETF, {len(stock_codes or [])} 只股票",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/migrate-pkl", response_model=APIResponse)
async def migrate_legacy_pkl(background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(migrate_pkl_cache)
        return APIResponse(success=True, message="PKL迁移任务已启动")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/cache")
async def clear_cache():
    try:
        service = DataSourceService()
        result = service.clear_cache()
        return {"success": True, "message": result.get("message", "清理完成"), **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/cache/info")
async def get_cache_info():
    try:
        service = DataSourceService()
        return service.get_cache_info()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
