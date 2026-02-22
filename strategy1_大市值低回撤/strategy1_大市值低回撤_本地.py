#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
克隆自聚宽文章：https://www.joinquant.com/post/67282
标题："低回撤"才是硬道理，3年90倍最大回撤9%
作者：好运来临

本地化版本说明：
- 使用 efinance 库从东方财富获取股票数据
- 本地模拟交易账户，不涉及真实交易
- 保留原策略的核心逻辑：六因子选股 + 回撤锁定 + 动态仓位管理

策略核心思想：
1. 选股：从沪深300成分股中，使用六因子打分系统筛选优质标的
2. 择时：通过沪深300的趋势指标判断市场状态（牛市/熊市）
3. 风控：回撤超过10%触发锁定，需满足解锁条件才能继续交易
4. 仓位：牛市加仓至95%，熊市减仓至60%

运行方式：
    /usr/bin/python3 strategy1_大市值低回撤_本地.py
    
依赖安装：
    /usr/bin/python3 -m pip install efinance numpy pandas --user
"""

import efinance as ef
import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import time

# ===================== 日志配置 =====================
# 配置日志输出格式：时间 - 日志级别 - 消息内容
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


# ===================== 全局配置类 =====================
class Config:
    """
    策略配置类
    
    存储策略运行所需的所有参数配置，包括：
    - 持仓限制
    - 止盈止损比例
    - 牛市判断阈值
    - 回撤控制参数
    
    属性说明：
        max_positions: 最大持仓数量，默认3只
        stop_loss_ratio: 止损比例，默认5%（亏损超过5%触发止损）
        take_profit_ratio: 止盈比例，默认35%（盈利超过35%触发止盈）
        bull_market_threshold: 牛市阈值，沪深300超过20日线3%判定为牛市
        strong_bull_threshold: 强势牛市阈值，超过20日线4%判定为强势牛市
        empty_drawdown: 空仓回撤阈值，回撤超过10%触发清仓锁定
        bull_add_ratio: 牛市加仓比例，牛市时买入金额乘以1.2
        stock_pool_limit: 选股池数量限制，最多分析100只股票
        drawdown_lock: 回撤锁定标记，True时禁止买入
        buy_signals: 当前买入信号列表
        max_total_value: 历史最大账户价值（用于计算回撤）
        starting_cash: 初始资金
    """
    max_positions: int = 3
    stop_loss_ratio: float = 0.05
    take_profit_ratio: float = 0.35
    bull_market_threshold: float = 1.03
    strong_bull_threshold: float = 1.04
    empty_drawdown: float = 0.10
    bull_add_ratio: float = 1.2
    stock_pool_limit: int = 100
    drawdown_lock: bool = False
    buy_signals: List[str] = []
    max_total_value: float = 0.0
    starting_cash: float = 100000.0


# ===================== 模拟账户类 =====================
class Position:
    """
    持仓类
    
    表示单个股票的持仓信息，包括：
    - 股票代码和名称
    - 持仓数量
    - 平均成本
    - 当前价格
    
    属性：
        code: 股票代码（6位数字字符串）
        name: 股票名称
        total_amount: 持仓数量（股）
        avg_cost: 平均买入成本
        current_price: 当前价格
    
    计算属性：
        market_value: 持仓市值 = 持仓数量 × 当前价格
        profit: 持仓盈亏 = (当前价格 - 平均成本) × 持仓数量
        profit_ratio: 盈亏比例 = (当前价格 - 平均成本) / 平均成本
    """
    def __init__(self, code: str, name: str, amount: int, avg_cost: float):
        """
        初始化持仓
        
        参数：
            code: 股票代码
            name: 股票名称
            amount: 持仓数量
            avg_cost: 平均成本
        """
        self.code = code
        self.name = name
        self.total_amount = amount
        self.avg_cost = avg_cost
        self.current_price = avg_cost
    
    @property
    def market_value(self) -> float:
        """计算持仓市值"""
        return self.total_amount * self.current_price
    
    @property
    def profit(self) -> float:
        """计算持仓盈亏金额"""
        return (self.current_price - self.avg_cost) * self.total_amount
    
    @property
    def profit_ratio(self) -> float:
        """计算盈亏比例"""
        if self.avg_cost == 0:
            return 0
        return (self.current_price - self.avg_cost) / self.avg_cost


class Portfolio:
    """
    投资组合类
    
    模拟交易账户，管理资金和持仓，包括：
    - 现金管理
    - 持仓管理
    - 买入/卖出操作
    - 回撤计算
    
    属性：
        starting_cash: 初始资金
        cash: 当前可用现金
        positions: 持仓字典 {股票代码: Position对象}
        total_value: 账户总价值（现金 + 持仓市值）
        max_total_value: 历史最大账户价值（用于计算最大回撤）
    
    主要方法：
        buy(): 买入股票
        sell(): 卖出股票
        update_prices(): 更新持仓价格
        drawdown: 当前回撤比例
    """
    def __init__(self, starting_cash: float = 100000.0):
        """
        初始化投资组合
        
        参数：
            starting_cash: 初始资金，默认10万元
        """
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.positions: Dict[str, Position] = {}
        self.total_value = starting_cash
        self.max_total_value = starting_cash
    
    def update_prices(self, price_dict: Dict[str, float]):
        """
        更新持仓股票的当前价格
        
        参数：
            price_dict: 价格字典 {股票代码: 价格}
        """
        for code, price in price_dict.items():
            if code in self.positions:
                self.positions[code].current_price = price
        self._calculate_total_value()
    
    def _calculate_total_value(self):
        """
        计算账户总价值
        
        总价值 = 现金 + 所有持仓市值
        同时更新历史最大价值（用于回撤计算）
        """
        pos_value = sum(p.market_value for p in self.positions.values())
        self.total_value = self.cash + pos_value
        if self.total_value > self.max_total_value:
            self.max_total_value = self.total_value
    
    @property
    def available_cash(self) -> float:
        """返回可用现金"""
        return self.cash
    
    @property
    def drawdown(self) -> float:
        """
        计算当前回撤比例
        
        回撤 = (历史最大价值 - 当前价值) / 历史最大价值
        
        返回：
            回撤比例，如0.05表示回撤5%
        """
        if self.max_total_value == 0:
            return 0
        return (self.max_total_value - self.total_value) / self.max_total_value
    
    def buy(self, code: str, name: str, amount: int, price: float, commission: float = 0.0003):
        """
        买入股票
        
        参数：
            code: 股票代码
            name: 股票名称
            amount: 买入数量（股）
            price: 买入价格
            commission: 佣金比例，默认万分之三
        
        返回：
            bool: 买入是否成功
        
        费用计算：
            - 买入成本 = 数量 × 价格
            - 佣金 = max(买入成本 × 佣金比例, 5元)
            - 总花费 = 买入成本 + 佣金
        """
        cost = amount * price
        commission_fee = max(cost * commission, 5)  # 最低佣金5元
        total_cost = cost + commission_fee
        
        if total_cost > self.cash:
            log.warning(f"资金不足，无法买入 {code}")
            return False
        
        self.cash -= total_cost
        
        if code in self.positions:
            # 已有持仓，更新平均成本
            pos = self.positions[code]
            total_amount = pos.total_amount + amount
            total_cost_basis = pos.avg_cost * pos.total_amount + cost
            pos.avg_cost = total_cost_basis / total_amount
            pos.total_amount = total_amount
            pos.current_price = price
        else:
            # 新建持仓
            self.positions[code] = Position(code, name, amount, price)
        
        self._calculate_total_value()
        log.info(f"买入成功: {code} ({name}) {amount}股 @ {price:.2f}元")
        return True
    
    def sell(self, code: str, amount: int, price: float, commission: float = 0.0003, tax: float = 0.001):
        """
        卖出股票
        
        参数：
            code: 股票代码
            amount: 卖出数量（股）
            price: 卖出价格
            commission: 佣金比例，默认万分之三
            tax: 印花税比例，默认千分之一
        
        返回：
            bool: 卖出是否成功
        
        费用计算：
            - 卖出金额 = 数量 × 价格
            - 佣金 = max(卖出金额 × 佣金比例, 5元)
            - 印花税 = 卖出金额 × 印花税比例
            - 净收入 = 卖出金额 - 佣金 - 印花税
        """
        if code not in self.positions:
            log.warning(f"未持有 {code}，无法卖出")
            return False
        
        pos = self.positions[code]
        if amount > pos.total_amount:
            amount = pos.total_amount  # 最多卖出全部持仓
        
        revenue = amount * price
        commission_fee = max(revenue * commission, 5)
        tax_fee = revenue * tax
        net_revenue = revenue - commission_fee - tax_fee
        
        self.cash += net_revenue
        pos.total_amount -= amount
        
        if pos.total_amount == 0:
            del self.positions[code]  # 清空持仓
        
        self._calculate_total_value()
        log.info(f"卖出成功: {code} {amount}股 @ {price:.2f}元")
        return True


# ===================== 数据获取模块 =====================
class DataFetcher:
    """
    数据获取类
    
    使用 efinance 库从东方财富获取股票数据，包括：
    - 沪深300成分股列表
    - 股票历史K线数据
    - 股票当前价格
    - 股票市值信息
    
    备用方案：
    - 如果网络获取失败，使用内置的沪深300成分股列表
    
    主要方法：
        get_hs300_stocks(): 获取沪深300成分股列表
        get_stock_history(): 获取股票历史数据
        get_current_price(): 获取单只股票当前价格
        get_current_prices(): 批量获取多只股票当前价格
        get_market_cap(): 获取股票总市值
    """
    
    # 沪深300成分股代码列表（备用）
    HS300_CODES = [
        '600519', '601318', '600036', '601166', '600887', '601398', '600030', '601288',
        '600276', '600000', '601888', '600016', '601012', '600048', '600900', '601328',
        '601939', '600028', '601988', '600585', '601668', '600346', '601818', '600690',
        '600309', '601888', '600887', '601211', '600196', '601229', '600703', '601601',
        '600104', '601899', '600009', '601688', '600745', '601888', '600893', '601669',
        '600438', '601236', '600809', '601877', '600486', '601633', '600406', '601238',
        '600176', '601319', '600588', '601390', '600837', '601985', '600660', '601766',
        '600848', '601816', '600795', '601857', '600547', '601225', '600460', '601728',
        '600905', '601919', '600570', '601872', '600637', '601336', '600183', '601636',
        '600498', '601998', '600085', '601628', '600519', '601958', '600019', '601186',
        '600690', '601988', '600760', '601788', '600536', '601326', '600635', '601360',
        '600820', '601231', '600129', '601611', '600415', '601881', '600511', '601995',
        '600886', '601868', '600521', '601898', '600535', '601866', '600655', '601901'
    ]
    
    # 沪深300成分股名称字典（备用）
    HS300_NAMES = {
        '600519': '贵州茅台', '601318': '中国平安', '600036': '招商银行', '601166': '兴业银行',
        '600887': '伊利股份', '601398': '工商银行', '600030': '中信证券', '601288': '农业银行',
        '600276': '恒瑞医药', '600000': '浦发银行', '601888': '中国中免', '600016': '民生银行',
        '601012': '隆基绿能', '600048': '保利发展', '600900': '长江电力', '601328': '交通银行',
        '601939': '建设银行', '600028': '中国石化', '601988': '中国银行', '600585': '海螺水泥'
    }
    
    @staticmethod
    def get_hs300_stocks() -> List[Dict]:
        """
        获取沪深300成分股列表
        
        返回：
            List[Dict]: 股票列表，每个元素为 {'code': 代码, 'name': 名称}
        
        获取方式：
            1. 首先尝试从东方财富获取实时行情数据
            2. 如果失败，使用内置的沪深300成分股列表
        """
        try:
            df = ef.stock.get_realtime_quotes()
            if df is not None and not df.empty:
                codes = df['股票代码'].tolist()[:100]
                names = df['股票名称'].tolist()[:100]
                return [{'code': str(c).zfill(6), 'name': str(n)} for c, n in zip(codes, names)]
        except Exception as e:
            log.error(f"获取实时行情失败: {e}")
        
        # 备用方案：使用内置列表
        return [{'code': code, 'name': DataFetcher.HS300_NAMES.get(code, '')} 
                for code in DataFetcher.HS300_CODES[:100]]
    
    @staticmethod
    def get_stock_history(code: str, days: int = 60) -> Optional[pd.DataFrame]:
        """
        获取股票历史K线数据
        
        参数：
            code: 股票代码
            days: 获取天数，默认60天
        
        返回：
            DataFrame: 历史数据，包含日期、开盘价、收盘价、最高价、最低价、成交量等
            None: 获取失败时返回None
        
        数据列说明：
            date: 日期
            open: 开盘价
            close: 收盘价
            high: 最高价
            low: 最低价
            volume: 成交量
            turnover: 成交额
            amplitude: 振幅
            change_pct: 涨跌幅
            change_amt: 涨跌额
            turnover_rate: 换手率
        """
        try:
            df = ef.stock.get_quote_history(code, klt=101, fqt=1)
            if df is not None and not df.empty:
                df = df.tail(days).copy()
                # 将中文列名转换为英文
                df = df.rename(columns={
                    '日期': 'date', '开盘': 'open', '收盘': 'close', '最高': 'high',
                    '最低': 'low', '成交量': 'volume', '成交额': 'turnover',
                    '振幅': 'amplitude', '涨跌幅': 'change_pct', '涨跌额': 'change_amt',
                    '换手率': 'turnover_rate'
                })
                return df
        except Exception as e:
            log.error(f"获取 {code} 历史数据失败: {e}")
        return None
    
    @staticmethod
    def get_current_price(code: str) -> Optional[float]:
        """
        获取单只股票的当前价格
        
        参数：
            code: 股票代码
        
        返回：
            float: 当前价格
            None: 获取失败时返回None
        """
        try:
            df = ef.stock.get_latest_quote(code)
            if df is not None and not df.empty:
                return float(df['最新价'].iloc[0])
        except Exception as e:
            log.error(f"获取 {code} 当前价格失败: {e}")
        return None
    
    @staticmethod
    def get_current_prices(codes: List[str]) -> Dict[str, float]:
        """
        批量获取多只股票的当前价格
        
        参数：
            codes: 股票代码列表
        
        返回：
            Dict[str, float]: 价格字典 {股票代码: 价格}
        
        获取方式：
            1. 首先尝试批量获取
            2. 如果失败，逐个获取（带延迟避免请求过快）
        """
        result = {}
        try:
            df = ef.stock.get_latest_quote(codes)
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    code = str(row['代码']).zfill(6)
                    try:
                        result[code] = float(row['最新价'])
                    except:
                        pass
        except Exception as e:
            log.error(f"批量获取价格失败: {e}")
            # 备用方案：逐个获取
            for code in codes:
                price = DataFetcher.get_current_price(code)
                if price:
                    result[code] = price
                time.sleep(0.1)  # 避免请求过快
        return result
    
    @staticmethod
    def get_market_cap(code: str) -> Optional[float]:
        """
        获取股票总市值
        
        参数：
            code: 股票代码
        
        返回：
            float: 总市值（亿元）
            1000.0: 获取失败时返回默认值（假设为大市值）
        """
        try:
            df = ef.stock.get_latest_quote(code)
            if df is not None and not df.empty:
                if '总市值' in df.columns:
                    return float(df['总市值'].iloc[0])
        except Exception as e:
            pass
        return 1000.0  # 默认返回大市值


# ===================== 技术指标计算 =====================
def calculate_macd(close: pd.Series, fastperiod: int = 12, slowperiod: int = 26, signalperiod: int = 9) -> Tuple[float, float, float]:
    """
    计算MACD指标
    
    MACD (Moving Average Convergence Divergence) 指标说明：
    - DIF (快线): 12日EMA - 26日EMA
    - DEA (慢线): DIF的9日EMA
    - MACD柱: 2 × (DIF - DEA)
    
    参数：
        close: 收盘价序列
        fastperiod: 快线周期，默认12
        slowperiod: 慢线周期，默认26
        signalperiod: 信号线周期，默认9
    
    返回：
        Tuple[float, float, float]: (DIF, DEA, MACD)
    
    使用方法：
        - 金叉（DIF上穿DEA）：买入信号
        - 死叉（DIF下穿DEA）：卖出信号
    """
    ema_fast = close.ewm(span=fastperiod, adjust=False).mean()
    ema_slow = close.ewm(span=slowperiod, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signalperiod, adjust=False).mean()
    macd = 2 * (dif - dea)
    return dif.iloc[-1], dea.iloc[-1], macd.iloc[-1]


def calculate_rsi(close: pd.Series, n: int = 14) -> float:
    """
    计算RSI指标
    
    RSI (Relative Strength Index) 相对强弱指标说明：
    - RSI = 100 - 100 / (1 + RS)
    - RS = N日内上涨幅度平均 / N日内下跌幅度平均
    - RSI > 70: 超买区域，可能回调
    - RSI < 30: 超卖区域，可能反弹
    
    参数：
        close: 收盘价序列
        n: 计算周期，默认14
    
    返回：
        float: RSI值 (0-100)
    
    注意：
        - 当所有周期都上涨时，RSI = 100
        - 当所有周期都下跌时，RSI = 0
    """
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=n).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=n).mean()
    loss = loss.replace(0, np.finfo(float).eps)  # 避免除零错误
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.replace([np.inf, -np.inf], 100)  # 处理无穷大
    return rsi.iloc[-1] if not rsi.empty else 50


# ===================== 策略核心类 =====================
class Strategy:
    """
    策略核心类
    
    实现完整的量化交易策略，包括：
    - 选股：六因子打分系统
    - 择时：沪深300趋势判断
    - 交易：买入/卖出执行
    - 风控：回撤锁定、止盈止损、仓位管理
    
    策略流程：
        1. 检查回撤锁定状态
        2. 选股打分，生成买入信号
        3. 执行交易（止盈止损 + 买入）
        4. 风控检查（空仓/加仓/减仓）
        5. 输出账户状态
    
    属性：
        config: 配置对象
        portfolio: 投资组合对象
        data_fetcher: 数据获取对象
        current_date: 当前日期
    """
    def __init__(self, starting_cash: float = 100000.0):
        """
        初始化策略
        
        参数：
            starting_cash: 初始资金，默认10万元
        """
        self.config = Config()
        self.config.starting_cash = starting_cash
        self.portfolio = Portfolio(starting_cash)
        self.data_fetcher = DataFetcher()
        self.current_date = datetime.now()
    
    def calculate_drawdown(self) -> float:
        """
        计算当前回撤
        
        返回：
            float: 回撤比例
        """
        return self.portfolio.drawdown
    
    def check_trend_recovery(self) -> Tuple[bool, str]:
        """
        检查趋势是否恢复（解锁条件判断）
        
        解锁条件（需同时满足）：
            1. 沪深300站上20日均线
            2. MACD金叉（DIF > DEA）
            3. 账户回撤 < 8%
        
        返回：
            Tuple[bool, str]: (是否解锁, 原因说明)
        """
        try:
            df = self.data_fetcher.get_stock_history('000300', 60)
            if df is None or len(df) < 60:
                return False, "沪深300数据不足60天"
            
            close = df['close']
            b_current = close.iloc[-1]
            b_ma20 = close.rolling(20).mean().iloc[-1]
            b_macd = calculate_macd(close)
            drawdown = self.calculate_drawdown()
            
            # 三个解锁条件
            cond1 = b_current > b_ma20  # 站上20日线
            cond2 = b_macd[0] > b_macd[1]  # MACD金叉
            cond3 = drawdown < 0.08  # 回撤小于8%
            
            if cond1 and cond2 and cond3:
                return True, f"解锁成功→沪深300站上20日线+MACD金叉+回撤{drawdown*100:.1f}%<8%"
            else:
                fail_reason = []
                if not cond1:
                    fail_reason.append(f"沪深300未站上20日线({b_current:.2f}<{b_ma20:.2f})")
                if not cond2:
                    fail_reason.append(f"MACD未金叉")
                if not cond3:
                    fail_reason.append(f"回撤{drawdown*100:.1f}%≥8%")
                return False, "解锁失败→" + "｜".join(fail_reason)
        except Exception as e:
            return False, f"检查趋势失败: {e}"
    
    def select_stocks(self) -> List[str]:
        """
        选股函数
        
        六因子打分系统：
            1. 市值因子 (10分): 市值 > 100亿
            2. 5日动量 (25分): 5日涨幅 > 5%
            3. 20日动量 (20分): 20日涨幅 > 10%
            4. 趋势强度 (25分): (MA5-MA20)/MA20 > 1%
            5. 量比 (15分): 当日成交量/20日均量 > 1.5
            6. 波动率 (5分): 20日波动率 < 8%
        
        选股流程：
            1. 检查回撤锁定状态
            2. 获取沪深300成分股
            3. 计算各因子得分
            4. 按得分排序，取前N只
            5. 主动换股：卖出跌出高分区的持仓
        
        返回：
            List[str]: 买入信号股票代码列表
        """
        # 步骤1：检查回撤锁定
        if self.config.drawdown_lock:
            is_unlock, unlock_reason = self.check_trend_recovery()
            log.info(f"【回撤锁定检查】{unlock_reason}")
            if is_unlock:
                self.config.drawdown_lock = False
            else:
                self.config.buy_signals = []
                return []
        
        # 步骤2：获取沪深300成分股
        hs300 = self.data_fetcher.get_hs300_stocks()
        if not hs300:
            log.info("【选股失败】沪深300成分股获取失败")
            return []
        
        stock_data = []
        select_stocks = hs300[:self.config.stock_pool_limit]
        
        # 步骤3：计算各因子得分
        for stock_info in select_stocks:
            code = stock_info['code']
            name = stock_info.get('name', '')
            
            # 获取市值
            market_cap = self.data_fetcher.get_market_cap(code)
            if market_cap is None:
                continue
            
            # 获取历史数据
            hist = self.data_fetcher.get_stock_history(code, 60)
            if hist is None or len(hist) < 60:
                continue
            
            close = hist['close']
            volume = hist['volume']
            
            # 计算技术指标
            ma5 = close.rolling(5).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            momentum_5 = close.iloc[-1] / close.iloc[-6] - 1  # 5日动量
            momentum_20 = close.iloc[-1] / close.iloc[-21] - 1  # 20日动量
            trend_strength = (ma5 - ma20) / ma20  # 趋势强度
            volatility = close.rolling(20).std().iloc[-1] / close.iloc[-1]  # 波动率
            avg20_vol = volume.rolling(20).mean().iloc[-1]
            volume_ratio = volume.iloc[-1] / avg20_vol if avg20_vol != 0 else 0  # 量比
            
            # 六因子打分
            score = 0
            if market_cap > 100: score += 10  # 大市值加分
            if momentum_5 > 0.05: score += 25  # 短期动量强
            if momentum_20 > 0.10: score += 20  # 中期动量强
            if trend_strength > 0.01: score += 25  # 趋势向上
            if volume_ratio > 1.5: score += 15  # 放量
            if volatility < 0.08: score += 5  # 波动小
            
            stock_data.append({
                'code': code,
                'name': name,
                'score': score,
                'market_cap': market_cap
            })
        
        # 步骤4：按得分排序
        if stock_data:
            stock_data.sort(key=lambda x: x['score'], reverse=True)
            signals = [s['code'] for s in stock_data[:self.config.max_positions * 2]]
            
            # 步骤5：主动换股
            for pos_code in list(self.portfolio.positions.keys()):
                if pos_code not in signals:
                    price = self.data_fetcher.get_current_price(pos_code)
                    if price:
                        pos = self.portfolio.positions[pos_code]
                        self.portfolio.sell(pos_code, pos.total_amount, price)
                        log.info(f"【主动换股】卖出{pos_code}，打分跌出高分区间")
            
            self.config.buy_signals = signals[:self.config.max_positions]
        else:
            # 兜底：无信号时取沪深300前N只
            self.config.buy_signals = [s['code'] for s in hs300[:self.config.max_positions]]
            log.info(f"【信号兜底】取沪深300前{self.config.max_positions}只")
        
        log.info(f"【选股完成】买入信号：{self.config.buy_signals}")
        return self.config.buy_signals
    
    def execute_trade(self):
        """
        执行交易
        
        交易流程：
            1. 检查回撤锁定状态
            2. 执行止盈/止损
            3. 判断牛市/熊市
            4. 计算买入金额
            5. 执行买入
        
        买入条件：
            - 持仓数量 < 最大持仓数
            - 可用现金 >= 500元
            - 有买入候选股票
        
        牛市加仓：
            - 沪深300 > 20日线 × 1.03 时，买入金额 × 1.2
        """
        # 步骤1：检查回撤锁定
        if self.config.drawdown_lock:
            log.info("【交易拦截】处于回撤锁定状态")
            return
        
        current_pos_count = len(self.portfolio.positions)
        available_cash = self.portfolio.available_cash
        buy_candidates = [s for s in self.config.buy_signals 
                         if s not in self.portfolio.positions]
        
        # 步骤2：执行止盈/止损
        for code in list(self.portfolio.positions.keys()):
            pos = self.portfolio.positions[code]
            profit_ratio = pos.profit_ratio
            
            if profit_ratio >= self.config.take_profit_ratio or profit_ratio <= -self.config.stop_loss_ratio:
                price = self.data_fetcher.get_current_price(code)
                if price:
                    self.portfolio.sell(code, pos.total_amount, price)
                    log.info(f"【止盈/止损】卖出{code}，收益率：{profit_ratio:.2%}")
                    current_pos_count -= 1
                    buy_candidates.append(code)
        
        # 步骤3：检查买入条件
        if current_pos_count >= self.config.max_positions:
            log.info(f"【交易拦截】持仓已满")
            return
        
        if available_cash < 500:
            log.info(f"【交易拦截】现金不足")
            return
        
        if not buy_candidates:
            log.info("【交易拦截】无买入候选")
            return
        
        # 步骤4：判断牛市/熊市
        try:
            df = self.data_fetcher.get_stock_history('000300', 60)
            if df is not None:
                close = df['close']
                b_ma20 = close.rolling(20).mean().iloc[-1]
                b_current = close.iloc[-1]
                is_bull = b_current > b_ma20 * self.config.bull_market_threshold
            else:
                is_bull = False
        except:
            is_bull = False
        
        # 步骤5：执行买入
        cash_per_stock = available_cash / len(buy_candidates)
        
        for code in buy_candidates:
            if current_pos_count >= self.config.max_positions:
                break
            
            # 牛市加仓
            buy_cash = cash_per_stock * self.config.bull_add_ratio if is_bull else cash_per_stock
            price = self.data_fetcher.get_current_price(code)
            
            if price is None:
                continue
            
            # 检查最小买入金额（1手=100股）
            min_cash = price * 100
            if buy_cash < min_cash:
                log.info(f"【买入拦截】{code}资金不足")
                continue
            
            # 计算买入数量（必须是100的整数倍）
            amount = int(buy_cash / price / 100) * 100
            if amount <= 0:
                continue
            
            # 获取股票名称
            name = ''
            for s in self.data_fetcher.get_hs300_stocks():
                if s['code'] == code:
                    name = s.get('name', '')
                    break
            
            if self.portfolio.buy(code, name, amount, price):
                current_pos_count += 1
    
    def check_risk(self):
        """
        风控检查
        
        风控措施：
            1. 强空仓+锁定：回撤 >= 10%，清仓并锁定
            2. 强空仓-不锁定：沪深300破60日线 + MACD死叉，清仓
            3. 强势加仓：强势牛市 + 仓位<95%，加仓至95%
            4. 熊市减仓：熊市 + 仓位>60%，减仓至60%
        
        强势牛市定义：
            - 沪深300 > 20日线 × 1.04
            - MACD金叉
            - RSI < 80
            - 量比 > 1.2
        
        熊市定义：
            - 沪深300 < 20日线
            - MACD死叉
        """
        total_value = self.portfolio.total_value
        if total_value <= 0:
            return
        
        pos_ratio = sum(p.market_value for p in self.portfolio.positions.values()) / total_value
        drawdown = self.calculate_drawdown()
        
        try:
            df = self.data_fetcher.get_stock_history('000300', 60)
            if df is None:
                return
            
            close = df['close']
            volume = df['volume']
            b_current = close.iloc[-1]
            b_ma20 = close.rolling(20).mean().iloc[-1]
            b_ma60 = close.rolling(60).mean().iloc[-1]
            b_macd = calculate_macd(close)
            b_rsi = calculate_rsi(close)
            b_vol_ratio = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]
            
            # 判断市场状态
            is_strong_bull = (b_current > b_ma20 * self.config.strong_bull_threshold and 
                            b_macd[0] > b_macd[1] and b_rsi < 80 and b_vol_ratio > 1.2)
            is_bear = b_current < b_ma20 and b_macd[0] < b_macd[1]
            
            # 风控措施1：强空仓+锁定
            if drawdown >= self.config.empty_drawdown:
                prices = self.data_fetcher.get_current_prices(list(self.portfolio.positions.keys()))
                for code in list(self.portfolio.positions.keys()):
                    if code in prices:
                        pos = self.portfolio.positions[code]
                        self.portfolio.sell(code, pos.total_amount, prices[code])
                self.config.drawdown_lock = True
                log.info(f"【强空仓+锁定】回撤{drawdown*100:.1f}%≥10%")
                return
            
            # 风控措施2：强空仓-不锁定
            elif b_current < b_ma60 and b_macd[0] < b_macd[1]:
                prices = self.data_fetcher.get_current_prices(list(self.portfolio.positions.keys()))
                for code in list(self.portfolio.positions.keys()):
                    if code in prices:
                        pos = self.portfolio.positions[code]
                        self.portfolio.sell(code, pos.total_amount, prices[code])
                log.info("【强空仓-不锁定】沪深300破60日线+MACD死叉")
                return
            
            # 风控措施3：强势加仓
            if is_strong_bull and pos_ratio < 0.95 and self.config.buy_signals:
                add_amount = total_value * 0.95 - sum(p.market_value for p in self.portfolio.positions.values())
                if add_amount > 0 and self.config.buy_signals:
                    top1 = self.config.buy_signals[0]
                    if top1 in self.portfolio.positions:
                        price = self.data_fetcher.get_current_price(top1)
                        if price:
                            amount = int(add_amount * 0.8 / price / 100) * 100
                            if amount > 0:
                                self.portfolio.buy(top1, '', amount, price)
                                log.info(f"【强势加仓】{top1}")
            
            # 风控措施4：熊市减仓
            if is_bear and pos_ratio > 0.6:
                reduce_amount = sum(p.market_value for p in self.portfolio.positions.values()) - total_value * 0.6
                if reduce_amount > 0:
                    # 优先减仓得分低的股票
                    low_score = [s for s in self.portfolio.positions.keys() 
                               if s not in self.config.buy_signals]
                    if not low_score:
                        low_score = list(self.portfolio.positions.keys())[-1:]
                    
                    for code in low_score:
                        if code in self.portfolio.positions:
                            pos = self.portfolio.positions[code]
                            price = self.data_fetcher.get_current_price(code)
                            if price:
                                reduce_shares = int(reduce_amount / price / 100) * 100
                                if reduce_shares > 0:
                                    self.portfolio.sell(code, min(reduce_shares, pos.total_amount), price)
                                    log.info(f"【熊市减仓】{code}")
        except Exception as e:
            log.error(f"风控检查失败: {e}")
    
    def print_status(self):
        """
        打印账户状态
        
        输出信息：
            - 当前时间
            - 初始资金
            - 当前市值
            - 可用现金
            - 总收益
            - 收益率
            - 最大回撤
            - 回撤锁定状态
            - 买入信号
            - 持仓明细
        """
        log.info("=" * 60)
        log.info(f"【账户汇总】{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log.info(f"初始资金: {self.portfolio.starting_cash:.2f}元")
        log.info(f"当前市值: {self.portfolio.total_value:.2f}元")
        log.info(f"可用现金: {self.portfolio.available_cash:.2f}元")
        log.info(f"总收益: {self.portfolio.total_value - self.portfolio.starting_cash:.2f}元")
        log.info(f"收益率: {(self.portfolio.total_value / self.portfolio.starting_cash - 1) * 100:.2f}%")
        log.info(f"最大回撤: {self.portfolio.drawdown * 100:.2f}%")
        log.info(f"回撤锁定: {self.config.drawdown_lock}")
        log.info(f"买入信号: {self.config.buy_signals}")
        
        if self.portfolio.positions:
            log.info(f"当前持仓: {len(self.portfolio.positions)}只")
            for code, pos in self.portfolio.positions.items():
                log.info(f"  {code} ({pos.name}) | {pos.total_amount}股 | "
                        f"成本{pos.avg_cost:.2f} | 现价{pos.current_price:.2f} | "
                        f"收益{pos.profit_ratio * 100:.2f}%")
        else:
            log.info("当前持仓: 空仓")
        log.info("=" * 60)
    
    def run_once(self):
        """
        执行一次完整的策略流程
        
        流程：
            1. 选股
            2. 交易
            3. 风控
            4. 输出状态
        
        返回：
            float: 当前账户总价值
        """
        log.info("\n" + "=" * 60)
        log.info("开始执行策略...")
        
        log.info("\n【步骤1】选股")
        self.select_stocks()
        
        log.info("\n【步骤2】交易")
        self.execute_trade()
        
        log.info("\n【步骤3】风控")
        self.check_risk()
        
        log.info("\n【步骤4】状态")
        self.print_status()
        
        return self.portfolio.total_value


# ===================== 主程序 =====================
def main():
    """
    主函数
    
    初始化策略并执行一次完整的策略流程
    """
    log.info("=" * 60)
    log.info("大市值低回撤策略 - 本地版本")
    log.info("=" * 60)
    
    # 创建策略实例，初始资金10万元
    strategy = Strategy(starting_cash=100000.0)
    
    log.info("\n初始化完成，开始运行策略...")
    strategy.run_once()
    
    log.info("\n策略执行完成！")


if __name__ == "__main__":
    main()
