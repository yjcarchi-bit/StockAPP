"""
数据更新 API 路由
================

提供数据更新管理接口
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..models import APIResponse

router = APIRouter()


@router.get("/status")
async def get_update_status():
    """
    获取数据更新服务状态
    """
    try:
        from core.data_update_service import get_update_service
        
        service = get_update_service()
        return service.get_status()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger", response_model=APIResponse)
async def trigger_update(background_tasks: BackgroundTasks):
    """
    触发数据更新（后台执行）
    """
    try:
        from core.data_update_service import get_update_service
        
        service = get_update_service()
        
        def run_update():
            service.update_now()
        
        background_tasks.add_task(run_update)
        
        return APIResponse(success=True, message="数据更新任务已启动")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-now")
async def update_now():
    """
    立即更新数据（同步执行）
    """
    try:
        from core.data_update_service import get_update_service
        
        service = get_update_service()
        results = service.update_now()
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start", response_model=APIResponse)
async def start_service():
    """
    启动数据更新服务
    """
    try:
        from core.data_update_service import get_update_service
        
        service = get_update_service()
        service.start()
        
        return APIResponse(success=True, message="数据更新服务已启动")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=APIResponse)
async def stop_service():
    """
    停止数据更新服务
    """
    try:
        from core.data_update_service import get_update_service
        
        service = get_update_service()
        service.stop()
        
        return APIResponse(success=True, message="数据更新服务已停止")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/set-codes", response_model=APIResponse)
async def set_codes(etf_codes: Optional[List[str]] = None, stock_codes: Optional[List[str]] = None):
    """
    设置要更新的证券代码
    """
    try:
        from core.data_update_service import get_update_service
        
        service = get_update_service()
        
        if etf_codes:
            service.set_etf_codes(etf_codes)
        
        if stock_codes:
            service.set_stock_codes(stock_codes)
        
        return APIResponse(
            success=True, 
            message=f"已设置 {len(etf_codes or [])} 个ETF, {len(stock_codes or [])} 只股票"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache")
async def clear_cache():
    """
    清除数据缓存
    """
    try:
        from core import DataSource
        
        ds = DataSource()
        count = ds.clear_cache()
        
        return {"success": True, "message": f"已清除 {count} 个缓存文件"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/info")
async def get_cache_info():
    """
    获取缓存信息
    """
    try:
        from core import DataSource
        
        ds = DataSource()
        info = ds.get_cache_info()
        
        return info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
