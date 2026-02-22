# 克隆自聚宽文章：https://www.joinquant.com/post/67113
# 标题：【策略升级】优质小市值周轮动策略-V1.3
# 作者：屌丝逆袭量化

# 标题：优质小市值周轮动策略（增强版）- 增加ATR止损和整体风控
# 作者：屌丝逆袭量化
# 日期：2026年2月10日
# # 为了更有利于实盘，新增如下功能（可开关和设置）：
# 1、成交量过滤：增加60日平均成交额大于0.1亿的条件过滤，保障成交率
# 2、价格过滤：增加收盘价大于2元的过滤，降低滑点和避免国九条退市（可配置）
# 3、排序可选：可改为按总市值升序排列
# 4、交易时间改进：将交易时间改到10:30，避免滑点过大或无法买卖
# 5、ATR止损：每天11:00检查个股是否超过2倍（可设置）ATR，如果超过，则卖出。
# 6、整体止损：当从近期高点回撤超过指定阈值时，进入冷静期（可设置），期间持有防御资产（可设置）

# 导入函数库
from jqdata import *
from jqfactor import get_factor_values
import numpy as np
import pandas as pd
import datetime

# 初始化函数 
def initialize(context):
    # 设定基准
    set_benchmark('000300.XSHG')
    #set_benchmark('518880.XSHG')
    # 用真实价格交易
    set_option('use_real_price', True)
    # 打开防未来函数
    set_option("avoid_future_data", True)
    # 将滑点设置
    set_slippage(FixedSlippage(0.002))
    # 设置交易成本
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5), type='fund')
    # 过滤order中低于error级别的日志
    log.set_level('order', 'error')
    
    # 初始化全局变量
    g.stock_num = 10
    g.limit_up_list = []
    g.hold_list = []
    
    # 价格过滤配置
    g.enable_price_filter = False  # 是否启用价格过滤，True为启用，False为关闭
    g.price_threshold = 2.0  # 价格过滤阈值，默认为2元
    
    # 成交量过滤
    g.enable_volume_filter = False   # 是否启用成交量过滤，True为启用，False为关闭
    g.min_avg_amount = 10e7  # 指定日期平均成交量最小值
    g.lookback_days = 60    # 回看成交量的天数
    
    # ATR止损配置
    g.enable_atr_stop_loss = False  # 是否启用ATR止损，True为启用，False为关闭
    g.atr_multiple = 2.0  # ATR倍数阈值，默认2倍
    g.atr_period = 14  # ATR计算周期，默认14天
    g.atr_stop_loss_records = {}  # 记录每只股票的止损价格
    
    # 整体风控配置（基于回撤）
    g.enable_overall_risk_control = True  # 是否启用整体风控
    g.max_drawdown_threshold = -0.1  # 最大回撤阈值，默认为-10%
    g.defense_duration = 20  # 防御期限，默认为20个交易日
    g.defense_start_date = None  # 防御开始日期
    g.in_defense_mode = False  # 是否处于防御模式
    
    # 资产历史记录（用于计算回撤）
    g.portfolio_history = []  # 记录每日总资产
    g.max_lookback_days = 60  # 回看周期，最大60天
    
    # 防御资产配置
    g.defense_assets = {
        '518880.XSHG': 0.5,  # 黄金ETF
        '511010.XSHG': 0.5   # 国债ETF
    }
    
    # 设置交易时间
    run_daily(prepare_stock_list, time='9:05', reference_security='000300.XSHG')
    run_weekly(weekly_adjustment, weekday=1, time='10:30', reference_security='000300.XSHG')
    run_daily(check_limit_up, time='14:00', reference_security='000300.XSHG')
    run_daily(print_position_info, time='15:10', reference_security='000300.XSHG')
    run_daily(check_risk_control, time='11:00', reference_security='000300.XSHG')
    run_daily(record_portfolio_value, time='15:00', reference_security='000300.XSHG')  # 收盘后记录资产

# 记录每日资产价值
def record_portfolio_value(context):
    """记录每日收盘后的资产价值"""
    if g.in_defense_mode:
        return
    
    current_date = context.current_dt
    total_value = context.portfolio.total_value
    
    # 添加记录：日期和总资产
    g.portfolio_history.append({
        'date': current_date,
        'total_value': total_value
    })
    
    # 只保留最近max_lookback_days天的记录
    if len(g.portfolio_history) > g.max_lookback_days:
        g.portfolio_history.pop(0)
    
    log.info("记录资产：日期{}，总资产{:.2f}".format(current_date.strftime('%Y-%m-%d'), total_value))

