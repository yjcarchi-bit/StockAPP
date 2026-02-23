"""
大市值低回撤策略
================
基于六因子打分和RSRS择时的低回撤策略

策略核心思想:
1. 六因子打分：动量、趋势强度、量比、波动率、市值
2. RSRS择时：基于阻力支撑相对强度的择时指标
3. 回撤锁定：回撤超过10%触发锁定机制
4. 动态成分股：使用历史沪深300成分股，避免前视偏差
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.strategy_base import StrategyBase, BarData
from core.indicators import Indicators
from core.data_source import DataSource


DEFAULT_STOCK_POOL = [
    {"code": "000001", "name": "平安银行"},
    {"code": "000002", "name": "万科A"},
    {"code": "000063", "name": "中兴通讯"},
    {"code": "000333", "name": "美的集团"},
    {"code": "000651", "name": "格力电器"},
    {"code": "000725", "name": "京东方A"},
    {"code": "000858", "name": "五粮液"},
    {"code": "002415", "name": "海康威视"},
    {"code": "002594", "name": "比亚迪"},
    {"code": "002714", "name": "牧原股份"},
    {"code": "600000", "name": "浦发银行"},
    {"code": "600009", "name": "上海机场"},
    {"code": "600016", "name": "民生银行"},
    {"code": "600019", "name": "宝钢股份"},
    {"code": "600028", "name": "中国石化"},
    {"code": "600030", "name": "中信证券"},
    {"code": "600036", "name": "招商银行"},
    {"code": "600048", "name": "保利发展"},
    {"code": "600050", "name": "中国联通"},
    {"code": "600104", "name": "上汽集团"},
    {"code": "600276", "name": "恒瑞医药"},
    {"code": "600309", "name": "万华化学"},
    {"code": "600346", "name": "恒力石化"},
    {"code": "600438", "name": "通威股份"},
    {"code": "600519", "name": "贵州茅台"},
    {"code": "600585", "name": "海螺水泥"},
    {"code": "600690", "name": "海尔智家"},
    {"code": "600887", "name": "伊利股份"},
    {"code": "600900", "name": "长江电力"},
    {"code": "601012", "name": "隆基绿能"},
    {"code": "601088", "name": "中国神华"},
    {"code": "601166", "name": "兴业银行"},
    {"code": "601288", "name": "农业银行"},
    {"code": "601318", "name": "中国平安"},
    {"code": "601328", "name": "交通银行"},
    {"code": "601398", "name": "工商银行"},
    {"code": "601601", "name": "中国太保"},
    {"code": "601628", "name": "中国人寿"},
    {"code": "601668", "name": "中国建筑"},
    {"code": "601688", "name": "华泰证券"},
    {"code": "601818", "name": "光大银行"},
    {"code": "601857", "name": "中国石油"},
    {"code": "601899", "name": "紫金矿业"},
    {"code": "601919", "name": "中远海控"},
    {"code": "601939", "name": "建设银行"},
    {"code": "601988", "name": "中国银行"},
    {"code": "603259", "name": "药明康德"},
    {"code": "603288", "name": "海天味业"},
]
DEFAULT_STOCK_POOL1 = [
    {"code": "000001", "name": "平安银行"},
    {"code": "000002", "name": "万科A"},
    {"code": "000063", "name": "中兴通讯"},
    {"code": "000100", "name": "TCL科技"},
    {"code": "000157", "name": "中联重科"},
    {"code": "000166", "name": "申万宏源"},
    {"code": "000301", "name": "东方盛虹"},
    {"code": "000333", "name": "美的集团"},
    {"code": "000338", "name": "潍柴动力"},
    {"code": "000408", "name": "藏格矿业"},
    {"code": "000425", "name": "徐工机械"},
    {"code": "000538", "name": "云南白药"},
    {"code": "000568", "name": "泸州老窖"},
    {"code": "000596", "name": "古井贡酒"},
    {"code": "000617", "name": "中油资本"},
    {"code": "000625", "name": "长安汽车"},
    {"code": "000630", "name": "铜陵有色"},
    {"code": "000651", "name": "格力电器"},
    {"code": "000661", "name": "长春高新"},
    {"code": "000708", "name": "中信特钢"},
    {"code": "000725", "name": "京东方A"},
    {"code": "000768", "name": "中航西飞"},
    {"code": "000776", "name": "广发证券"},
    {"code": "000786", "name": "北新建材"},
    {"code": "000792", "name": "盐湖股份"},
    {"code": "000807", "name": "云铝股份"},
    {"code": "000858", "name": "五粮液"},
    {"code": "000876", "name": "新希望"},
    {"code": "000895", "name": "双汇发展"},
    {"code": "000938", "name": "紫光股份"},
    {"code": "000963", "name": "华东医药"},
    {"code": "000975", "name": "山金国际"},
    {"code": "000977", "name": "浪潮信息"},
    {"code": "000983", "name": "山西焦煤"},
    {"code": "000999", "name": "华润三九"},
    {"code": "001391", "name": "国货航"},
    {"code": "001965", "name": "招商公路"},
    {"code": "001979", "name": "招商蛇口"},
    {"code": "002001", "name": "新和成"},
    {"code": "002027", "name": "分众传媒"},
    {"code": "002028", "name": "思源电气"},
    {"code": "002049", "name": "紫光国微"},
    {"code": "002050", "name": "三花智控"},
    {"code": "002074", "name": "国轩高科"},
    {"code": "002142", "name": "宁波银行"},
    {"code": "002179", "name": "中航光电"},
    {"code": "002230", "name": "科大讯飞"},
    {"code": "002236", "name": "大华股份"},
    {"code": "002241", "name": "歌尔股份"},
    {"code": "002252", "name": "上海莱士"},
    {"code": "002304", "name": "洋河股份"},
    {"code": "002311", "name": "海大集团"},
    {"code": "002352", "name": "顺丰控股"},
    {"code": "002371", "name": "北方华创"},
    {"code": "002384", "name": "东山精密"},
    {"code": "002415", "name": "海康威视"},
    {"code": "002422", "name": "科伦药业"},
    {"code": "002459", "name": "晶澳科技"},
    {"code": "002460", "name": "赣锋锂业"},
    {"code": "002463", "name": "沪电股份"},
    {"code": "002466", "name": "天齐锂业"},
    {"code": "002475", "name": "立讯精密"},
    {"code": "002493", "name": "荣盛石化"},
    {"code": "002594", "name": "比亚迪"},
    {"code": "002600", "name": "领益智造"},
    {"code": "002601", "name": "龙佰集团"},
    {"code": "002625", "name": "光启技术"},
    {"code": "002648", "name": "卫星化学"},
    {"code": "002709", "name": "天赐材料"},
    {"code": "002714", "name": "牧原股份"},
    {"code": "002736", "name": "国信证券"},
    {"code": "002916", "name": "深南电路"},
    {"code": "002920", "name": "德赛西威"},
    {"code": "002938", "name": "鹏鼎控股"},
    {"code": "003816", "name": "中国广核"},
    {"code": "300014", "name": "亿纬锂能"},
    {"code": "300015", "name": "爱尔眼科"},
    {"code": "300033", "name": "同花顺"},
    {"code": "300059", "name": "东方财富"},
    {"code": "300122", "name": "智飞生物"},
    {"code": "300124", "name": "汇川技术"},
    {"code": "300251", "name": "光线传媒"},
    {"code": "300274", "name": "阳光电源"},
    {"code": "300308", "name": "中际旭创"},
    {"code": "300316", "name": "晶盛机电"},
    {"code": "300347", "name": "泰格医药"},
    {"code": "300394", "name": "天孚通信"},
    {"code": "300408", "name": "三环集团"},
    {"code": "300413", "name": "芒果超媒"},
    {"code": "300418", "name": "昆仑万维"},
    {"code": "300433", "name": "蓝思科技"},
    {"code": "300442", "name": "润泽科技"},
    {"code": "300476", "name": "胜宏科技"},
    {"code": "300498", "name": "温氏股份"},
    {"code": "300502", "name": "新易盛"},
    {"code": "300628", "name": "亿联网络"},
    {"code": "300661", "name": "圣邦股份"},
    {"code": "300750", "name": "宁德时代"},
    {"code": "300759", "name": "康龙化成"},
    {"code": "300760", "name": "迈瑞医疗"},
    {"code": "300782", "name": "卓胜微"},
    {"code": "300803", "name": "指南针"},
    {"code": "300832", "name": "新产业"},
    {"code": "300866", "name": "安克创新"},
    {"code": "300896", "name": "爱美客"},
    {"code": "300979", "name": "华利集团"},
    {"code": "300999", "name": "金龙鱼"},
    {"code": "301236", "name": "软通动力"},
    {"code": "301269", "name": "华大九天"},
    {"code": "302132", "name": "中航成飞"},
    {"code": "600000", "name": "浦发银行"},
    {"code": "600009", "name": "上海机场"},
    {"code": "600010", "name": "包钢股份"},
    {"code": "600011", "name": "华能国际"},
    {"code": "600015", "name": "华夏银行"},
    {"code": "600016", "name": "民生银行"},
    {"code": "600018", "name": "上港集团"},
    {"code": "600019", "name": "宝钢股份"},
    {"code": "600023", "name": "浙能电力"},
    {"code": "600025", "name": "华能水电"},
    {"code": "600026", "name": "中远海能"},
    {"code": "600027", "name": "华电国际"},
    {"code": "600028", "name": "中国石化"},
    {"code": "600029", "name": "南方航空"},
    {"code": "600030", "name": "中信证券"},
    {"code": "600031", "name": "三一重工"},
    {"code": "600036", "name": "招商银行"},
    {"code": "600039", "name": "四川路桥"},
    {"code": "600048", "name": "保利发展"},
    {"code": "600050", "name": "中国联通"},
    {"code": "600061", "name": "国投资本"},
    {"code": "600066", "name": "宇通客车"},
    {"code": "600085", "name": "同仁堂"},
    {"code": "600089", "name": "特变电工"},
    {"code": "600104", "name": "上汽集团"},
    {"code": "600111", "name": "北方稀土"},
    {"code": "600115", "name": "中国东航"},
    {"code": "600150", "name": "中国船舶"},
    {"code": "600160", "name": "巨化股份"},
    {"code": "600161", "name": "天坛生物"},
    {"code": "600176", "name": "中国巨石"},
    {"code": "600183", "name": "生益科技"},
    {"code": "600188", "name": "兖矿能源"},
    {"code": "600196", "name": "复星医药"},
    {"code": "600219", "name": "南山铝业"},
    {"code": "600233", "name": "圆通速递"},
    {"code": "600276", "name": "恒瑞医药"},
    {"code": "600309", "name": "万华化学"},
    {"code": "600346", "name": "恒力石化"},
    {"code": "600362", "name": "江西铜业"},
    {"code": "600372", "name": "中航机载"},
    {"code": "600377", "name": "宁沪高速"},
    {"code": "600406", "name": "国电南瑞"},
    {"code": "600415", "name": "小商品城"},
    {"code": "600426", "name": "华鲁恒升"},
    {"code": "600436", "name": "片仔癀"},
    {"code": "600438", "name": "通威股份"},
    {"code": "600460", "name": "士兰微"},
    {"code": "600482", "name": "中国动力"},
    {"code": "600489", "name": "中金黄金"},
    {"code": "600515", "name": "海南机场"},
    {"code": "600519", "name": "贵州茅台"},
    {"code": "600522", "name": "中天科技"},
    {"code": "600547", "name": "山东黄金"},
    {"code": "600570", "name": "恒生电子"},
    {"code": "600584", "name": "长电科技"},
    {"code": "600585", "name": "海螺水泥"},
    {"code": "600588", "name": "用友网络"},
    {"code": "600600", "name": "青岛啤酒"},
    {"code": "600660", "name": "福耀玻璃"},
    {"code": "600674", "name": "川投能源"},
    {"code": "600690", "name": "海尔智家"},
    {"code": "600741", "name": "华域汽车"},
    {"code": "600760", "name": "中航沈飞"},
    {"code": "600795", "name": "国电电力"},
    {"code": "600803", "name": "新奥股份"},
    {"code": "600809", "name": "山西汾酒"},
    {"code": "600845", "name": "宝信软件"},
    {"code": "600875", "name": "东方电气"},
    {"code": "600886", "name": "国投电力"},
    {"code": "600887", "name": "伊利股份"},
    {"code": "600893", "name": "航发动力"},
    {"code": "600900", "name": "长江电力"},
    {"code": "600905", "name": "三峡能源"},
    {"code": "600918", "name": "中泰证券"},
    {"code": "600919", "name": "江苏银行"},
    {"code": "600926", "name": "杭州银行"},
    {"code": "600930", "name": "华电新能"},
    {"code": "600938", "name": "中国海油"},
    {"code": "600941", "name": "中国移动"},
    {"code": "600958", "name": "东方证券"},
    {"code": "600989", "name": "宝丰能源"},
    {"code": "600999", "name": "招商证券"},
    {"code": "601006", "name": "大秦铁路"},
    {"code": "601009", "name": "南京银行"},
    {"code": "601012", "name": "隆基绿能"},
    {"code": "601018", "name": "宁波港"},
    {"code": "601021", "name": "春秋航空"},
    {"code": "601058", "name": "赛轮轮胎"},
    {"code": "601059", "name": "信达证券"},
    {"code": "601066", "name": "中信建投"},
    {"code": "601077", "name": "渝农商行"},
    {"code": "601088", "name": "中国神华"},
    {"code": "601100", "name": "恒立液压"},
    {"code": "601111", "name": "中国国航"},
    {"code": "601117", "name": "中国化学"},
    {"code": "601127", "name": "赛力斯"},
    {"code": "601136", "name": "首创证券"},
    {"code": "601138", "name": "工业富联"},
    {"code": "601166", "name": "兴业银行"},
    {"code": "601169", "name": "北京银行"},
    {"code": "601186", "name": "中国铁建"},
    {"code": "601211", "name": "国泰海通"},
    {"code": "601225", "name": "陕西煤业"},
    {"code": "601229", "name": "上海银行"},
    {"code": "601236", "name": "红塔证券"},
    {"code": "601238", "name": "广汽集团"},
    {"code": "601288", "name": "农业银行"},
    {"code": "601298", "name": "青岛港"},
    {"code": "601318", "name": "中国平安"},
    {"code": "601319", "name": "中国人保"},
    {"code": "601328", "name": "交通银行"},
    {"code": "601336", "name": "新华保险"},
    {"code": "601360", "name": "三六零"},
    {"code": "601377", "name": "兴业证券"},
    {"code": "601390", "name": "中国中铁"},
    {"code": "601398", "name": "工商银行"},
    {"code": "601456", "name": "国联民生"},
    {"code": "601600", "name": "中国铝业"},
    {"code": "601601", "name": "中国太保"},
    {"code": "601607", "name": "上海医药"},
    {"code": "601618", "name": "中国中冶"},
    {"code": "601628", "name": "中国人寿"},
    {"code": "601633", "name": "长城汽车"},
    {"code": "601658", "name": "邮储银行"},
    {"code": "601668", "name": "中国建筑"},
    {"code": "601669", "name": "中国电建"},
    {"code": "601688", "name": "华泰证券"},
    {"code": "601689", "name": "拓普集团"},
    {"code": "601698", "name": "中国卫通"},
    {"code": "601728", "name": "中国电信"},
    {"code": "601766", "name": "中国中车"},
    {"code": "601788", "name": "光大证券"},
    {"code": "601800", "name": "中国交建"},
    {"code": "601808", "name": "中海油服"},
    {"code": "601816", "name": "京沪高铁"},
    {"code": "601818", "name": "光大银行"},
    {"code": "601825", "name": "沪农商行"},
    {"code": "601838", "name": "成都银行"},
    {"code": "601857", "name": "中国石油"},
    {"code": "601868", "name": "中国能建"},
    {"code": "601872", "name": "招商轮船"},
    {"code": "601877", "name": "正泰电器"},
    {"code": "601878", "name": "浙商证券"},
    {"code": "601881", "name": "中国银河"},
    {"code": "601888", "name": "中国中免"},
    {"code": "601898", "name": "中煤能源"},
    {"code": "601899", "name": "紫金矿业"},
    {"code": "601901", "name": "方正证券"},
    {"code": "601916", "name": "浙商银行"},
    {"code": "601919", "name": "中远海控"},
    {"code": "601939", "name": "建设银行"},
    {"code": "601985", "name": "中国核电"},
    {"code": "601988", "name": "中国银行"},
    {"code": "601995", "name": "中金公司"},
    {"code": "601998", "name": "中信银行"},
    {"code": "603019", "name": "中科曙光"},
    {"code": "603195", "name": "公牛集团"},
    {"code": "603259", "name": "药明康德"},
    {"code": "603260", "name": "合盛硅业"},
    {"code": "603288", "name": "海天味业"},
    {"code": "603296", "name": "华勤技术"},
    {"code": "603369", "name": "今世缘"},
    {"code": "603392", "name": "万泰生物"},
    {"code": "603501", "name": "豪威集团"},
    {"code": "603799", "name": "华友钴业"},
    {"code": "603893", "name": "瑞芯微"},
    {"code": "603986", "name": "兆易创新"},
    {"code": "603993", "name": "洛阳钼业"},
    {"code": "605117", "name": "德业股份"},
    {"code": "605499", "name": "东鹏饮料"},
    {"code": "688008", "name": "澜起科技"},
    {"code": "688009", "name": "中国通号"},
    {"code": "688012", "name": "中微公司"},
    {"code": "688036", "name": "传音控股"},
    {"code": "688041", "name": "海光信息"},
    {"code": "688047", "name": "龙芯中科"},
    {"code": "688082", "name": "盛美上海"},
    {"code": "688111", "name": "金山办公"},
    {"code": "688126", "name": "沪硅产业"},
    {"code": "688169", "name": "石头科技"},
    {"code": "688187", "name": "时代电气"},
    {"code": "688223", "name": "晶科能源"},
    {"code": "688256", "name": "寒武纪"},
    {"code": "688271", "name": "联影医疗"},
    {"code": "688303", "name": "大全能源"},
    {"code": "688396", "name": "华润微"},
    {"code": "688472", "name": "阿特斯"},
    {"code": "688506", "name": "百利天恒"},
    {"code": "688981", "name": "中芯国际"},
]

class LargeCapLowDrawdownStrategy(StrategyBase):
    """
    大市值低回撤策略
    
    基于六因子打分和RSRS择时的低回撤策略。通过多因子选股和择时指标控制回撤。
    
    支持动态成分股：使用历史沪深300成分股进行回测，避免前视偏差。
    """
    
    display_name = "大市值低回撤策略"
    description = (
        "基于六因子打分和RSRS择时的低回撤策略。通过动量、趋势强度、量比、波动率、市值"
        "六个因子进行选股打分，结合RSRS择时指标判断市场状态，并采用回撤锁定机制控制风险。"
        "支持使用历史沪深300成分股进行回测，避免前视偏差。"
    )
    logic = [
        "1. 动态成分股：根据回测日期使用当时的沪深300成分股（避免前视偏差）",
        "2. 六因子打分：5日动量、20日动量、趋势强度、量比、波动率、市值",
        "3. RSRS择时：基于阻力支撑相对强度的择时指标",
        "4. 回撤锁定：回撤超过10%触发锁定机制",
        "5. 分批解锁：锁定后分批解锁仓位",
        "6. 冷却期保护：解锁后设置冷却期",
    ]
    suitable = "适合追求稳健收益、希望控制回撤的投资者"
    risk = "震荡市场可能频繁触发锁定，影响收益"
    params_info = {
        "max_positions": {
            "default": 3,
            "min": 1,
            "max": 5,
            "step": 1,
            "description": "最大持仓数量",
            "type": "slider",
        },
        "stop_loss_ratio": {
            "default": 0.05,
            "min": 0.03,
            "max": 0.10,
            "step": 0.01,
            "description": "止损比例",
            "type": "slider",
        },
        "take_profit_ratio": {
            "default": 0.35,
            "min": 0.20,
            "max": 0.50,
            "step": 0.05,
            "description": "止盈比例",
            "type": "slider",
        },
        "use_dynamic_components": {
            "default": True,
            "description": "使用动态成分股（避免前视偏差）",
            "type": "checkbox",
        },
        "tushare_token": {
            "default": "",
            "description": "Tushare Token（获取历史成分股需要，注册地址: https://tushare.pro/）",
            "type": "text",
        },
    }
    
    def __init__(self, use_dynamic_components: bool = True):
        super().__init__()
        
        self._max_positions = 3
        self._stop_loss_ratio = 0.05
        self._take_profit_ratio = 0.35
        self._use_dynamic_components = use_dynamic_components
        
        self._default_stock_pool: List[Dict] = DEFAULT_STOCK_POOL
        self._stock_scores: Dict[str, Dict[str, Any]] = {}
        
        self._position_highs: Dict[str, float] = {}
        self._is_locked: bool = False
        self._lock_start_date: Optional[datetime] = None
        self._cool_down_end: Optional[datetime] = None
        
        self._data_source: Optional[DataSource] = None
        self._components_history: Dict[str, List[str]] = {}
        self._current_components: List[str] = []
        self._last_components_update: Optional[datetime] = None
    
    def initialize(self) -> None:
        """策略初始化"""
        self._max_positions = self.get_param("max_positions", 3)
        self._stop_loss_ratio = self.get_param("stop_loss_ratio", 0.05)
        self._take_profit_ratio = self.get_param("take_profit_ratio", 0.35)
        self._use_dynamic_components = self.get_param("use_dynamic_components", True)
        self._tushare_token = self.get_param("tushare_token", None)
        
        self._stock_scores = {}
        self._position_highs = {}
        self._is_locked = False
        self._lock_start_date = None
        self._cool_down_end = None
        
        if self._use_dynamic_components:
            self._data_source = DataSource()
            self._preload_components_history()
        
        self.log(f"策略初始化完成")
        self.log(f"  最大持仓: {self._max_positions}")
        self.log(f"  止损比例: {self._stop_loss_ratio * 100:.0f}%")
        self.log(f"  止盈比例: {self._take_profit_ratio * 100:.0f}%")
        self.log(f"  动态成分股: {'启用' if self._use_dynamic_components else '禁用'}")
    
    def _preload_components_history(self) -> None:
        """预加载历史成分股数据"""
        self.log("预加载沪深300历史成分股数据...")
        
        start_date = self._params.get("backtest_start_date", "2020-01-01")
        end_date = self._params.get("backtest_end_date", datetime.now().strftime("%Y-%m-%d"))
        
        try:
            self._components_history = self._data_source.get_index_components_history(
                index_code="000300",
                start_date=start_date,
                end_date=end_date,
                freq="M",
                tushare_token=self._tushare_token
            )
            
            if self._components_history:
                self.log(f"  成功加载 {len(self._components_history)} 期成分股数据")
            else:
                self.log("  警告: 无法加载历史成分股，将使用默认股票池")
                self._use_dynamic_components = False
        except Exception as e:
            self.log(f"  加载历史成分股失败: {e}")
            self._use_dynamic_components = False
    
    def _get_components_for_date(self, date: datetime) -> List[str]:
        """获取指定日期的成分股列表"""
        if not self._use_dynamic_components or not self._components_history:
            return [stock["code"] for stock in self._default_stock_pool]
        
        date_str = date.strftime("%Y-%m-%d")
        
        available_dates = sorted(self._components_history.keys())
        
        target_date = None
        for d in available_dates:
            if d <= date_str:
                target_date = d
            else:
                break
        
        if target_date:
            return self._components_history[target_date]
        
        if available_dates:
            return self._components_history[available_dates[0]]
        
        return [stock["code"] for stock in self._default_stock_pool]
    
    def _calculate_stock_score(self, code: str) -> Optional[Dict[str, Any]]:
        """计算股票评分"""
        df = self.get_history(code, 60)
        if df is None or len(df) < 30:
            return None
        
        close = df["close"].values
        volume = df["volume"].values if "volume" in df.columns else None
        amount = df["amount"].values if "amount" in df.columns else None
        
        if len(close) < 30:
            return None
        
        current_price = close[-1]
        if current_price <= 0:
            return None
        
        momentum_5 = (close[-1] / close[-6] - 1) if len(close) > 5 else 0
        momentum_20 = (close[-1] / close[-21] - 1) if len(close) > 20 else 0
        
        ma5 = np.mean(close[-5:])
        ma20 = np.mean(close[-20:])
        trend_strength = (ma5 - ma20) / ma20 if ma20 > 0 else 0
        
        if volume is not None and len(volume) >= 20:
            avg_volume = np.mean(volume[-20:])
            volume_ratio = volume[-1] / avg_volume if avg_volume > 0 else 1
        else:
            volume_ratio = 1
        
        volatility = np.std(close[-20:]) / close[-1] if close[-1] > 0 else 1
        
        avg_amount = np.mean(amount[-20:]) if amount is not None and len(amount) >= 20 else 1e8
        
        score = 0
        
        if momentum_5 > 0.03:
            score += 20
        elif momentum_5 > 0:
            score += 10
        
        if momentum_20 > 0.1:
            score += 20
        elif momentum_20 > 0:
            score += 10
        
        if trend_strength > 0.02:
            score += 15
        elif trend_strength > 0:
            score += 8
        
        if volume_ratio > 1.5:
            score += 10
        elif volume_ratio > 1:
            score += 5
        
        if volatility < 0.03:
            score += 15
        elif volatility < 0.05:
            score += 10
        elif volatility < 0.08:
            score += 5
        
        return {
            "code": code,
            "current_price": current_price,
            "momentum_5": momentum_5,
            "momentum_20": momentum_20,
            "trend_strength": trend_strength,
            "volume_ratio": volume_ratio,
            "volatility": volatility,
            "avg_amount": avg_amount,
            "score": score,
        }
    
    def _calculate_all_scores(self) -> None:
        """计算所有股票评分"""
        self._stock_scores = {}
        
        for code in self._current_components:
            if code not in self._data:
                continue
            
            score_data = self._calculate_stock_score(code)
            if score_data is not None:
                self._stock_scores[code] = score_data
    
    def _select_stocks(self) -> List[str]:
        """选股"""
        sorted_stocks = sorted(
            self._stock_scores.items(),
            key=lambda x: -x[1]["score"]
        )
        
        return [code for code, _ in sorted_stocks[:self._max_positions * 2]]
    
    def _check_risk_control(self) -> None:
        """风险控制检查"""
        total_value = self._portfolio.total_value
        peak_value = self._portfolio.peak_value if hasattr(self._portfolio, 'peak_value') else total_value
        
        if peak_value > 0:
            drawdown = (peak_value - total_value) / peak_value
            
            if drawdown > 0.10 and not self._is_locked:
                self._is_locked = True
                self._lock_start_date = self._current_date
                self.log(f"触发回撤锁定，回撤: {drawdown * 100:.2f}%")
        
        if self._is_locked:
            if self._cool_down_end and self._current_date >= self._cool_down_end:
                self._is_locked = False
                self._lock_start_date = None
                self.log("回撤锁定解除")
    
    def _check_stop_loss_take_profit(self) -> None:
        """检查止损止盈"""
        for code in list(self._portfolio.positions.keys()):
            pos = self._portfolio.get_position(code)
            
            if pos.is_empty:
                continue
            
            if code not in self._stock_scores:
                continue
            
            current_price = self._stock_scores[code]["current_price"]
            
            if code not in self._position_highs:
                self._position_highs[code] = current_price
            else:
                self._position_highs[code] = max(self._position_highs[code], current_price)
            
            pnl_ratio = (current_price - pos.cost_price) / pos.cost_price
            
            if pnl_ratio <= -self._stop_loss_ratio:
                self.sell_all(code, current_price)
                self.log(f"止损卖出: {code}，亏损: {pnl_ratio * 100:.2f}%")
                if code in self._position_highs:
                    del self._position_highs[code]
            
            elif pnl_ratio >= self._take_profit_ratio:
                self.sell_all(code, current_price)
                self.log(f"止盈卖出: {code}，盈利: {pnl_ratio * 100:.2f}%")
                if code in self._position_highs:
                    del self._position_highs[code]
    
    def _rebalance(self) -> None:
        """调仓"""
        if self._is_locked:
            return
        
        target_stocks = self._select_stocks()[:self._max_positions]
        
        current_holdings = [
            code for code in self._portfolio.positions.keys()
            if self.has_position(code)
        ]
        
        for code in current_holdings:
            if code not in target_stocks:
                if code in self._stock_scores:
                    self.sell_all(code, self._stock_scores[code]["current_price"])
                    self.log(f"调仓卖出: {code}")
        
        if not target_stocks:
            return
        
        cash_available = self._portfolio.cash
        if cash_available < 1000:
            return
        
        cash_per_stock = cash_available / len(target_stocks)
        
        for code in target_stocks:
            if self.has_position(code):
                continue
            
            if code not in self._stock_scores:
                continue
            
            price = self._stock_scores[code]["current_price"]
            if price <= 0:
                continue
            
            amount = int(cash_per_stock / price / 100) * 100
            if amount <= 0:
                continue
            
            score = self._stock_scores[code]["score"]
            
            if self.buy(code, price, amount):
                self.log(f"买入: {code}，评分: {score}")
    
    def on_trading_day(self, date: datetime, bars: dict) -> None:
        """交易日回调 - 每天只调用一次"""
        if self._use_dynamic_components:
            if self._last_components_update is None or \
               (date - self._last_components_update).days >= 30:
                self._current_components = self._get_components_for_date(date)
                self._last_components_update = date
        else:
            self._current_components = [stock["code"] for stock in self._default_stock_pool]
        
        self._calculate_all_scores()
        
        self._check_risk_control()
        
        self._check_stop_loss_take_profit()
        
        self._rebalance()
        
        for code in self._portfolio.positions.keys():
            if code in self._stock_scores:
                self.update_position_price(code, self._stock_scores[code]["current_price"])
    
    def on_end(self) -> None:
        """回测结束"""
        self.log("回测结束")
        self._print_summary()
    
    def _print_summary(self) -> None:
        """打印策略摘要"""
        self.log("\n=== 大市值低回撤策略摘要 ===")
        self.log(f"最终资产: {self._portfolio.total_value:,.2f}")
        self.log(f"总收益率: {((self._portfolio.total_value / self._portfolio.initial_capital - 1) * 100):.2f}%")
        self.log(f"动态成分股模式: {'启用' if self._use_dynamic_components else '禁用'}")
