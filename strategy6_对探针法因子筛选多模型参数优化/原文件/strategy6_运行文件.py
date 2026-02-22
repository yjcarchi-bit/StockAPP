# 克隆自聚宽文章：https://www.joinquant.com/post/67193
# 标题：对探针法因子筛选多模型参数优化
# 作者：玮富世家

# --------------------------------------------------------------------------------
# 回测策略代码 (集成动态阈值)
# --------------------------------------------------------------------------------
from jqdata import *
from jqfactor import *
import numpy as np
import pandas as pd
import pickle
from six import StringIO, BytesIO
import talib
from sklearn.preprocessing import minmax_scale

def initialize(context):
    set_benchmark('000985.XSHG')
    set_option('use_real_price', True)
    set_option("avoid_future_data", True)
    set_slippage(FixedSlippage(0))
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, 
                             close_commission=0.0003, close_today_commission=0, min_commission=5), type='stock')
    log.set_level('order', 'error')
    
    g.stock_num = 10
    g.hold_list = []
    g.yesterday_HL_list = []

    g.avg_ai_score = 0
    g.avg_consistency = 0
    
    # 【新增】初始化历史一致性记录，用于计算动态阈值
    g.consistency_history = []
    
    # 加载模型文件 (请确保这些文件已上传到回测环境的研究根目录)
    try:
        g.model_reg = pickle.loads(read_file('model_reg_final.pkl'))
        g.model_cls = pickle.loads(read_file('model_cls_final.pkl'))
        g.model_dir = pickle.loads(read_file('model_dir_final.pkl'))
        g.factor_list = list(pd.read_csv(BytesIO(read_file('selected_factors.csv')))['factor'])
    except Exception as e:
        log.error(f"模型加载失败，请检查文件是否上传: {e}")

    run_daily(prepare_stock_list, '9:05')
    # 根据需求调整调仓频率，原代码为周度
    run_monthly(weekly_adjustment, 1, '9:30') 
    run_daily(record_portfolio_value_consistency, '9:31')
    run_daily(check_limit_up, '14:00')


def prepare_stock_list(context):
    g.hold_list = []
    for position in list(context.portfolio.positions.values()):
        stock = position.security
        g.hold_list.append(stock)
    if g.hold_list != []:
        df = get_price(g.hold_list, end_date=context.previous_date, frequency='daily', 
                       fields=['close', 'high_limit'], count=1, panel=False, fill_paused=False)
        df = df[df['close'] == df['high_limit']]
        g.yesterday_HL_list = list(df.code)
    else:
        g.yesterday_HL_list = []

def get_stock_list(context):
    yesterday = context.previous_date
    today = context.current_dt
    initial_list = get_index_stocks('000985.XSHG', today)
    initial_list = filter_all_stock2(context, initial_list)

    # 分批获取因子数据
    # 注意：这里假设 g.factor_list 长度约为 40-70，按原代码分批逻辑
    # 如果因子数量变动，需动态调整切片，这里保留原逻辑
    f_len = len(g.factor_list)
    split_idx = 30
    
    factor_data1 = get_factor_values(initial_list, g.factor_list[:split_idx], end_date=yesterday, count=1)
    factor_data2 = get_factor_values(initial_list, g.factor_list[split_idx:], end_date=yesterday, count=1)

    df_jq_factor_value1 = pd.DataFrame(index=initial_list, columns=g.factor_list[:split_idx])
    for factor in g.factor_list[:split_idx]:
        df_jq_factor_value1[factor] = list(factor_data1[factor].T.iloc[:, 0])

    df_jq_factor_value2 = pd.DataFrame(index=initial_list, columns=g.factor_list[split_idx:])
    for factor in g.factor_list[split_idx:]:
        df_jq_factor_value2[factor] = list(factor_data2[factor].T.iloc[:, 0])

    df_jq_factor_value = pd.concat([df_jq_factor_value1, df_jq_factor_value2], axis=1)
    # 填充缺失值
    df_jq_factor_value = df_jq_factor_value.fillna(0) 

    # 三模型预测
    preds = np.column_stack([
        g.model_reg.predict(df_jq_factor_value),
        g.model_cls.predict(df_jq_factor_value),
        g.model_dir.predict(df_jq_factor_value)
    ])

    ai_score = preds.mean(axis=1)
    consistency = preds.var(axis=1, ddof=0)

    df = df_jq_factor_value.copy()
    df['AI_score'] = ai_score
    df['consistency'] = consistency

    g.avg_ai_score = df['AI_score'].mean()         
    g.avg_consistency = df['consistency'].mean()    

    # ================= 动态自适应阈值逻辑 (修改开始) =================
    
    # 1. 记录当前一致性到历史列表
    g.consistency_history.append(g.avg_consistency)
    
    # 2. 维护滑动窗口 (例如过去24次调仓，约2年)
    window_length = 24
    if len(g.consistency_history) > window_length:
        g.consistency_history.pop(0)
    
    # 3. 计算动态阈值 (取历史分布的 80% 分位数)
    # 冷启动保护：如果历史数据不足5次，使用默认值 0.005
    if len(g.consistency_history) >= 5:
        dynamic_threshold = np.percentile(g.consistency_history, 80)
    else:
        dynamic_threshold = 0.005

    log.info(f"当前市场一致性方差: {g.avg_consistency:.5f}, 动态防御阈值(Top80%): {dynamic_threshold:.5f}")

    # 4. 使用动态阈值进行判断
    if g.avg_consistency > dynamic_threshold:
        log.info("【防御模式触发】市场分歧过大，优先选择确定性(consistency)高的股票")
        # 逻辑：先取一致性最好(数值最小)的10%
        df_sorted_by_consistency = df.sort_values(by='consistency', ascending=True)
        top_10_percent = int(0.1 * len(df_sorted_by_consistency))
        df_candidate = df_sorted_by_consistency.head(top_10_percent)
        
        # 再在候选池中按AI得分排序取前20%
        df_candidate_sorted = df_candidate.sort_values(by='AI_score', ascending=False)
        top_20_percent = int(0.2 * len(df_candidate_sorted))
        df_selected = df_candidate_sorted.head(top_20_percent)
    else:
        log.info("【进攻模式】市场分歧正常，直接选择AI得分最高的股票")
        df_sorted_by_ai = df.sort_values(by='AI_score', ascending=False)
        top_20_percent = int(0.2 * len(df_sorted_by_ai))
        df_selected = df_sorted_by_ai.head(top_20_percent)
        
    # ================= 动态自适应阈值逻辑 (修改结束) =================

    lst = df_selected.index.tolist()
    lst = filter_paused_stock(lst)
    lst = filter_limitup_stock(context, lst)
    lst = filter_limitdown_stock(context, lst)
    lst = lst[:g.stock_num]

    return lst

