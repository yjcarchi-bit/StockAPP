"""
定时任务调度模块
================
管理实时数据推送和策略信号生成的定时任务

特性:
- 交易时间判断
- 定时数据推送
- 策略信号生成
- 异常恢复机制
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import logging

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None
    CronTrigger = None

from .realtime_data import (
    RealtimeDataProvider, 
    TradingTimeChecker, 
    MarketStatus,
)
from .strategy_signal_service import StrategySignalService


logger = logging.getLogger(__name__)


@dataclass
class SchedulerConfig:
    """调度器配置"""
    quote_interval: int = 3
    signal_interval: int = 60
    cleanup_interval: int = 300
    heartbeat_interval: int = 30


class RealtimeScheduler:
    """
    实时数据调度器
    
    管理实时数据推送和策略信号生成
    
    Example:
        >>> scheduler = RealtimeScheduler(data_provider, signal_service, manager)
        >>> scheduler.start()
    """
    
    def __init__(
        self,
        data_provider: RealtimeDataProvider,
        signal_service: StrategySignalService,
        connection_manager: Any,
        config: Optional[SchedulerConfig] = None,
    ):
        """
        初始化调度器
        
        Args:
            data_provider: 实时数据提供者
            signal_service: 策略信号服务
            connection_manager: WebSocket连接管理器
            config: 调度器配置
        """
        self.data_provider = data_provider
        self.signal_service = signal_service
        self.connection_manager = connection_manager
        self.config = config or SchedulerConfig()
        
        self._running = False
        self._tasks: list = []
        self._scheduler: Optional[AsyncIOScheduler] = None
        
        self._last_quote_time: Optional[datetime] = None
        self._last_signal_time: Optional[datetime] = None
        self._error_count = 0
        self._max_errors = 10
    
    def _should_run(self) -> bool:
        """判断是否应该运行任务"""
        return (
            TradingTimeChecker.is_trading_time() and
            self.connection_manager.get_client_count() > 0
        )
    
    async def _push_quotes(self) -> None:
        """推送实时行情"""
        if not self._should_run():
            return
        
        try:
            quotes = self.data_provider.get_all_quotes()
            quotes_dict = {code: quote.to_dict() for code, quote in quotes.items()}
            
            await self.connection_manager.broadcast_quotes(quotes_dict)
            
            self._last_quote_time = datetime.now()
            self._error_count = 0
            
            logger.debug(f"推送行情数据: {len(quotes)} 只ETF")
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"推送行情失败: {e}")
            
            if self._error_count >= self._max_errors:
                logger.error("错误次数过多，暂停推送")
                await asyncio.sleep(60)
                self._error_count = 0
    
    async def _generate_and_push_signal(self) -> None:
        """生成并推送策略信号"""
        if self.connection_manager.get_client_count() == 0:
            return
        
        try:
            cached_quotes = self.data_provider.get_cached_quotes()
            
            signal = self.signal_service.calculate_signal(cached_quotes)
            
            await self.connection_manager.broadcast_signal(signal.to_dict())
            
            self._last_signal_time = datetime.now()
            
            logger.info(f"推送策略信号: {signal.action} {signal.target_etf}")
            
        except Exception as e:
            logger.error(f"生成信号失败: {e}")
    
    async def _cleanup_connections(self) -> None:
        """清理无效连接"""
        try:
            cleaned = await self.connection_manager.cleanup_dead_connections()
            if cleaned > 0:
                logger.info(f"清理无效连接: {cleaned} 个")
        except Exception as e:
            logger.error(f"清理连接失败: {e}")
    
    async def _run_quote_loop(self) -> None:
        """行情推送循环"""
        while self._running:
            try:
                if TradingTimeChecker.is_trading_time():
                    await self._push_quotes()
                
                await asyncio.sleep(self.config.quote_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"行情循环错误: {e}")
                await asyncio.sleep(self.config.quote_interval)
    
    async def _run_signal_loop(self) -> None:
        """信号生成循环"""
        while self._running:
            try:
                if TradingTimeChecker.is_trading_time():
                    await self._generate_and_push_signal()
                
                await asyncio.sleep(self.config.signal_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"信号循环错误: {e}")
                await asyncio.sleep(self.config.signal_interval)
    
    async def _run_cleanup_loop(self) -> None:
        """清理循环"""
        while self._running:
            try:
                await self._cleanup_connections()
                await asyncio.sleep(self.config.cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理循环错误: {e}")
                await asyncio.sleep(self.config.cleanup_interval)
    
    def start(self) -> None:
        """启动调度器"""
        if self._running:
            return
        
        self._running = True
        
        self._tasks = [
            asyncio.create_task(self._run_quote_loop()),
            asyncio.create_task(self._run_signal_loop()),
            asyncio.create_task(self._run_cleanup_loop()),
        ]
        
        logger.info("实时数据调度器已启动")
    
    async def start_async(self) -> None:
        """异步启动调度器"""
        self.start()
        
        if APSCHEDULER_AVAILABLE and self._scheduler is None:
            self._scheduler = AsyncIOScheduler()
            
            self._scheduler.add_job(
                self._push_quotes,
                CronTrigger(
                    day_of_week="mon-fri",
                    hour="9-11",
                    minute="*",
                    second="*/3",
                ),
                id="quote_push_morning",
            )
            
            self._scheduler.add_job(
                self._push_quotes,
                CronTrigger(
                    day_of_week="mon-fri",
                    hour="13-15",
                    minute="*",
                    second="*/3",
                ),
                id="quote_push_afternoon",
            )
            
            self._scheduler.add_job(
                self._generate_and_push_signal,
                CronTrigger(
                    day_of_week="mon-fri",
                    hour="15",
                    minute="5",
                ),
                id="daily_signal",
            )
            
            self._scheduler.start()
    
    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        
        for task in self._tasks:
            task.cancel()
        
        self._tasks.clear()
        
        if self._scheduler:
            self._scheduler.shutdown()
            self._scheduler = None
        
        logger.info("实时数据调度器已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            "running": self._running,
            "client_count": self.connection_manager.get_client_count(),
            "market_status": TradingTimeChecker.get_market_status().value,
            "last_quote_time": self._last_quote_time.isoformat() if self._last_quote_time else None,
            "last_signal_time": self._last_signal_time.isoformat() if self._last_signal_time else None,
            "error_count": self._error_count,
        }


scheduler: Optional[RealtimeScheduler] = None


def get_scheduler() -> Optional[RealtimeScheduler]:
    """获取调度器实例"""
    return scheduler


def init_scheduler(
    etf_pool: list,
    etf_names: Optional[dict] = None,
    connection_manager: Any = None,
) -> RealtimeScheduler:
    """
    初始化调度器
    
    Args:
        etf_pool: ETF代码列表
        etf_names: ETF名称映射
        connection_manager: WebSocket连接管理器
        
    Returns:
        调度器实例
    """
    global scheduler
    
    data_provider = RealtimeDataProvider(
        etf_pool=etf_pool,
        etf_names=etf_names,
    )
    
    signal_service = StrategySignalService(
        etf_pool=etf_pool,
        etf_names=etf_names,
    )
    
    scheduler = RealtimeScheduler(
        data_provider=data_provider,
        signal_service=signal_service,
        connection_manager=connection_manager,
    )
    
    return scheduler
