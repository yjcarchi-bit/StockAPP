# 克隆自聚宽文章：https://www.joinquant.com/post/66658
# 标题：多策略组合5年440%
# 作者：鱼树

# 克隆自聚宽文章：https://www.joinquant.com/post/66642
# 标题：一个简易的多策略封装模板
# 作者：zifan

"""
多策略模板 by zifan
"""

from jqdata import *
from jqfactor import *
import numpy as np
import pandas as pd

def initialize(context):
    log.set_level("order", "error")

    set_benchmark("000300.XSHG")
    set_option("avoid_future_data", True)
    set_option("use_real_price", True)
    set_option('match_with_order_book', True) # 模拟盘开启盘口撮合模式

    g.STRATEGY_CONFIG = [
        {
            "name": "cash",
            "class": Cash,
            "pct": 0.00,
            "run": [],
        },
        {
            "name": "小市值",
            "class": PNFTPtCRITR,
            "pct": 0.00,
            "run": [
                {
                    "type": "run_daily",
                    "func": "prepare_stock_list",
                    "params": {
                        "time": "9:05",
                        "reference_security": "000300.XSHG",
                    },
                },
                {
                    "type": "run_weekly",
                    "func": "weekly_adjustment",
                    "params": {
                        "weekday": 1,
                        "time": "10:20",
                        "reference_security": "000300.XSHG",
                    },
                },
                {
                    "type": "run_daily",
                    "func": "check_limit_up",
                    "params": {
                        "time": "14:00",
                        "reference_security": "000300.XSHG",
                    },
                },
            ],
        },
        {
            "name": "搅屎棍",
            "class": FMS_Strategy,
            "pct": 0.43,
            "run": [
                {
                    "type": "run_daily",
                    "func": "prepare_stock_list",
                    "params": {
                        "time": "9:05",
                        "reference_security": "000300.XSHG",
                    },
                },
                {
                    "type": "run_weekly",
                    "func": "weekly_adjustment",
                    "params": {
                        "weekday": 1,
                        "time": "11:20",
                        "reference_security": "000300.XSHG",
                    },
                },
                {
                    "type": "run_daily",
                    "func": "check_limit_up",
                    "params": {
                        "time": "14:20",
                        "reference_security": "000300.XSHG",
                    },
                },
            ],
        },
        {
            "name": "偷鸡摸狗",
            "class": Steal_Dog_Strategy,
            "pct": 0.22,
            "run": [
                {
                    "type": "run_daily",
                    "func": "prepare_stock_list",
                    "params": {
                        "time": "9:05",
                    },
                },
                {
                    "type": "run_daily",
                    "func": "trade",
                    "params": {
                        "time": "9:45",
                    },
                },
                {
                    "type": "run_daily",
                    "func": "stop_loss",
                    "params": {
                        "time": "14:00",
                    },
                },
            ],
        },
        {
            "name": "ETF轮动",
            "class": ETF_Rotation_Strategy,
            "pct": 0.35,
            "run": [
                {
                    "type": "run_daily",
                    "func": "trade",
                    "params": {
                        "time": "11:05",
                    },
                },
            ],
        },
    ]

    set_subportfolios([SubPortfolioConfig(context.portfolio.starting_cash * strategy["pct"], "stock") for strategy in g.STRATEGY_CONFIG])
    process_initialize(context)

def process_initialize(context):
    set_slippage(FixedSlippage(0.001), type="fund")
    set_slippage(FixedSlippage(0.001), type="stock")
    set_order_cost(
        OrderCost(
            open_tax=0,
            close_tax=0.001,
            open_commission=0.0001,
            close_commission=0.0001,
            close_today_commission=0,
            min_commission=5,
        ),
        type="stock",
    )
    set_order_cost(
        OrderCost(
            open_tax=0,
            close_tax=0,
            open_commission=0,
            close_commission=0,
            close_today_commission=0,
            min_commission=0,
        ),
        type="mmf",
    )
    
    g.strategys = []
    for i in range(len(g.STRATEGY_CONFIG)):
        if g.STRATEGY_CONFIG[i]["pct"] == 0:
            continue
        strategy = g.STRATEGY_CONFIG[i]["class"](i, g.STRATEGY_CONFIG[i]["name"])
        strategy.initialize(context)
        g.strategys.append(strategy)
        for task in g.STRATEGY_CONFIG[i]["run"]:
            name = f'FUNC_{i}_{task["func"]}'
            exec(f"""def {name}(context):return getattr(g.strategys[{len(g.strategys)-1}], "{task["func"]}")(context)""", globals())
            globals()[task["type"]](globals()[name], **task["params"])

    run_daily(record_all_strategies_daily_value, "15:00")

def record_all_strategies_daily_value(context):
    for strategy in g.strategys:
        strategy.record_daily_value(context)

class Strategy:
    def __init__(self, subportfolio_index, name):
        self.subportfolio_index = subportfolio_index
        self.name = name
        self.portfolio_value = pd.DataFrame(columns=['date', 'total_value'])
        self.starting_cash = None

    def record_daily_value(self, context):
        subportfolio = context.subportfolios[self.subportfolio_index]
        new_data = {'date': context.current_dt.date(), 'total_value': subportfolio.total_value}
        self.portfolio_value = self.portfolio_value.append(new_data, ignore_index=True)
        if self.starting_cash is None:
            self.starting_cash = subportfolio.total_value
        if self.starting_cash == 0:
            returns = 0
        else:
            returns = (subportfolio.total_value / self.starting_cash - 1) * 100
        rounded_returns = round(returns, 1)
        record(**{self.name +'': rounded_returns})

    def order_target_value(self, security, value):
        return order_target_value(security, value, pindex=self.subportfolio_index)

    def order(self, security, amount):
        return order(security, amount, pindex=self.subportfolio_index)

    def order_target(self, security, amount):
        return order_target(security, amount, pindex=self.subportfolio_index)

    def order_value(self, security, value):
        return order_value(security, value, pindex=self.subportfolio_index)


