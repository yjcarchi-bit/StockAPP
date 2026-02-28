"""
回测 API 路由
==============
"""

from fastapi import APIRouter, HTTPException
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..models import (
    BacktestRequest,
    CompareRequest,
    OptimizeRequest,
    BacktestResult,
    CompareResult,
    OptimizationResult,
)

router = APIRouter()


@router.post("/run", response_model=BacktestResult)
async def run_backtest(request: BacktestRequest):
    """
    运行回测
    
    - **strategy**: 策略名称
    - **strategy_params**: 策略参数
    - **backtest_params**: 回测参数
    - **etf_codes**: ETF代码列表
    """
    try:
        from ..services.backtest_engine import BacktestService
        
        service = BacktestService()
        result = service.run(
            strategy=request.strategy,
            strategy_params=request.strategy_params,
            backtest_params=request.backtest_params.model_dump(),
            etf_codes=request.etf_codes
        )
        
        result["result_id"] = str(uuid.uuid4())
        return BacktestResult(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", response_model=CompareResult)
async def compare_strategies(request: CompareRequest):
    """
    策略对比
    
    - **strategies**: 策略列表 (2-3个)
    - **strategy_params_list**: 各策略参数
    - **backtest_params**: 回测参数
    - **etf_codes**: ETF代码列表
    """
    try:
        from ..services.backtest_engine import BacktestService
        
        service = BacktestService()
        results = []
        
        for i, strategy in enumerate(request.strategies):
            params = request.strategy_params_list[i] if i < len(request.strategy_params_list) else {}
            result = service.run(
                strategy=strategy,
                strategy_params=params,
                backtest_params=request.backtest_params.model_dump(),
                etf_codes=request.etf_codes
            )
            result["result_id"] = str(uuid.uuid4())
            result["strategy"] = strategy
            results.append(BacktestResult(**result))
        
        best_return = max(results, key=lambda x: x.metrics.total_return)
        best_sharpe = max(results, key=lambda x: x.metrics.sharpe_ratio)
        min_drawdown = min(results, key=lambda x: x.metrics.max_drawdown)
        
        return CompareResult(
            results=results,
            best_return_strategy=best_return.strategy,
            best_sharpe_strategy=best_sharpe.strategy,
            min_drawdown_strategy=min_drawdown.strategy
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize", response_model=OptimizationResult)
async def optimize_parameters(request: OptimizeRequest):
    """
    参数优化
    
    - **strategy**: 策略名称
    - **param_grid**: 参数网格
    - **fixed_params**: 固定参数
    - **backtest_params**: 回测参数
    - **etf_codes**: ETF代码列表
    - **optimization_metric**: 优化目标
    - **method**: 优化方法 (grid/random)
    - **n_iter**: 随机搜索迭代次数
    """
    try:
        from ..services.optimizer import OptimizerService
        
        service = OptimizerService()
        result = service.optimize(
            strategy=request.strategy,
            param_grid=request.param_grid,
            fixed_params=request.fixed_params,
            backtest_params=request.backtest_params.model_dump(),
            etf_codes=request.etf_codes,
            metric=request.optimization_metric,
            method=request.method,
            n_iter=request.n_iter
        )
        
        return OptimizationResult(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