# 选股模块
def get_factor_filter_list(context, stock_list, jqfactor, sort, p1, p2):
    yesterday = context.previous_date
    score_list = get_factor_values(stock_list, jqfactor, end_date=yesterday, count=1)[jqfactor].iloc[0].tolist()
    df = pd.DataFrame(columns=['code', 'score'])
    df['code'] = stock_list
    df['score'] = score_list
    df = df.dropna()
    df.sort_values(by='score', ascending=sort, inplace=True)
    filter_list = list(df.code)[int(p1*len(df)):int(p2*len(df))]
    return filter_list

def get_stock_list(context):
    yesterday = context.previous_date
    initial_list = get_all_securities().index.tolist()
    initial_list = filter_new_stock(context, initial_list)
    initial_list = filter_kcbj_stock(initial_list)
    initial_list = filter_st_stock(initial_list)
    
    if g.enable_price_filter:
        initial_list = filter_price_stock(context, initial_list, g.price_threshold)
    
    if g.enable_volume_filter:
        initial_list = filter_volume_stock(context, initial_list, min_avg_amount=g.min_avg_amount, lookback_days=g.lookback_days)
    
    price_list1 = get_factor_filter_list(context, initial_list, 'price_no_fq', True, 0, 0.1)
    
    df = get_price(initial_list, start_date=yesterday, end_date=yesterday, fields=['close'], fq='pre', panel=False)
    df = df.sort_values(by='close', ascending=True)
    price_list2 = list(df.code)[int(0*len(df)):int(0.1*len(df))]
    
    q = query(valuation.code, valuation.market_cap, valuation.circulating_market_cap, indicator.roe, indicator.gross_profit_margin,
              indicator.inc_total_revenue_year_on_year, indicator.inc_net_profit_annual).filter(
        valuation.pb_ratio > 0,
        valuation.code.in_(price_list1)).order_by(valuation.circulating_market_cap.asc())
    
    df = get_fundamentals(q, date=yesterday)
    df = df[df['inc_total_revenue_year_on_year'] > 0]
    #df = df[df['gross_profit_margin']>0]
    final_list = list(df.code)[:15]
    return final_list

def prepare_stock_list(context):
    if g.in_defense_mode:
        log.info("当前处于防御模式，跳过股票池准备")
        return
    
    g.hold_list = []
    for position in list(context.portfolio.positions.values()):
        stock = position.security
        g.hold_list.append(stock)
    
    if g.hold_list != []:
        df = get_price(g.hold_list, end_date=context.previous_date, frequency='daily', fields=['close', 'high_limit'], count=1, panel=False, fill_paused=False)
        df = df[df['close'] == df['high_limit']]
        g.high_limit_list = list(df.code)
    else:
        g.high_limit_list = []

def weekly_adjustment(context):
    if g.in_defense_mode:
        log.info("当前处于防御模式，跳过正常的股票轮动调整")
        check_defense_period_end(context)
        return
    
    target_list = get_stock_list(context)
    target_list = filter_paused_stock(target_list)
    target_list = filter_limitup_stock(context, target_list)
    target_list = filter_limitdown_stock(context, target_list)
    
    target_list = target_list[:min(g.stock_num, len(target_list))]
    
    for stock in g.hold_list:
        if (stock not in target_list) and (stock not in g.high_limit_list):
            log.info("卖出[%s]" % (stock))
            position = context.portfolio.positions[stock]
            close_position(position)
            if stock in g.atr_stop_loss_records:
                del g.atr_stop_loss_records[stock]
        else:
            log.info("已持有[%s]" % (stock))
    
    position_count = len(context.portfolio.positions)
    target_num = len(target_list)
    if target_num > position_count:
        value = context.portfolio.cash / (target_num - position_count)
        for stock in target_list:
            if context.portfolio.positions[stock].total_amount == 0:
                if open_position(stock, value):
                    update_atr_stop_loss_price(context, stock)
                    if len(context.portfolio.positions) == target_num:
                        break