class Cash(Strategy):
    def initialize(g, context):
        g.target = "511880.XSHG"
        pass


class PNFTPtCRITR(Strategy):
    """
    原始过程化 PNFTPtCRITR 策略的类封装版。
    - 将原来存储在 g.xxx 的变量迁移为 self.xxx
    - 使用类内下单封装（调用 Strategy 基类的方法）
    - 保留原始逻辑、过滤器、因子、系数等不变
    """
    def __init__(self, subportfolio_index, name):
        super(PNFTPtCRITR, self).__init__(subportfolio_index, name)
        # 成员将在 initialize 中被初始化
        self.stock_num = None
        self.hold_list = None
        self.yesterday_HL_list = None
        self.factor_list = None

    def initialize(self, context):
        # 初始化成员变量（从原 g.* 迁移）
        self.stock_num = 2
        self.hold_list = []
        self.yesterday_HL_list = []
        self.factor_list = [
            'price_no_fq',                  # 技术指标因子 不复权价格因子
            'total_profit_to_cost_ratio',   # 质量类因子 成本费用利润率
            'inventory_turnover_rate'       # 质量类因子 存货周转率
        ]

    # -------------------------
    # 1-1 准备股票池
    # -------------------------
    def prepare_stock_list(self, context):
        # 获取已持有列表
        self.hold_list = []
        for position in list(context.portfolio.subportfolios[self.subportfolio_index].positions.values()):
            stock = position.security
            self.hold_list.append(stock)

        # 获取昨日涨停列表（在持仓中）
        if self.hold_list:
            df = get_price(self.hold_list,
                           end_date=context.previous_date,
                           frequency='daily',
                           fields=['close', 'high_limit'],
                           count=1,
                           panel=False,
                           fill_paused=False)
            df = df[df['close'] == df['high_limit']]
            # df.code 是代码列
            self.yesterday_HL_list = list(df.code)
        else:
            self.yesterday_HL_list = []

    # -------------------------
    # 1-2 选股模块（返回 final_list）
    # -------------------------
    def get_stock_list(self, context):
        yesterday = context.previous_date
        initial_list = get_all_securities().index.tolist()

        initial_list = self.filter_new_stock(context, initial_list)
        initial_list = self.filter_kcbj_stock(initial_list)
        initial_list = self.filter_st_stock(initial_list)

        # MS: 获取因子值
        factor_values = get_factor_values(
            initial_list,
            [
                self.factor_list[0],
                self.factor_list[1],
                self.factor_list[2],
            ],
            end_date=yesterday,
            count=1
        )

        # 构建 DataFrame（index 为代码）
        df = pd.DataFrame(index=initial_list, columns=factor_values.keys())
        # 将因子列填入（与原代码相同的取法）
        df[self.factor_list[0]] = list(factor_values[self.factor_list[0]].T.iloc[:, 0])
        df[self.factor_list[1]] = list(factor_values[self.factor_list[1]].T.iloc[:, 0])
        df[self.factor_list[2]] = list(factor_values[self.factor_list[2]].T.iloc[:, 0])
        df = df.dropna()

        # 原始 coef_list（保持不变）
        coef_list = [
            -6.123355346008858e-05,
            -0.002579342458393642,
            -2.194257357346814e-06
        ]

        df['total_score'] = (coef_list[0] * df[self.factor_list[0]] +
                             coef_list[1] * df[self.factor_list[1]] +
                             coef_list[2] * df[self.factor_list[2]])

        df = df.sort_values(by=['total_score'], ascending=False)
        complex_factor_list = list(df.index)[:int(0.1 * len(list(df.index)))]

        # 取基本面剔除 eps <= 0，并按流通市值升序（与原脚本一致）
        q = query(valuation.code, valuation.circulating_market_cap, indicator.eps).filter(
            valuation.code.in_(complex_factor_list)
        ).order_by(valuation.circulating_market_cap.asc())

        df_funda = get_fundamentals(q)
        df_funda = df_funda[df_funda['eps'] > 0]
        final_list = list(df_funda.code)
        return final_list

    # -------------------------
    # 1-3 每周调仓：整体调整持仓
    # -------------------------
    def weekly_adjustment(self, context):
        # 获取应买入列表
        target_list = self.get_stock_list(context)
        target_list = self.filter_paused_stock(target_list)
        target_list = self.filter_limitup_stock(context, target_list)
        target_list = self.filter_limitdown_stock(context, target_list)

        # 截取不超过最大持仓数
        target_list = target_list[:min(self.stock_num, len(target_list))]

        # 卖出不在 target 且不在昨日涨停名单的持仓
        for stock in list(self.hold_list):
            # 若该持仓已经退出 portfolio.positions（例如已被平掉），跳过
            if stock not in context.portfolio.subportfolios[self.subportfolio_index].positions:
                continue
            if (stock not in target_list) and (stock not in self.yesterday_HL_list):
                log.info("卖出[%s]" % (stock))
                position = context.portfolio.subportfolios[self.subportfolio_index].positions[stock]
                self.close_position(position)
            else:
                log.info("已持有[%s]" % (stock))

        # 买入：按空位数量等额分配当前可用现金
        position_count = len([p for p in context.portfolio.subportfolios[self.subportfolio_index].positions.values() if p.total_amount > 0])
        target_num = len(target_list)
        if target_num > position_count:
            # 使用可用现金进行分配（与原脚本一致）
            value = context.portfolio.subportfolios[self.subportfolio_index].cash / (target_num - position_count) if (target_num - position_count) > 0 else 0
            for stock in target_list:
                # 仅当当前没有持仓时尝试开仓
                pos = context.portfolio.subportfolios[self.subportfolio_index].positions.get(stock)
                total_amount = pos.total_amount if pos is not None else 0
                if total_amount == 0:
                    if self.open_position(stock, value):
                        if len([p for p in context.portfolio.subportfolios[self.subportfolio_index].positions.values() if p.total_amount > 0]) == target_num:
                            break

    # -------------------------
    # 1-4 调整昨日涨停股票（收盘前检查）
    # -------------------------
    def check_limit_up(self, context):
        now_time = context.current_dt
        if self.yesterday_HL_list:
            for stock in list(self.yesterday_HL_list):
                current_data = get_price(
                    stock,
                    end_date=now_time,
                    frequency='1m',
                    fields=['close', 'high_limit'],
                    skip_paused=False,
                    fq='pre',
                    count=1,
                    panel=False,
                    fill_paused=True
                )
                # current_data.iloc[0,0] 是 close, [0,1] 是 high_limit (和原脚本一致)
                if current_data.iloc[0, 0] < current_data.iloc[0, 1]:
                    log.info("[%s]涨停打开，卖出" % (stock))
                    # 如果持仓存在则平仓
                    if stock in context.portfolio.subportfolios[self.subportfolio_index].positions:
                        position = context.portfolio.subportfolios[self.subportfolio_index].positions[stock]
                        self.close_position(position)
                else:
                    log.info("[%s]涨停，继续持有" % (stock))

    # -------------------------
    # 2-x 过滤函数（保持原逻辑）
    # -------------------------
    def filter_paused_stock(self, stock_list):
        current_data = get_current_data()
        return [stock for stock in stock_list if not current_data[stock].paused]

    def filter_st_stock(self, stock_list):
        current_data = get_current_data()
        filtered = [
            stock for stock in stock_list
            if (not current_data[stock].is_st)
            and ('ST' not in current_data[stock].name)
            and ('*' not in current_data[stock].name)
            and ('退' not in current_data[stock].name)
        ]
        return filtered

    def filter_kcbj_stock(self, stock_list):
        # 原脚本直接在循环中修改 list；这里返回新列表以更安全
        out = []
        for stock in stock_list:
            if stock[0] == '4' or stock[0] == '8' or stock[:2] == '68'or stock[:2] == '30':
                continue
            out.append(stock)
        return out

    def filter_limitup_stock(self, context, stock_list):
        # last_prices: DataFrame indexed by code with time series
        if not stock_list:
            return []
        try:
            last_prices = history(1, unit='1m', field='close', security_list=stock_list)
        except Exception:
            # 兼容性：history 在某些环境会抛异常，直接返回原列表
            last_prices = None

        current_data = get_current_data()
        out = []
        for stock in stock_list:
            # 若已在持仓则保留（原逻辑）
            if stock in context.portfolio.subportfolios[self.subportfolio_index].positions.keys():
                out.append(stock)
                continue
            # 若没有 history 数据可用，保守保留
            if last_prices is None:
                out.append(stock)
            else:
                try:
                    last_close = last_prices[stock][-1]
                    if last_close < current_data[stock].high_limit:
                        out.append(stock)
                except Exception:
                    out.append(stock)
        return out

    def filter_limitdown_stock(self, context, stock_list):
        if not stock_list:
            return []
        try:
            last_prices = history(1, unit='1m', field='close', security_list=stock_list)
        except Exception:
            last_prices = None

        current_data = get_current_data()
        out = []
        for stock in stock_list:
            if stock in context.portfolio.subportfolios[self.subportfolio_index].positions.keys():
                out.append(stock)
                continue
            if last_prices is None:
                out.append(stock)
            else:
                try:
                    last_close = last_prices[stock][-1]
                    if last_close > current_data[stock].low_limit:
                        out.append(stock)
                except Exception:
                    out.append(stock)
        return out

    def filter_new_stock(self, context, stock_list):
        # 使用模块级导入 datetime
        import datetime as _dt
        yesterday = context.previous_date
        out = []
        for stock in stock_list:
            try:
                info = get_security_info(stock)
                start_date = info.start_date
                if not (yesterday - start_date < _dt.timedelta(days=375)):
                    out.append(stock)
            except Exception:
                # 若无法获得信息则保留（更稳健）
                out.append(stock)
        return out

    # -------------------------
    # 3-x 交易模块：类内下单封装（保留原逻辑）
    # -------------------------
    def order_target_value_(self, security, value):
        """
        内部下单封装：调用 Strategy 基类的 order_target_value（已封装 pindex）
        返回 order 对象（或 None）
        """
        if value == 0:
            log.debug("Selling out %s" % (security))
        else:
            log.debug("Order %s to value %f" % (security, value))
        return self.order_target_value(security, value)

    def open_position(self, security, value):
        order_obj = self.order_target_value_(security, value)
        if order_obj is not None:
            # 若有成交量则认为开仓成功（与原脚本相同）
            try:
                if getattr(order_obj, 'filled', 0) > 0:
                    return True
            except Exception:
                # 若 order 对象不含 filled 字段，保守返回 False
                return False
        return False

    def close_position(self, position):
        security = position.security
        order_obj = self.order_target_value_(security, 0)  # 可能会因停牌失败
        if order_obj is not None:
            try:
                # 与原脚本相同的条件判断
                if order_obj.status == OrderStatus.held and order_obj.filled == order_obj.amount:
                    return True
            except Exception:
                # 若 order_obj 没有这些字段，则无法确认完全成交，返回 False
                return False
        return False


