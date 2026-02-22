"""
FastAPI 应用入口
================
A股量化回测平台后端 API
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import backtest, data, strategies, data_update, websocket
from .config import settings
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.etf_pool import ETFPool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    from core.scheduler import init_scheduler
    from backend.app.routers.websocket import manager
    
    etf_pool = ETFPool()
    scheduler = init_scheduler(
        etf_pool=etf_pool.get_default_pool(),
        etf_names={code: info.name for code, info in etf_pool.DEFAULT_ETF_POOL.items()},
        connection_manager=manager,
    )
    scheduler.start()
    
    yield
    
    scheduler.stop()


app = FastAPI(
    title="StockAPP API",
    description="A股量化回测平台 API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(backtest.router, prefix="/api/backtest", tags=["回测"])
app.include_router(data.router, prefix="/api/data", tags=["数据"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["策略"])
app.include_router(data_update.router, prefix="/api/data-update", tags=["数据更新"])
app.include_router(websocket.router, prefix="/ws", tags=["实时数据"])


@app.get("/")
async def root():
    return {
        "name": "StockAPP API",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