def check_limit_up(context):
    if g.in_defense_mode:
        return
        
    now_time = context.current_dt
    if g.high_limit_list != []:
        for stock in g.high_limit_list:
            current_data = get_price(stock, end_date=now_time, frequency='1m', fields=['close', 'high_limit'], skip_paused=False, fq='pre', count=1, panel=False, fill_paused=True)
            if current_data.iloc[0, 0] < current_data.iloc[0, 1]:
                log.info("[%s]涨停打开，卖出" % (stock))
                position = context.portfolio.positions[stock]
                close_position(position)
                if stock in g.atr_stop_loss_records:
                    del g.atr_stop_loss_records[stock]
            else:
                log.info("[%s]涨停，继续持有" % (stock))

# 风控检查函数
def check_risk_control(context):
    """每天11:00执行风险控制检查"""
    # 检查整体回撤
    check_overall_drawdown(context)
    
    # 如果不在防御模式，执行ATR止损检查
    if not g.in_defense_mode and g.enable_atr_stop_loss:
        check_atr_stop_loss(context)
    
    # 如果处于防御模式，检查防御期限是否结束
    if g.in_defense_mode:
        check_defense_period_end(context)

def check_overall_drawdown(context):
    """检查整体回撤是否超过阈值"""
    if not g.enable_overall_risk_control:
        return
    
    if g.in_defense_mode:
        return
    
    # 获取当前总资产
    current_value = context.portfolio.total_value
    
    # 如果没有历史数据，记录当前值并返回
    if not g.portfolio_history:
        log.info("暂无历史资产数据，无法计算回撤")
        return
    
    # 计算近期最高点（回看防御天数周期）
    lookback_days = min(len(g.portfolio_history), g.defense_duration)
    recent_history = g.portfolio_history[-lookback_days:]
    
    if not recent_history:
        return
    
    # 计算近期最高总资产
    max_value = max([record['total_value'] for record in recent_history])
    
    # 计算回撤率
    if max_value > 0:
        drawdown = (current_value - max_value) / max_value
    else:
        drawdown = 0
    
    log.info("整体回撤检查：当前资产{:.2f}，近期{:.0f}天最高资产{:.2f}，回撤率{:.2f}%，阈值{:.2f}%".format(
        current_value, lookback_days, max_value, drawdown*100, g.max_drawdown_threshold*100))
    
    # 如果回撤超过阈值，进入防御模式
    if drawdown < g.max_drawdown_threshold:
        log.warn("整体回撤超过阈值({:.2f}%)，触发防御机制，进入防御模式".format(g.max_drawdown_threshold*100))
        enter_defense_mode(context)

def enter_defense_mode(context):
    """进入防御模式：卖出所有股票，买入防御资产"""
    g.in_defense_mode = True
    g.defense_start_date = context.current_dt.date()
    
    log.info("开始进入防御模式，防御开始日期：%s，预计结束日期：%s" % 
             (g.defense_start_date, g.defense_start_date + datetime.timedelta(days=g.defense_duration)))
    
    # 卖出所有股票持仓
    holdings = list(context.portfolio.positions.keys())
    if holdings:
        log.info("开始清空股票持仓，共%d只股票" % len(holdings))
        for stock in holdings:
            if stock in g.defense_assets:
                continue
                
            position = context.portfolio.positions[stock]
            if close_position(position):
                log.info("成功卖出防御股票[%s]" % stock)
                if stock in g.atr_stop_loss_records:
                    del g.atr_stop_loss_records[stock]
            else:
                log.warn("卖出防御股票[%s]失败" % stock)
    
    # 买入防御资产
    if context.portfolio.available_cash > 100:
        allocate_defense_assets(context)
    else:
        log.info("现金不足，无法买入防御资产")