class FMS_Strategy(Strategy):
    """
    Four-Mess-Stick strategy (封装自原过程化脚本)。
    原脚本逻辑保留（仅将 g.* -> self.*，下单调用改为类方法）。
    """
    SW1 = {
        '801010': '农林牧渔I',
        '801020': '采掘I',
        '801030': '化工I',
        '801040': '钢铁I',
        '801050': '有色金属I',
        '801060': '建筑建材I',
        '801070': '机械设备I',
        '801080': '电子I',
        '801090': '交运设备I',
        '801100': '信息设备I',
        '801110': '家用电器I',
        '801120': '食品饮料I',
        '801130': '纺织服装I',
        '801140': '轻工制造I',
        '801150': '医药生物I',
        '801160': '公用事业I',
        '801170': '交通运输I',
        '801180': '房地产I',
        '801190': '金融服务I',
        '801200': '商业贸易I',
        '801210': '休闲服务I',
        '801220': '信息服务I',
        '801230': '综合I',
        '801710': '建筑材料I',
        '801720': '建筑装饰I',
        '801730': '电气设备I',
        '801740': '国防军工I',
        '801750': '计算机I',
        '801760': '传媒I',
        '801770': '通信I',
        '801780': '银行I',
        '801790': '非银金融I',
        '801880': '汽车I',
        '801890': '机械设备I',
        '801950': '煤炭I',
        '801960': '石油石化I',
        '801970': '环保I',
        '801980': '美容护理I'
    }

    def __init__(self, subportfolio_index, name):
        super(FMS_Strategy, self).__init__(subportfolio_index, name)
        # Will be initialized in initialize()
        self.stock_num = None
        self.hold_list = None
        self.yesterday_HL_list = None
        self.num = None

    def initialize(self, context):
        self.stock_num = 2
        self.hold_list = []
        self.yesterday_HL_list = []
        self.num = 1

    # -------------------------
    # 1-1 准备股票池
    # -------------------------
    def prepare_stock_list(self, context):
        # 获取已持有列表
        self.hold_list = []
        for position in list(context.portfolio.subportfolios[self.subportfolio_index].positions.values()):
            stock = position.security
            self.hold_list.append(stock)

        # 获取昨日涨停列表（在持仓中）
        if self.hold_list:
            df = get_price(self.hold_list,
                           end_date=context.previous_date,
                           frequency='daily',
                           fields=['close', 'high_limit'],
                           count=1,
                           panel=False,
                           fill_paused=False)
            df = df[df['close'] == df['high_limit']]
            self.yesterday_HL_list = list(df.code)
        else:
            self.yesterday_HL_list = []

    # -------------------------
    # industry / helper 收集
    # -------------------------
    def industry_count(self, stockList, industry_code, date):
        # 返回每个 industry_code 在 stockList 中的成分数
        i_Constituent_Stocks = {}
        for ic in industry_code:
            temp = get_industry_stocks(ic, date)
            i_Constituent_Stocks[ic] = list(set(temp).intersection(set(stockList)))
        count_dict = {}
        for name, content_list in i_Constituent_Stocks.items():
            count = len(content_list)
            count_dict[name] = count
        return count_dict

    def getStockIndustry(self, p_stocks, p_industries_type, p_day):
        dict_stk_2_ind = {}
        stocks_industry_dict = get_industry(p_stocks, date=p_day)
        for stock in stocks_industry_dict:
            if p_industries_type in stocks_industry_dict[stock]:
                dict_stk_2_ind[stock] = stocks_industry_dict[stock][p_industries_type]['industry_code']
        return pd.Series(dict_stk_2_ind)

    # -------------------------
    # 1-2 选股模块
    # -------------------------
    def get_stock_list(self, context):
        import datetime as _dt
        yesterday = context.previous_date
        today = context.current_dt
        final_list = []
        # 初始列表：取指数成分
        initial_list = get_index_stocks('000985.XSHG', today)
        p_count = 1
        p_industries_type = 'sw_l1'

        # 获取历史价格（防未来数据）
        h = get_price(initial_list, end_date=yesterday, frequency='1d', fields=['close'], count=p_count + 20, panel=False)
        h['date'] = pd.DatetimeIndex(h.time).date
        df_close = h.pivot(index='code', columns='date', values='close').dropna(axis=0)
        df_ma20 = df_close.rolling(window=20, axis=1).mean().iloc[:, -p_count:]
        df_bias = (df_close.iloc[:, -p_count:] > df_ma20)

        s_stk_2_ind = self.getStockIndustry(p_stocks=initial_list, p_industries_type=p_industries_type, p_day=yesterday)
        df_bias['industry_code'] = s_stk_2_ind

        df_ratio = ((df_bias.groupby('industry_code').sum() * 100.0) / df_bias.groupby('industry_code').count()).round()
        column_names = df_ratio.columns.tolist()

        # 取当天列并选 top g.num 个行业代码
        today_col = _dt.date(yesterday.year, yesterday.month, yesterday.day)
        top_values = df_ratio[today_col].nlargest(self.num)
        I = top_values.index.tolist()

        sum_of_top_values = df_ratio.sum()
        TT = sum_of_top_values[today_col]
        name_list = [self.SW1[code] for code in I if code in self.SW1]
        print(name_list)
        print('全市场宽度：', np.array(df_ratio.sum(axis=0).mean()))

        # 若不含特定行业则进入开仓路径（与原脚本逻辑）
        if '801780' not in I and '801050' not in I and '801950' not in I and '801040' not in I:
            # 基于 399101.XSHE 指数成分筛选
            S_stocks = get_index_stocks('399101.XSHE', today)
            stocks = self.filter_kcbj_stock(S_stocks)
            choice = self.filter_st_stock(stocks)
            choice = self.filter_new_stock(context, choice)

            q = query(valuation.code).filter(
                valuation.code.in_(choice),
                indicator.roe > 0.15,
                indicator.roa > 0.10,
            ).order_by(valuation.market_cap.asc()).limit(self.stock_num)

            BIG_stock_list = get_fundamentals(q).set_index('code').index.tolist()
            BIG_stock_list = self.filter_paused_stock(BIG_stock_list)
            BIG_stock_list = self.filter_limitup_stock(context, BIG_stock_list)
            L = self.filter_limitdown_stock(context, BIG_stock_list)
        else:
            print('跑')
            L = []
        return L

    # -------------------------
    # 1-3 每周调仓
    # -------------------------
    def weekly_adjustment(self, context):
        target_B = self.get_stock_list(context)
        # 卖出不在 target 且不在昨日涨停名单的持仓
        for stock in list(self.hold_list):
            if stock not in context.portfolio.subportfolios[self.subportfolio_index].positions:
                continue
            if (stock not in target_B) and (stock not in self.yesterday_HL_list):
                position = context.portfolio.subportfolios[self.subportfolio_index].positions[stock]
                self.close_position(position)

        # 计算买入目标并下单
        position_count = len([p for p in context.portfolio.subportfolios[self.subportfolio_index].positions.values() if p.total_amount > 0])
        target_num = len(target_B)
        if target_num > position_count:
            buy_num = min(len(target_B), self.stock_num * self.num - position_count)
            if buy_num <= 0:
                return
            value = context.portfolio.subportfolios[self.subportfolio_index].cash / buy_num
            for stock in target_B:
                if stock not in list(context.portfolio.subportfolios[self.subportfolio_index].positions.keys()):
                    if self.open_position(stock, value):
                        if len([p for p in context.portfolio.subportfolios[self.subportfolio_index].positions.values() if p.total_amount > 0]) == target_num:
                            break

    # -------------------------
    # 1-4 检查昨日涨停股票
    # -------------------------
    def check_limit_up(self, context):
        now_time = context.current_dt
        if self.yesterday_HL_list:
            for stock in list(self.yesterday_HL_list):
                current_data = get_price(
                    stock,
                    end_date=now_time,
                    frequency='1m',
                    fields=['close', 'high_limit'],
                    skip_paused=False,
                    fq='pre',
                    count=1,
                    panel=False,
                    fill_paused=True
                )
                if current_data.iloc[0, 0] < current_data.iloc[0, 1]:
                    log.info("[%s]涨停打开，卖出" % (stock))
                    if stock in context.portfolio.subportfolios[self.subportfolio_index].positions:
                        position = context.portfolio.subportfolios[self.subportfolio_index].positions[stock]
                        self.close_position(position)
                else:
                    log.info("[%s]涨停，继续持有" % (stock))

    # -------------------------
    # 3-x 交易模块（类方法封装）
    # -------------------------
    def order_target_value_(self, security, value):
        if value == 0:
            log.debug("Selling out %s" % (security))
        else:
            log.debug("Order %s to value %f" % (security, value))
        # call Strategy 基类的 order_target_value（会传入 pindex）
        return self.order_target_value(security, value)

    def open_position(self, security, value):
        order_obj = self.order_target_value_(security, value)
        if order_obj is not None:
            try:
                if getattr(order_obj, 'filled', 0) > 0:
                    return True
            except Exception:
                return False
        return False

    def close_position(self, position):
        security = position.security
        order_obj = self.order_target_value_(security, 0)
        if order_obj is not None:
            try:
                if order_obj.status == OrderStatus.held and order_obj.filled == order_obj.amount:
                    return True
            except Exception:
                return False
        return False

    # -------------------------
    # 2-x 过滤器（与原脚本一致）
    # -------------------------
    def filter_paused_stock(self, stock_list):
        current_data = get_current_data()
        return [stock for stock in stock_list if not current_data[stock].paused]

    def filter_st_stock(self, stock_list):
        current_data = get_current_data()
        return [
            stock for stock in stock_list
            if not current_data[stock].is_st
            and 'ST' not in current_data[stock].name
            and '*' not in current_data[stock].name
            and '退' not in current_data[stock].name
        ]

    def filter_kcbj_stock(self, stock_list):
        # 保持原脚本删除规则（包含以 '3' 开头也剔除）
        out = []
        for stock in stock_list:
            if stock[0] == '4' or stock[0] == '8' or stock[:2] == '68' or stock[0] == '3':
                continue
            out.append(stock)
        return out

    def filter_limitup_stock(self, context, stock_list):
        if not stock_list:
            return []
        try:
            last_prices = history(1, unit='1m', field='close', security_list=stock_list)
        except Exception:
            last_prices = None

        current_data = get_current_data()
        out = []
        for stock in stock_list:
            if stock in context.portfolio.subportfolios[self.subportfolio_index].positions.keys():
                out.append(stock)
                continue
            if last_prices is None:
                out.append(stock)
            else:
                try:
                    last_close = last_prices[stock][-1]
                    if last_close < current_data[stock].high_limit:
                        out.append(stock)
                except Exception:
                    out.append(stock)
        return out

    def filter_limitdown_stock(self, context, stock_list):
        if not stock_list:
            return []
        try:
            last_prices = history(1, unit='1m', field='close', security_list=stock_list)
        except Exception:
            last_prices = None

        current_data = get_current_data()
        out = []
        for stock in stock_list:
            if stock in context.portfolio.subportfolios[self.subportfolio_index].positions.keys():
                out.append(stock)
                continue
            if last_prices is None:
                out.append(stock)
            else:
                try:
                    last_close = last_prices[stock][-1]
                    if last_close > current_data[stock].low_limit:
                        out.append(stock)
                except Exception:
                    out.append(stock)
        return out

    def filter_new_stock(self, context, stock_list):
        import datetime as _dt
        yesterday = context.previous_date
        out = []
        for stock in stock_list:
            try:
                info = get_security_info(stock)
                start_date = info.start_date
                if not (yesterday - start_date < _dt.timedelta(days=375)):
                    out.append(stock)
            except Exception:
                out.append(stock)
        return out


