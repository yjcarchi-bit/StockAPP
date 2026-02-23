# 克隆自聚宽文章：https://www.joinquant.com/post/67282
# 标题：“低回撤”才是硬道理，3年90倍最大回撤9%
# 作者：好运来临

# 导入函数库
from jqdata import *
import numpy as np
import pandas as pd
# ===================== 辅助函数（核心修复calculate_rsi） =====================
def calculate_macd(close, fastperiod=12, slowperiod=26, signalperiod=9):
    """计算MACD指标，返回DIF, DEA, MACD"""
    ema_fast = close.ewm(span=fastperiod, adjust=False).mean()
    ema_slow = close.ewm(span=slowperiod, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signalperiod, adjust=False).mean()
    macd = 2 * (dif - dea)
    return dif.iloc[-1], dea.iloc[-1], macd.iloc[-1]
def calculate_rsi(close, n=14):
    """修复版：计算RSI指标，使用标准EMA算法，返回最后一个RSI数值"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    
    avg_gain = gain.ewm(com=n-1, adjust=False).mean()
    avg_loss = loss.ewm(com=n-1, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    rsi = rsi.fillna(50)
    rsi = rsi.replace([np.inf, -np.inf], 100)
    
    return rsi.iloc[-1] if not rsi.empty else 50
def calculate_account_drawdown(context):
    """计算账户最大回撤，返回回撤比例"""
    total_value = context.portfolio.total_value
    if not hasattr(g, 'max_total_value'):
        g.max_total_value = context.portfolio.starting_cash
    if total_value > g.max_total_value:
        g.max_total_value = total_value
    drawdown = (g.max_total_value - total_value) / g.max_total_value
    return round(drawdown, 4)
def check_trend_recovery(context):
    """【放宽条件】判断沪深300趋势是否转好，返回(是否解锁, 原因)"""
    bench_hist = get_price('000300.XSHG', end_date=context.current_dt, count=60, frequency='1d', 
                           fields=['close', 'volume'], fq='pre')
    if len(bench_hist) < 60:
        return False, "沪深300数据不足60天，无法判断趋势"
    
    b_close, b_vol = bench_hist['close'], bench_hist['volume']
    b_current = b_close.iloc[-1]
    b_ma20 = b_close.rolling(20).mean().iloc[-1]
    b_macd = calculate_macd(b_close)
    drawdown = calculate_account_drawdown(context)
    # 解锁条件【从4个→3个核心，大幅放宽】
    cond1 = b_current > b_ma20  # 沪深300站上20日线（趋势反转核心）
    cond2 = b_macd[0] > b_macd[1]  # MACD金叉（动能转强）
    cond3 = drawdown < 0.08  # 账户回撤收窄至8%以内（风险释放，原5%）
    # 移除量比>1.2的严苛要求，保留核心趋势判断
    
    if cond1 and cond2 and cond3:
        return True, f"解锁成功→沪深300站上20日线+MACD金叉+回撤{drawdown*100:.1f}%<8%"
    else:
        fail_reason = []
        if not cond1: fail_reason.append(f"沪深300未站上20日线({b_current:.2f}<{b_ma20:.2f})")
        if not cond2: fail_reason.append(f"MACD未金叉(DIF{b_macd[0]:.4f}≤DEA{b_macd[1]:.4f})")
        if not cond3: fail_reason.append(f"回撤{drawdown*100:.1f}%≥8%")
        return False, "解锁失败→" + "｜".join(fail_reason)
# ===================== 策略主代码（仅修改initialize调度，其余无修改） =====================
def initialize(context):
    set_benchmark('000300.XSHG')
    set_slippage(FixedSlippage(0.001))
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, 
                             close_commission=0.0003, close_today_commission=0, min_commission=5), type='stock')
    
    # 全局变量
    g.max_positions = 3        # 最大持仓3只
    g.stop_loss_ratio = 0.05   # 5%止损
    g.take_profit_ratio = 0.35 # 35%止盈
    g.bull_market_threshold = 1.03  # 牛市阈值
    g.strong_bull_threshold = 1.04  # 强势牛市阈值
    g.empty_drawdown = 0.10    # 回撤≥10%触发空仓
    g.bull_add_ratio = 1.2     # 牛市加仓比例
    g.stock_pool_limit = 100   # 选股池数量限制
    g.drawdown_lock = False    # 回撤空仓锁定标记
    g.buy_signals = []         # 提前初始化买入信号，避免未定义
    g.sold_today = []          # 当天已卖出股票黑名单，防止止盈止损后立即买回
    # 运行函数：盘前选股 + 盘中交易 + 午后风控 + 收盘日志
    run_daily(before_market_open, time='09:00')  # 9点盘前选股
    run_daily(trade, time='09:30')  # 9:30开盘交易
    run_daily(check_risk, time='14:30')  # 14:30午后风控
    run_daily(print_daily_position_and_profit, time='15:10')  # 15:10收盘后打印日志

## 盘前选股【无修改】
def before_market_open(context):
    stock_list = []  # 使用列表收集数据，避免循环中pd.concat
    # 1. 【前移解锁】若处于锁定状态，先判断是否解锁
    if g.drawdown_lock:
        is_unlock, unlock_reason = check_trend_recovery(context)
        if is_unlock:
            g.drawdown_lock = False  # 解除锁定
        log.info(f"【回撤锁定检查】{unlock_reason}")
        if not is_unlock:
            g.buy_signals = []
            return  # 未解锁，直接返回，不生成信号
    # 2. 正常生成沪深300成分股选股信号
    hs300_stocks = get_index_stocks('000300.XSHG')
    if not hs300_stocks:
        g.buy_signals = []
        log.info("【选股失败】沪深300成分股获取失败，当日无买入信号")
        return
    select_stocks = hs300_stocks[:g.stock_pool_limit]
    # 因子计算+打分
    for stock in select_stocks:
        fdf = get_fundamentals(query(valuation.market_cap).filter(valuation.code == stock))
        if fdf.empty: continue
        market_cap = fdf['market_cap'].iloc[0]
        hist = get_price(stock, end_date=context.current_dt, count=60, frequency='1d', 
                         fields=['close', 'volume'], fq='pre')
        if len(hist) < 60: continue
        close = hist['close']
        volume = hist['volume']
        ma5, ma20 = close.rolling(5).mean().iloc[-1], close.rolling(20).mean().iloc[-1]
        momentum_5 = close.iloc[-1] / close.iloc[-6] - 1
        momentum_20 = close.iloc[-1] / close.iloc[-21] - 1
        trend_strength = (ma5 - ma20) / ma20
        volatility = close.rolling(20).std().iloc[-1] / close.iloc[-1]
        avg20_vol = volume.rolling(20).mean().iloc[-1]
        volume_ratio = volume.iloc[-1] / avg20_vol if avg20_vol != 0 else 0
        # 打分
        score = 0
        if market_cap > 100: score += 10
        if momentum_5 > 0.05: score += 25
        if momentum_20 > 0.10: score += 20
        if trend_strength > 0.01: score += 25
        if volume_ratio > 1.5: score += 15
        if volatility < 0.08: score += 5
        stock_list.append({
            'code': stock, 'score': score, 'momentum_5': momentum_5, 'momentum_20': momentum_20,
            'trend_strength': trend_strength, 'volatility': volatility, 'volume_ratio': volume_ratio,
            'market_cap': market_cap
        })
    # 一次性创建DataFrame，避免O(n²)复杂度
    stock_data = pd.DataFrame(stock_list) if stock_list else pd.DataFrame(columns=['code', 'score', 'momentum_5', 'momentum_20', 
                                       'trend_strength', 'volatility', 'volume_ratio', 'market_cap'])
    # 3. 【信号校验】生成信号+主动换股，无信号则用沪深300前3只兜底
    if not stock_data.empty:
        stock_data = stock_data.sort_values('score', ascending=False).reset_index(drop=True)
        g.buy_signals = stock_data['code'].tolist()[:g.max_positions*2]
        # 主动换股
        current_pos = [s for s in context.portfolio.positions if context.portfolio.positions[s].total_amount > 0]
        for stock in current_pos:
            if stock not in g.buy_signals:
                order_target(stock, 0)
                log.info(f"【主动换股】卖出{stock}，打分跌出高分区间")
        g.buy_signals = g.buy_signals[:g.max_positions]
    else:
        # 兜底：无信号时取沪深300前3只，避免解锁后无票可买
        g.buy_signals = hs300_stocks[:g.max_positions]
        log.info(f"【信号兜底】多因子打分无结果，取沪深300前{g.max_positions}只为买入信号")
    
    log.info(f"【选股完成】买入信号：{g.buy_signals}，共{len(g.buy_signals)}只")

## 盘中交易【无修改】
def trade(context):
    g.sold_today = []  # 每次交易开始时清空当日卖出黑名单
    
    if g.drawdown_lock:
        log.info("【交易拦截】仍处于回撤锁定状态，暂停买入")
        return
    
    current_pos = [s for s in context.portfolio.positions if context.portfolio.positions[s].total_amount > 0]
    current_pos_count = len(current_pos)
    available_cash = context.portfolio.available_cash
    buy_candidates = [s for s in g.buy_signals if s not in current_pos]  # 仅买未持仓标的
    # 1. 先执行止盈/止损（无修改）
    for stock in current_pos:
        pos = context.portfolio.positions[stock]
        if pos.total_amount <= 0: continue
        profit_ratio = (pos.price - pos.avg_cost) / pos.avg_cost if pos.avg_cost != 0 else 0
        if profit_ratio >= g.take_profit_ratio or profit_ratio <= -g.stop_loss_ratio:
            order_target(stock, 0)
            log.info(f"【止盈/止损】卖出{stock}，收益率：{profit_ratio:.2%}")
            g.sold_today.append(stock)  # 加入当日卖出黑名单
    # 止盈止损后重新计算持仓数量（修复持仓计数不准确问题）
    current_pos = [s for s in context.portfolio.positions if context.portfolio.positions[s].total_amount > 0 and s not in g.sold_today]
    current_pos_count = len(current_pos)
    # 过滤掉当天已卖出的股票，防止立即买回
    buy_candidates = [s for s in buy_candidates if s not in g.sold_today]
    # 2. 买入核心逻辑【放宽门槛+解锁后优先买入】
    # 放宽现金门槛：1000→500；移除原有破60日线拦截（解锁后已判断趋势，避免重复拦截）
    if current_pos_count >= g.max_positions:
        log.info(f"【交易拦截】持仓{current_pos_count}只≥最大持仓{g.max_positions}只，暂停买入")
        return
    if available_cash < 500:
        log.info(f"【交易拦截】可用现金{available_cash:.2f}元<500元，暂停买入")
        return
    if not buy_candidates:
        log.info(f"【交易拦截】无未持仓买入信号，当前持仓：{current_pos}")
        return
    # 牛市判断+资金分配
    bench_hist = get_price('000300.XSHG', count=60, frequency='1d', fields=['close'], fq='pre')
    b_ma20 = bench_hist['close'].rolling(20).mean().iloc[-1]
    b_current = bench_hist['close'].iloc[-1]
    is_bull = b_current > b_ma20 * g.bull_market_threshold
    cash_per_stock = available_cash / len(buy_candidates)
    # 执行买入（至少1手，无其他拦截）
    for stock in buy_candidates:
        if current_pos_count >= g.max_positions: break
        buy_cash = cash_per_stock * g.bull_add_ratio if is_bull else cash_per_stock
        current_price = get_current_data()[stock].last_price
        min_cash = current_price * 100  # 1手最低资金
        if buy_cash < min_cash:
            log.info(f"【买入拦截】{stock}需至少{min_cash:.2f}元，当前分配{buy_cash:.2f}元，跳过")
            continue
        # 执行买入
        order_value(stock, buy_cash)
        log.info(f"【买入成功】{stock}，牛市：{is_bull}，买入金额：{buy_cash:.2f}元")
        current_pos_count += 1

## 午后风控【无修改】
def check_risk(context):
    total_value = context.portfolio.total_value
    if total_value <= 0: return
    current_pos = [s for s in context.portfolio.positions if context.portfolio.positions[s].total_amount > 0]
    pos_value = sum([context.portfolio.positions[s].total_amount * context.portfolio.positions[s].price for s in current_pos])
    pos_ratio = pos_value / total_value if total_value > 0 else 0
    drawdown = calculate_account_drawdown(context)
    # 复合择时
    bench_hist = get_price('000300.XSHG', count=60, frequency='1d', fields=['close', 'volume'], fq='pre')
    b_close, b_vol = bench_hist['close'], bench_hist['volume']
    b_current, b_ma20, b_ma60 = b_close.iloc[-1], b_close.rolling(20).mean().iloc[-1], b_close.rolling(60).mean().iloc[-1]
    b_macd = calculate_macd(b_close)
    b_rsi = calculate_rsi(b_close)
    b_vol_ma20 = b_vol.rolling(20).mean().iloc[-1]
    b_vol_ratio = b_vol.iloc[-1] / b_vol_ma20 if pd.notna(b_vol_ma20) and b_vol_ma20 != 0 else 1.0
    is_strong_bull = (b_current > b_ma20 * g.strong_bull_threshold) and (b_macd[0] > b_macd[1]) and (b_rsi < 80) and (b_vol_ratio > 1.2)
    is_bear = (b_current < b_ma20) and (b_macd[0] < b_macd[1])
    # 1. 强空仓条件【优化：仅回撤≥10%才锁定，其他空仓不锁定】
    if drawdown >= g.empty_drawdown:
        for stock in current_pos:
            order_target(stock, 0)
        g.drawdown_lock = True  # 仅回撤触发锁定
        log.info(f"【强空仓+锁定】账户回撤{drawdown*100:.1f}%≥10%，清仓所有标的并锁定")
        return
    elif b_current < b_ma60 and b_macd[0] < b_macd[1]:
        for stock in current_pos:
            order_target(stock, 0)
        # 非回撤触发的空仓，不锁定，后续可正常买入
        log.info(f"【强空仓-不锁定】沪深300破60日线+MACD死叉，清仓所有标的（未锁定）")
        return
    # 2. 强势牛市加仓（无修改）
    if is_strong_bull and pos_ratio < 0.95 and len(g.buy_signals) > 0 and current_pos:
        target_pos = total_value * 0.95
        add_amount = target_pos - pos_value
        if add_amount > 0:
            top1 = g.buy_signals[0]
            if top1 in current_pos:
                order_value(top1, add_amount * 0.8)
                log.info(f"【强势加仓】{top1}，加仓金额{add_amount*0.8:.2f}元")
            if len(g.buy_signals) >= 2 and g.buy_signals[1] in current_pos:
                order_value(g.buy_signals[1], add_amount * 0.2)
                log.info(f"【强势加仓】{g.buy_signals[1]}，加仓金额{add_amount*0.2:.2f}元")
    # 3. 熊市减仓（无修改）
    if is_bear and pos_ratio > 0.6 and current_pos:
        target_pos = total_value * 0.6
        reduce_amount = pos_value - target_pos
        if reduce_amount > 0:
            low_score_stocks = [s for s in current_pos if s not in g.buy_signals]
            if not low_score_stocks:
                low_score_stocks = current_pos[-1:]
            for stock in low_score_stocks:
                pos = context.portfolio.positions[stock]
                stock_val = pos.total_amount * pos.price
                reduce_val = min(stock_val, reduce_amount)
                target_amount = int((stock_val - reduce_val) / pos.price)
                target_amount = round(target_amount / 100) * 100 if target_amount >0 else 0
                order_target(stock, target_amount)
                log.info(f"【熊市减仓】{stock}，减仓金额{reduce_val:.2f}元")

## 收盘日志【无修改】
def print_daily_position_and_profit(context):
    current_date = context.current_dt.strftime('%Y-%m-%d')
    tv = context.portfolio.total_value
    ac = context.portfolio.available_cash
    sc = context.portfolio.starting_cash
    tp = tv - sc
    tpr = tp / sc if sc>0 else 0
    drawdown = calculate_account_drawdown(context)
    # 沪深300趋势数据
    bench_hist = get_price('000300.XSHG', count=60, frequency='1d', fields=['close'], fq='pre')
    b_current = bench_hist['close'].iloc[-1] if len(bench_hist)>=60 else 0
    b_ma20 = bench_hist['close'].rolling(20).mean().iloc[-1] if len(bench_hist)>=60 else 0
    b_ma60 = bench_hist['close'].rolling(60).mean().iloc[-1] if len(bench_hist)>=60 else 0
    is_bull = b_current > b_ma20 * g.bull_market_threshold if len(bench_hist)>=60 else False
    # 打印核心信息
    log.info("="*80)
    log.info(f"【{current_date} 沪深300强趋量化策略 - 账户汇总】")
    log.info(f"初始资金：{sc:.2f}元 | 当前总市值：{tv:.2f}元 | 可用现金：{ac:.2f}元")
    log.info(f"总收益：{tp:.2f}元（{tpr:.2%}）| 最大回撤：{drawdown*100:.1f}% | 牛市状态：{is_bull}")
    log.info(f"沪深300：{b_current:.2f} | 20日线：{b_ma20:.2f} | 60日线：{b_ma60:.2f}")
    log.info(f"核心状态：回撤锁定={g.drawdown_lock} | 买入信号={g.buy_signals} | 信号数量={len(g.buy_signals)}")
    # 持仓明细
    current_pos = [s for s in context.portfolio.positions if context.portfolio.positions[s].total_amount > 0]
    log.info(f"当前持仓：{len(current_pos)}只（最大可持仓{g.max_positions}只）")
    if not current_pos:
        log.info("【持仓状态】空仓")
    else:
        for stock in current_pos:
            pos = context.portfolio.positions[stock]
            name = get_security_info(stock).display_name if get_security_info(stock) else "未知"
            hold = pos.total_amount
            cost = pos.avg_cost
            price = pos.price
            val = hold * price
            profit = val - hold * cost
            pr = (price - cost)/cost if cost>0 else 0
            log.info(f"  {stock}（{name}）| 持仓{hold}股 | 成本{cost:.2f} | 当前{price:.2f} | 收益{profit:.2f}元（{pr:.2%}）")
    log.info("="*80)