def allocate_defense_assets(context):
    """分配资金到防御资产"""
    total_cash = context.portfolio.available_cash
    log.info("开始分配防御资产，可用现金：%.2f" % total_cash)
    
    available_defense_assets = {}
    for asset, weight in g.defense_assets.items():
        try:
            current_data = get_current_data()[asset]
            if not current_data.paused:
                available_defense_assets[asset] = weight
            else:
                log.warn("防御资产[%s]停牌，跳过" % asset)
        except:
            log.warn("防御资产[%s]无法获取数据，跳过" % asset)
    
    if not available_defense_assets:
        log.error("没有可用的防御资产，防御模式将只持有现金")
        return
    
    # 修复：将字典值转换为列表再求和
    total_weight = sum(list(available_defense_assets.values()))
    
    for asset, weight in available_defense_assets.items():
        normalized_weight = weight / total_weight
        allocate_amount = total_cash * normalized_weight
        
        if allocate_amount > 100:
            log.info("买入防御资产[%s]，金额：%.2f，权重：%.2f" % (asset, allocate_amount, normalized_weight))
            
            current_price = get_current_data()[asset].last_price
            if current_price > 0:
                shares = int(allocate_amount / current_price / 100) * 100
                if shares > 0:
                    order = order_target(asset, shares)
                    if order and order.filled > 0:
                        log.info("成功买入防御资产[%s]，数量：%d" % (asset, shares))
                    else:
                        log.warn("买入防御资产[%s]失败" % asset)
        else:
            log.info("防御资产[%s]分配金额不足，跳过" % asset)

def check_defense_period_end(context):
    """检查防御期限是否结束"""
    if not g.in_defense_mode or not g.defense_start_date:
        return
    
    current_date = context.current_dt.date()
    days_in_defense = (current_date - g.defense_start_date).days
    
    log.info("防御模式已持续%d天，总防御期限%d天" % (days_in_defense, g.defense_duration))
    
    if days_in_defense >= g.defense_duration:
        log.info("防御期限结束，退出防御模式")
        exit_defense_mode(context)

def exit_defense_mode(context):
    """退出防御模式：卖出防御资产，恢复正常交易"""
    g.in_defense_mode = False
    g.defense_start_date = None
    
    log.info("开始退出防御模式，恢复正常的股票轮动策略")
    
    holdings = list(context.portfolio.positions.keys())
    if holdings:
        log.info("开始清空防御资产，共%d只" % len(holdings))
        for asset in holdings:
            position = context.portfolio.positions[asset]
            if close_position(position):
                log.info("成功卖出防御资产[%s]" % asset)
            else:
                log.warn("卖出防御资产[%s]失败" % asset)
    
    g.hold_list = []
    g.atr_stop_loss_records = {}
    g.high_limit_list = []
    # 清空历史记录，重新开始
    g.portfolio_history = []
    log.info("防御模式退出完成，等待下一次正常调仓")

# ATR止损函数
def check_atr_stop_loss(context):
    """每天11:00检查ATR止损"""
    if not g.enable_atr_stop_loss:
        return
        
    holdings = list(context.portfolio.positions.keys())
    if not holdings:
        return
    
    log.info("开始执行ATR止损检查，当前持仓数量：%d" % len(holdings))
    
    for stock in holdings:
        if get_current_data()[stock].paused:
            continue
            
        current_price = get_current_data()[stock].last_price
        
        if stock not in g.atr_stop_loss_records:
            update_atr_stop_loss_price(context, stock)
        
        if stock in g.atr_stop_loss_records:
            stop_price = g.atr_stop_loss_records[stock]
            
            if current_price <= stop_price:
                log.info("股票[%s]触发ATR止损，当前价格%.2f，止损价格%.2f" % 
                        (stock, current_price, stop_price))
                
                position = context.portfolio.positions[stock]
                if close_position(position):
                    log.info("股票[%s]ATR止损卖出成功" % stock)
                    del g.atr_stop_loss_records[stock]
                else:
                    log.warn("股票[%s]ATR止损卖出失败" % stock)
            else:
                new_stop_price = update_trailing_stop_loss(context, stock, current_price)
                if new_stop_price > stop_price:
                    g.atr_stop_loss_records[stock] = new_stop_price
                    log.info("股票[%s]更新跟踪止损价：%.2f -> %.2f" % 
                            (stock, stop_price, new_stop_price))