def weekly_adjustment(context):
    target_list = get_stock_list(context)
    for stock in g.hold_list:
        if (stock not in target_list) and (stock not in g.yesterday_HL_list):
            position = context.portfolio.positions[stock]
            close_position(position)
    position_count = len(context.portfolio.positions)
    target_num = len(target_list)
    if target_num > position_count:
        buy_num = min(len(target_list), g.stock_num - position_count)
        if buy_num > 0:
            value = context.portfolio.cash / buy_num
            for stock in target_list:
                if stock not in list(context.portfolio.positions.keys()):
                    if open_position(stock, value):
                        if len(context.portfolio.positions) == target_num:
                            break

def check_limit_up(context):
    now_time = context.current_dt
    if g.yesterday_HL_list != []:
        for stock in g.yesterday_HL_list:
            current_data = get_price(stock, end_date=now_time, frequency='1m', fields=['close', 'high_limit'],
                                     skip_paused=False, fq='pre', count=1, panel=False, fill_paused=True)
            if current_data.iloc[0, 0] < current_data.iloc[0, 1]:
                log.info("[%s]涨停打开，卖出" % (stock))
                position = context.portfolio.positions[stock]
                close_position(position)

def filter_all_stock2(context, stock_list):
    # 动态获取过去一年的所有交易日，取最近的一个
    by_date = context.previous_date
    all_stocks = get_all_securities(date=by_date).index.tolist()
    stock_list = list(set(stock_list).intersection(set(all_stocks)))
    curr_data = get_current_data()
    return [stock for stock in stock_list if not (
            stock.startswith(('3', '68', '4', '8')) or
            curr_data[stock].paused or
            curr_data[stock].is_st or
            ('ST' in curr_data[stock].name) or
            ('*' in curr_data[stock].name) or
            ('退' in curr_data[stock].name) or
            (curr_data[stock].day_open == curr_data[stock].high_limit) or
            (curr_data[stock].day_open == curr_data[stock].low_limit)
    )]

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

def filter_paused_stock(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list if not current_data[stock].paused]

def filter_limitup_stock(context, stock_list):
    # 使用 history 获取最近一分钟数据代替 last_prices 
    # 注意：history 返回的是 DataFrame，需要正确索引
    last_prices = history(1, unit='1m', field='close', security_list=stock_list)
    current_data = get_current_data()
    return [stock for stock in stock_list if stock in context.portfolio.positions.keys()
            or last_prices[stock][-1] < current_data[stock].high_limit]

def filter_limitdown_stock(context, stock_list):
    last_prices = history(1, unit='1m', field='close', security_list=stock_list)
    current_data = get_current_data()
    return [stock for stock in stock_list if stock in context.portfolio.positions.keys()
            or last_prices[stock][-1] > current_data[stock].low_limit]

def record_portfolio_value_consistency(context):
    record(模型预测全市场不确定性均值=g.avg_consistency)