class Steal_Dog_Strategy(Strategy):
    """
    封装自：2025清明节福利【偷鸡摸狗跑路】 (MarioC)
    已修复: get_index_stocks 的第二个参数改为 context.current_dt（避免传入 get_current_data() 导致的类型错误）。
    其余逻辑保持不变（变量从 context/g 迁移为 self）。
    """
    def __init__(self, subportfolio_index, name):
        super(Steal_Dog_Strategy, self).__init__(subportfolio_index, name)
        self.ETF_POOL = None
        self.stock_num = None
        self.strategy_type = None
        self.counterattack_days = None
        self.momentum_days = None
        self.days_counter = None
        self.firsttrade = None
        self.hold_list = None
        self.yesterday_HL_list = None

    def initialize(self, context):
        self.ETF_POOL = [
            '518880.XSHG',
            '513100.XSHG',
            '159915.XSHE',
        ]
        self.stock_num = 2
        self.strategy_type = '跑路'
        self.counterattack_days = 5
        self.momentum_days = 5
        self.days_counter = 0
        self.firsttrade = 0
        self.hold_list = []
        self.yesterday_HL_list = []

    def stop_loss(self, context):
        now_time = context.current_dt
        num = 0

        if self.yesterday_HL_list:
            for stock in self.yesterday_HL_list:
                current_data = get_price(stock, end_date=now_time, frequency='1m',
                                         fields=['close', 'high_limit'], skip_paused=False,
                                         fq='pre', count=1, panel=False)
                if current_data.iloc[0, 0] < current_data.iloc[0, 1]:
                    log.info(f"{stock} 涨停打开，卖出")
                    if stock in context.portfolio.subportfolios[self.subportfolio_index].positions:
                        self.close_position(context.portfolio.subportfolios[self.subportfolio_index].positions[stock])
                    num += 1
                else:
                    log.info(f"{stock} 涨停，继续持有")

        SS = []
        S = []
        for stock in list(self.hold_list):
            if stock not in self.ETF_POOL and stock in context.portfolio.subportfolios[self.subportfolio_index].positions:
                position = context.portfolio.subportfolios[self.subportfolio_index].positions[stock]
                try:
                    if position.price < position.avg_cost * 0.92:
                        self.order_target_value(stock, 0)
                        log.debug(f"止损卖出 {stock}")
                        num += 1
                    else:
                        S.append(stock)
                        SS.append((position.price - position.avg_cost) / position.avg_cost)
                except Exception:
                    continue

        if num >= 1 and SS:
            min_indices = np.argsort(SS)[:3]
            min_stocks = [S[i] for i in min_indices if i < len(S)]
            if min_stocks:
                cash = context.portfolio.subportfolios[self.subportfolio_index].cash / len(min_stocks)
                for stock in min_stocks:
                    self.order_value(stock, cash)
                    log.info(f"补仓 {stock},金额:{cash}")

    def prepare_stock_list(self, context):
        self.hold_list = list(context.portfolio.subportfolios[self.subportfolio_index].positions.keys())
        if self.hold_list:
            df = get_price(self.hold_list, end_date=context.previous_date, frequency='daily',
                           fields=['close', 'high_limit'], count=1, panel=False, fill_paused=False)
            df = df[df['close'] == df['high_limit']]
            self.yesterday_HL_list = list(df.code)
        else:
            self.yesterday_HL_list = []

    def calculate_momentum(self, etf, days=25):
        df = attribute_history(etf, days, '1d', ['close'])
        y = np.log(df['close'].values)
        x = np.arange(len(y))
        weights = np.linspace(1, 2, len(y))
        slope, intercept = np.polyfit(x, y, 1, w=weights)
        annualized_return = math.exp(slope * 250) - 1
        residuals = y - (slope * x + intercept)
        r_squared = 1 - (np.sum(weights * residuals ** 2) / np.sum(weights * (y - np.mean(y)) ** 2))
        return annualized_return * r_squared

    def filter_stocks(self, context, stock_list):
        stock_list = self.filter_paused_stock(stock_list)
        stock_list = self.filter_st_stock(stock_list)
        stock_list = self.filter_kcbj_stock(stock_list)
        stock_list = self.filter_new_stock(context, stock_list)
        stock_list = self.filter_highprice_stock(context, stock_list)
        return stock_list

    def get_blue_chip_stocks(self, context, stock_index='000300.XSHG'):
        # <-- 修复点：第二个参数使用 context.current_dt（datetime），避免传非日期类型
        stock_list = get_index_stocks(stock_index, context.current_dt)
        stock_list = self.filter_stocks(context, stock_list)

        roic_stocks = self.filter_roic_stocks(context, stock_list)
        big_stocks = self.filter_big_stocks(context, stock_list)
        bm_stocks = self.filter_bm_stocks(context, stock_list)

        combined_stocks = list(set(roic_stocks + big_stocks + bm_stocks))

        fundamentals_query = get_fundamentals(
            query(valuation.code)
            .filter(valuation.code.in_(combined_stocks))
            .order_by(valuation.market_cap.desc())
            .limit(self.stock_num)
        )
        return list(fundamentals_query.code)

    def filter_roic_stocks(self, context, stock_list):
        yesterday = context.previous_date
        roic_stocks = []
        for stock in stock_list:
            try:
                roic = get_factor_values(stock, 'roic_ttm', end_date=yesterday, count=1)['roic_ttm'].iloc[0, 0]
                if roic > 0.08:
                    roic_stocks.append(stock)
            except Exception:
                continue
        return roic_stocks

    def filter_big_stocks(self, context, stock_list):
        query_result = get_fundamentals(
            query(valuation.code)
            .filter(
                valuation.code.in_(stock_list),
                valuation.pe_ratio_lyr.between(0, 30),
                valuation.ps_ratio.between(0, 8),
                valuation.pcf_ratio < 10,
                indicator.eps > 0.3,
                indicator.roe > 0.1,
                indicator.net_profit_margin > 0.1,
                indicator.gross_profit_margin > 0.3,
                indicator.inc_revenue_year_on_year > 0.25
            )
        )
        return list(query_result.code)

    def filter_bm_stocks(self, context, stock_list):
        query_result = get_fundamentals(
            query(valuation.code)
            .filter(
                valuation.code.in_(stock_list),
                valuation.market_cap.between(100, 900),
                valuation.pb_ratio.between(0, 10),
                valuation.pcf_ratio < 4,
                indicator.eps > 0.3,
                indicator.roe > 0.2,
                indicator.net_profit_margin > 0.1,
                indicator.inc_revenue_year_on_year > 0.2,
                indicator.inc_operation_profit_year_on_year > 0.1
            )
        )
        return list(query_result.code)

    def get_small_cap_stocks(self, context, stock_index='399101.XSHE'):
        # <-- 修复点：第二个参数使用 context.current_dt（datetime）
        stock_list = get_index_stocks(stock_index, context.current_dt)
        stock_list = self.filter_stocks(context, stock_list)

        query_result = get_fundamentals(
            query(valuation.code)
            .filter(
                valuation.code.in_(stock_list),
                indicator.roe > 0.15,
                indicator.roa > 0.10
            )
            .order_by(valuation.market_cap.asc())
            .limit(self.stock_num)
        )
        return list(query_result.code)

    def trade(self, context):
        current_data = get_current_data()
        next_strategy = None
        if self.strategy_type == '偷鸡':
            if self.days_counter < self.counterattack_days:
                self.days_counter += 1
                print("偷鸡模式持续%s天" % self.days_counter)
                next_strategy = '偷鸡'
            else:
                next_strategy = '跑路'
                self.days_counter = 0
        elif self.strategy_type == '摸狗':
            if self.days_counter < self.counterattack_days:
                self.days_counter += 1
                print("跑路模式持续%s天" % self.days_counter)
                next_strategy = '摸狗'
            else:
                next_strategy = '跑路'
                self.days_counter = 0
        else:
            target_etf = self.get_top_momentum_etf(self.ETF_POOL)
            if target_etf == '159915.XSHE':
                next_strategy = '偷鸡'
            elif target_etf == '510180.XSHG':
                next_strategy = '摸狗'
            else:
                next_strategy = '跑路'
            self.days_counter = 0

        if list(context.portfolio.subportfolios[self.subportfolio_index].positions.keys()):
            hold_list_now = list(context.portfolio.subportfolios[self.subportfolio_index].positions.keys())[0]
        else:
            hold_list_now = "0"
        high_etf = self.get_top_momentum_etf(self.ETF_POOL)
        if high_etf in ['510180.XSHG', '159915.XSHE']:
            high_etf = '0'

        if next_strategy == self.strategy_type and self.firsttrade == 1 and high_etf == hold_list_now:
            log.info(f"策略保持不变，继续执行 {self.strategy_type} 策略")
            if self.strategy_type != '跑路':
                log.info("策略持续天数:", self.days_counter)
            return

        self.strategy_type = next_strategy

        if self.strategy_type == '偷鸡':
            self.firsttrade = 1
            self.execute_steal_chicken_strategy(context, current_data)
        elif self.strategy_type == '摸狗':
            self.firsttrade = 1
            self.execute_modog_strategy(context, current_data)
        else:
            self.firsttrade = 1
            self.execute_rout_strategy(context)

    def clear_portfolio(self, context):
        for stock in list(context.portfolio.subportfolios[self.subportfolio_index].positions.keys()):
            self.order_target_value(stock, 0)

    def get_top_momentum_etf(self, etf_pool):
        scores = {etf: self.calculate_momentum(etf) for etf in etf_pool}
        return max(scores, key=scores.get)

    def execute_steal_chicken_strategy(self, context, current_data):
        if self.days_counter == 0:
            log.info("开始偷鸡策略")
            target_stocks = self.get_small_cap_stocks(context)
            self.adjust_portfolio(context, target_stocks)

    def execute_modog_strategy(self, context, current_data):
        if self.days_counter == 0:
            log.info("开始摸狗策略")
            target_stocks = self.get_blue_chip_stocks(context)
            self.adjust_portfolio(context, target_stocks)

    def execute_rout_strategy(self, context=None):
        log.info("开始跑路策略")
        target_etf = self.get_top_momentum_etf(self.ETF_POOL)
        if target_etf in {'510180.XSHG', '159915.XSHE'}:
            target_etf = ''
        if not target_etf:
            log.info("目标 ETF 为空，跳过买入操作")
            return
        for stock in list(context.portfolio.subportfolios[self.subportfolio_index].positions.keys()):
            if stock != target_etf:
                self.order_target_value(stock, 0)
                log.info(f"卖出 {stock}")
        if context.portfolio.subportfolios[self.subportfolio_index].available_cash > 10000:
            log.info(f"买入 {target_etf}，金额: {context.portfolio.subportfolios[self.subportfolio_index].available_cash}")
            self.order_value(target_etf, context.portfolio.subportfolios[self.subportfolio_index].available_cash)
        else:
            log.info("可用现金不足，无法买入目标 ETF")

    def adjust_portfolio(self, context, target_stocks):
        for stock in list(context.portfolio.subportfolios[self.subportfolio_index].positions.keys()):
            if stock not in target_stocks:
                if stock in context.portfolio.subportfolios[self.subportfolio_index].positions:
                    self.close_position(context.portfolio.subportfolios[self.subportfolio_index].positions[stock])
        if not target_stocks:
            return
        cash_per_stock = context.portfolio.subportfolios[self.subportfolio_index].cash / len(target_stocks)
        for stock in target_stocks:
            if stock not in context.portfolio.subportfolios[self.subportfolio_index].positions:
                order_obj = self.order_value(stock, cash_per_stock)
                log.info(f"买入 {stock}，金额: {cash_per_stock}")

    def order_target_value_(self, security, value):
        if value == 0:
            log.debug("Selling out %s" % (security))
        else:
            log.debug("Order %s to value %f" % (security, value))
        return self.order_target_value(security, value)

    def open_position(self, security, value):
        order_obj = self.order_target_value_(security, value)
        if order_obj is not None:
            try:
                if getattr(order_obj, 'filled', 0) > 0:
                    return True
            except Exception:
                return False
        return False

    def close_position(self, position):
        order_obj = self.order_target_value_(position.security, 0)
        if order_obj is not None:
            try:
                if order_obj.status == OrderStatus.held and order_obj.filled == order_obj.amount:
                    return True
            except Exception:
                return False
        return False

    def filter_paused_stock(self, stock_list):
        return [stock for stock in stock_list if not get_current_data()[stock].paused]

    def filter_st_stock(self, stock_list):
        return [stock for stock in stock_list if not get_current_data()[stock].is_st]

    def filter_kcbj_stock(self, stock_list):
        return [stock for stock in stock_list if not (stock[0] in ['4', '8'] or stock[:2] in ['68', '3'])]

    def filter_new_stock(self, context, stock_list):
        out = []
        for stock in stock_list:
            try:
                if (context.previous_date - get_security_info(stock).start_date).days > 375:
                    out.append(stock)
            except Exception:
                out.append(stock)
        return out

    def filter_highprice_stock(self, context, stock_list):
        try:
            last_prices = history(1, '1m', 'close', stock_list)
        except Exception:
            last_prices = None
        out = []
        for stock in stock_list:
            try:
                if last_prices is None:
                    out.append(stock)
                else:
                    if last_prices[stock][-1] < 100:
                        out.append(stock)
            except Exception:
                out.append(stock)
        return out