def update_atr_stop_loss_price(context, stock):
    """计算股票的ATR止损价格"""
    try:
        end_date = context.previous_date
        start_date = end_date - datetime.timedelta(days=g.atr_period + 10)
        
        prices = get_price(stock, start_date=start_date, end_date=end_date, 
                          frequency='daily', fields=['high', 'low', 'close'], 
                          skip_paused=True, fq='pre', panel=False)
        
        if len(prices) < g.atr_period:
            log.warn("股票[%s]历史数据不足，无法计算ATR" % stock)
            return
        
        prices['prev_close'] = prices['close'].shift(1)
        prices['high_low'] = prices['high'] - prices['low']
        prices['high_prev_close'] = abs(prices['high'] - prices['prev_close'])
        prices['low_prev_close'] = abs(prices['low'] - prices['prev_close'])
        
        prices['tr'] = prices[['high_low', 'high_prev_close', 'low_prev_close']].max(axis=1)
        
        atr = prices['tr'].tail(g.atr_period).mean()
        
        if stock in context.portfolio.positions:
            cost_price = context.portfolio.positions[stock].avg_cost
        else:
            cost_price = prices['close'].iloc[-1]
        
        stop_loss_price = cost_price - (atr * g.atr_multiple)
        
        g.atr_stop_loss_records[stock] = stop_loss_price
        
        log.info("股票[%s]ATR止损价计算完成：成本价%.2f，ATR=%.4f，止损价=%.2f" % 
                (stock, cost_price, atr, stop_loss_price))
        
        return stop_loss_price
        
    except Exception as e:
        log.error("计算股票[%s]ATR止损价时出错：%s" % (stock, str(e)))
        return None

def update_trailing_stop_loss(context, stock, current_price):
    """更新跟踪止损价格"""
    if stock not in g.atr_stop_loss_records:
        return None
    
    current_stop = g.atr_stop_loss_records[stock]
    
    if stock in context.portfolio.positions:
        cost_price = context.portfolio.positions[stock].avg_cost
    else:
        cost_price = current_price
    
    try:
        end_date = context.previous_date
        start_date = end_date - datetime.timedelta(days=g.atr_period + 10)
        
        prices = get_price(stock, start_date=start_date, end_date=end_date, 
                          frequency='daily', fields=['high', 'low', 'close'], 
                          skip_paused=True, fq='pre', panel=False)
        
        if len(prices) >= g.atr_period:
            prices['prev_close'] = prices['close'].shift(1)
            prices['high_low'] = prices['high'] - prices['low']
            prices['high_prev_close'] = abs(prices['high'] - prices['prev_close'])
            prices['low_prev_close'] = abs(prices['low'] - prices['prev_close'])
            prices['tr'] = prices[['high_low', 'high_prev_close', 'low_prev_close']].max(axis=1)
            atr = prices['tr'].tail(g.atr_period).mean()
            
            new_stop = current_price - (atr * g.atr_multiple)
            
            if new_stop > current_stop:
                return new_stop
    
    except Exception as e:
        log.error("更新跟踪止损时出错：%s" % str(e))
    
    return current_stop

# 过滤函数
def filter_paused_stock(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list if not current_data[stock].paused]

def filter_st_stock(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list
            if not current_data[stock].is_st
            and 'ST' not in current_data[stock].name
            and '*' not in current_data[stock].name
            and '退' not in current_data[stock].name]

def filter_limitup_stock(context, stock_list):
    last_prices = history(1, unit='1m', field='close', security_list=stock_list)
    current_data = get_current_data()
    return [stock for stock in stock_list if stock in context.portfolio.positions.keys()
            or last_prices[stock][-1] < current_data[stock].high_limit]

def filter_limitdown_stock(context, stock_list):
    last_prices = history(1, unit='1m', field='close', security_list=stock_list)
    current_data = get_current_data()
    return [stock for stock in stock_list if stock in context.portfolio.positions.keys()
            or last_prices[stock][-1] > current_data[stock].low_limit]

def filter_kcbj_stock(stock_list):
    filtered_list = []
    for stock in stock_list:
        if stock[0] != '4' and stock[0] != '8' and stock[:2] != '68':
            filtered_list.append(stock)
    return filtered_list

def filter_new_stock(context, stock_list):
    yesterday = context.previous_date
    filtered_list = []
    for stock in stock_list:
        start_date = get_security_info(stock).start_date
        if start_date and (yesterday - start_date).days >= 250:
            filtered_list.append(stock)
    return filtered_list

def filter_price_stock(context, stock_list, price_threshold=2.0):
    if not stock_list:
        return stock_list
    
    yesterday = context.previous_date
    df = get_price(stock_list, start_date=yesterday, end_date=yesterday, 
                   fields=['close'], fq='pre', panel=False, skip_paused=False, fill_paused=False)
    
    filtered_stocks = df[df['close'] >= price_threshold]['code'].tolist()
    
    log.info("价格过滤：从%d只股票中过滤出%d只价格>=%.2f元的股票" % 
             (len(stock_list), len(filtered_stocks), price_threshold))
    
    return filtered_stocks

