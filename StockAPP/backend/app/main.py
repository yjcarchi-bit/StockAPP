"""
FastAPI 应用入口
================
A股量化回测平台后端 API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import backtest, data, strategies, data_update
from .config import settings

app = FastAPI(
    title="StockAPP API",
    description="A股量化回测平台 API",
    version="2.0.0",
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