class ETF_Rotation_Strategy(Strategy):
    """
    封装自：核心资产轮动 提速版 / 安全摸狗 / ETF策略之核心资产轮动 (保留原逻辑)
    将原脚本中的 g.* -> self.*，下单使用基类 order_*（带 pindex）。
    """
    def __init__(self, subportfolio_index, name):
        super(ETF_Rotation_Strategy, self).__init__(subportfolio_index, name)
        # will be initialized in initialize()
        self.etf_pool = None
        self.m_days = None

    def initialize(self, context):
        # 参数迁移自原脚本
        self.etf_pool = [
            # 境外
            "513100.XSHG",  # 纳指ETF
            "513520.XSHG",  # 日经ETF
            "513030.XSHG",  # 德国ETF
            # 商品
            "518880.XSHG",  # 黄金ETF
            "161226.XSHE",  # 白银LOF
            "159985.XSHE",  # 豆粕ETF
            # 债券
            "511090.XSHG",  # 30年国债ETF
            # 国内
            '159525.XSHE',  # 红利低波
            "513130.XSHG",  # 恒生科技
            '159915.XSHE',  # 创业板100（成长股，科技股）
            '159628.XSHE',  # 国证2000（中小盘）
        ]
        self.m_days = 25  # 动量参考天数

    # -------------------------
    # MOM: 动量计算（保留原实现）
    # -------------------------
    def MOM(self, etf):
        import math
        current_data = get_current_data()
        # attribute_history 取最近 self.m_days 个交易日收盘价
        df = attribute_history(etf, self.m_days, '1d', ['close'])
        # 将开盘或最新价追加到序列用于计算（与原脚本行为相同）
        try:
            last_price = current_data[etf].last_price
        except Exception:
            # 若无法从 get_current_data 取得 last_price，退回使用历史序列的最后一天收盘价
            if len(df["close"].values) > 0:
                last_price = df["close"].values[-1]
            else:
                last_price = 0.0
        prices = np.append(df["close"].values, last_price)
        # 对数变换与加权线性回归
        y = np.log(prices)
        n = len(y)
        if n <= 1:
            return -9999.0
        x = np.arange(n)
        weights = np.linspace(1, 2, n)
        # numpy.polyfit 支持 weights 参数
        slope, intercept = np.polyfit(x, y, 1, w=weights)
        # 年化收益（与原脚本一致）
        annualized_returns = math.pow(math.exp(slope), 250) - 1
        residuals = y - (slope * x + intercept)
        weighted_residuals = weights * residuals ** 2
        denom = np.sum(weights * (y - np.mean(y)) ** 2)
        if denom == 0:
            r_squared = 0.0
        else:
            r_squared = 1 - (np.sum(weighted_residuals) / denom)
        score = annualized_returns * r_squared
        return score

    # -------------------------
    # get_rank: 对 etf_pool 评分并返回排序（原逻辑）
    # -------------------------
    def get_rank(self, context, etf_pool):
        score_list = []
        for etf in etf_pool:
            score = self.MOM(etf)
            score_list.append(score)
        df = pd.DataFrame(
            index=etf_pool,
            data={
                'date': [context.current_dt.strftime('%Y-%m-%d')],
                'etf': etf_pool,
                'score': score_list
            }
        )
        df = df.sort_values(by='score', ascending=False)
        print(df)
        # 安全区间筛选（与原脚本一致）
        df = df[(df['score'] > 0) & (df['score'] <= 5)]
        rank_list = list(df.index)
        if len(rank_list) == 0:
            rank_list = []  # 全部小于0时返回空（原脚本逻辑）
        return rank_list

    # -------------------------
    # trade: 主交易逻辑（保留原行为）
    # -------------------------
    def trade(self, context):
        # 获取动量最高的一只ETF
        target_num = 1
        target_list = self.get_rank(context, self.etf_pool)[:target_num]

        # 卖出不在 target_list 的持仓（使用基类下单，带 pindex）
        hold_list = list(context.portfolio.subportfolios[self.subportfolio_index].positions)
        for etf in hold_list:
            if etf not in target_list:
                # 使用封装的 order_target_value（会传 pindex）
                self.order_target_value(etf, 0)
                print('卖出' + str(etf))
            else:
                print('继续持有' + str(etf))

        # 买入：若持仓少于 target_num，则等额买入目标 ETF
        hold_list = list(context.portfolio.subportfolios[self.subportfolio_index].positions)
        if len(hold_list) < target_num:
            avail = context.portfolio.subportfolios[self.subportfolio_index].available_cash
            denom = (target_num - len(hold_list)) if (target_num - len(hold_list)) > 0 else 1
            value = avail / denom
            for etf in target_list:
                # 若当前持仓数量为0 则下单
                pos = context.portfolio.subportfolios[self.subportfolio_index].positions.get(etf)
                total_amount = pos.total_amount if pos is not None else 0
                if total_amount == 0:
                    self.order_target_value(etf, value)
                    print('买入' + str(etf))