def filter_volume_stock(context, stock_list, min_avg_amount=10000000, lookback_days=60):
    if not stock_list:
        return stock_list
    
    yesterday = context.previous_date
    start_date = yesterday - datetime.timedelta(days=lookback_days+10)
    
    filtered_stocks = []
    
    batch_size = 100
    for i in range(0, len(stock_list), batch_size):
        batch = stock_list[i:i+batch_size]
        
        df = get_price(batch, start_date=start_date, end_date=yesterday, 
                      fields=['money'], fq='pre', panel=False, skip_paused=True)
        
        if not df.empty:
            avg_amounts = df.groupby('code')['money'].mean()
            batch_filtered = avg_amounts[avg_amounts >= min_avg_amount].index.tolist()
            filtered_stocks.extend(batch_filtered)
    
    log.info("成交量过滤：从%d只股票中过滤出%d只60日平均成交额>=%.2f万的股票" % 
             (len(stock_list), len(filtered_stocks), min_avg_amount/10000))
    
    return filtered_stocks

# 交易模块
def order_target_value_(security, value):
    if value == 0:
        log.debug("Selling out %s" % (security))
    else:
        log.debug("Order %s to value %f" % (security, value))
    return order_target_value(security, value)

def open_position(security, value):
    order = order_target_value_(security, value)
    if order != None and order.filled > 0:
        return True
    return False

def close_position(position):
    security = position.security
    order = order_target_value_(security, 0)
    if order != None:
        if order.status == OrderStatus.held and order.filled == order.amount:
            return True
    return False

# 打印持仓信息
def print_position_info(context):
    trades = get_trades()
    for _trade in trades.values():
        print('成交记录：'+str(_trade))
    
    if g.in_defense_mode:
        print('策略状态：防御模式')
        if g.defense_start_date:
            current_date = context.current_dt.date()
            days_in_defense = (current_date - g.defense_start_date).days
            remaining_days = max(0, g.defense_duration - days_in_defense)
            print('防御已持续：{}天，剩余：{}天'.format(days_in_defense, remaining_days))
    else:
        print('策略状态：正常模式')
        
        # 计算并显示当前回撤
        current_value = context.portfolio.total_value
        if g.portfolio_history:
            lookback_days = min(len(g.portfolio_history), g.defense_duration)
            recent_history = g.portfolio_history[-lookback_days:]
            if recent_history:
                max_value = max([record['total_value'] for record in recent_history])
                if max_value > 0:
                    drawdown = (current_value - max_value) / max_value * 100
                    print('当前回撤：{:.2f}% (相对于最近{}天最高点)'.format(drawdown, lookback_days))
    
    if not g.in_defense_mode:
        print('ATR止损记录：')
        for stock, stop_price in g.atr_stop_loss_records.items():
            if stock in context.portfolio.positions:
                position = context.portfolio.positions[stock]
                current_price = position.price
                distance_pct = (current_price - stop_price) / current_price * 100 if current_price > 0 else 0
                print('股票:{}，止损价:{:.2f}，现价:{:.2f}，距离止损:{:.2f}%'.format(
                    stock, stop_price, current_price, distance_pct))
    
    total_value = context.portfolio.total_value
    starting_cash = context.portfolio.starting_cash
    overall_return = (total_value - starting_cash) / starting_cash * 100
    print('整体收益：起始资金{:.2f}，当前总资产{:.2f}，收益率{:.2f}%'.format(
        starting_cash, total_value, overall_return))
    
    for position in list(context.portfolio.positions.values()):
        securities = position.security
        cost = position.avg_cost
        price = position.price
        ret = 100*(price/cost-1) if cost > 0 else 0
        value = position.value
        amount = position.total_amount    
        print('代码:{}'.format(securities))
        print('成本价:{}'.format(format(cost, '.2f')))
        print('现价:{}'.format(price))
        print('收益率:{}%'.format(format(ret, '.2f')))
        print('持仓(股):{}'.format(amount))
        print('市值:{}'.format(format(value, '.2f')))
        print('———————————————————————————————————')
    print('———————————————————————————————————————分割线————————————————————————————————————————')