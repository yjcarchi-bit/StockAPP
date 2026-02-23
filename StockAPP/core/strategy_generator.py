"""
策略生成器模块
=============
智能生成量化交易策略代码

功能:
1. 自然语言解析：理解用户的策略描述
2. 策略模板匹配：匹配最适合的策略模板
3. 参数提取：从描述中提取策略参数
4. 代码生成：生成可运行的策略代码
5. 策略验证：验证生成的策略代码

使用示例:
    >>> from core.strategy_generator import StrategyGenerator
    >>> generator = StrategyGenerator()
    >>> 
    >>> # 生成策略
    >>> result = generator.generate("我想做一个双均线策略，快线20日，慢线60日")
    >>> print(result.code)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple
import re
import ast
import textwrap

from .strategy_base import StrategyCategory


class StrategyType(Enum):
    """策略类型"""
    TREND_FOLLOWING = "趋势跟踪"
    MEAN_REVERSION = "均值回归"
    MOMENTUM = "动量策略"
    BREAKOUT = "突破策略"
    ROTATION = "轮动策略"
    ARBITRAGE = "套利策略"
    MULTI_FACTOR = "多因子策略"
    CUSTOM = "自定义策略"


class SignalType(Enum):
    """信号类型"""
    ENTRY = "入场信号"
    EXIT = "出场信号"
    STOP_LOSS = "止损信号"
    TAKE_PROFIT = "止盈信号"
    REBALANCE = "调仓信号"


@dataclass
class StrategyParameter:
    """策略参数"""
    name: str
    display_name: str
    default_value: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    description: str = ""
    param_type: str = "int"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "default_value": self.default_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "step": self.step,
            "description": self.description,
            "param_type": self.param_type,
        }


@dataclass
class StrategyLogic:
    """策略逻辑"""
    entry_conditions: List[str] = field(default_factory=list)
    exit_conditions: List[str] = field(default_factory=list)
    stop_loss: Optional[str] = None
    take_profit: Optional[str] = None
    position_sizing: str = "固定比例"
    rebalance_frequency: str = "每日"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_conditions": self.entry_conditions,
            "exit_conditions": self.exit_conditions,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_sizing": self.position_sizing,
            "rebalance_frequency": self.rebalance_frequency,
        }


@dataclass
class GeneratedStrategy:
    """生成的策略"""
    name: str
    class_name: str
    category: StrategyCategory
    strategy_type: StrategyType
    description: str
    code: str
    parameters: List[StrategyParameter] = field(default_factory=list)
    logic: StrategyLogic = None
    suitable_market: str = ""
    risk_warning: str = ""
    dependencies: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "class_name": self.class_name,
            "category": self.category.value,
            "strategy_type": self.strategy_type.value,
            "description": self.description,
            "code": self.code,
            "parameters": [p.to_dict() for p in self.parameters],
            "logic": self.logic.to_dict() if self.logic else None,
            "suitable_market": self.suitable_market,
            "risk_warning": self.risk_warning,
            "dependencies": self.dependencies,
            "validation_errors": self.validation_errors,
        }


class StrategyGenerator:
    """
    策略生成器
    
    根据自然语言描述生成量化策略代码
    
    Example:
        >>> generator = StrategyGenerator()
        >>> result = generator.generate("做一个RSI策略，超卖30买入，超买70卖出")
        >>> print(result.code)
    """
    
    def __init__(self):
        self._keyword_mappings = self._init_keyword_mappings()
        self._strategy_templates = self._init_strategy_templates()
        self._indicator_patterns = self._init_indicator_patterns()
    
    def _init_keyword_mappings(self) -> Dict[str, str]:
        """初始化关键词映射"""
        return {
            "均线": "ma",
            "移动平均": "ma",
            "ma": "ma",
            "双均线": "dual_ma",
            "金叉": "golden_cross",
            "死叉": "death_cross",
            "rsi": "rsi",
            "相对强弱": "rsi",
            "超买": "overbought",
            "超卖": "oversold",
            "macd": "macd",
            "布林": "bollinger",
            "boll": "bollinger",
            "bollinger": "bollinger",
            "kdj": "kdj",
            "动量": "momentum",
            "突破": "breakout",
            "轮动": "rotation",
            "etf": "etf",
            "趋势": "trend",
            "反转": "reversal",
            "震荡": "oscillation",
            "网格": "grid",
            "止损": "stop_loss",
            "止盈": "take_profit",
            "仓位": "position",
            "快线": "fast_period",
            "慢线": "slow_period",
            "周期": "period",
            "上轨": "upper_band",
            "下轨": "lower_band",
            "中轨": "middle_band",
        }
    
    def _init_strategy_templates(self) -> Dict[str, Dict[str, Any]]:
        """初始化策略模板"""
        return {
            "dual_ma": {
                "name": "双均线策略",
                "type": StrategyType.TREND_FOLLOWING,
                "category": StrategyCategory.SIMPLE,
                "keywords": ["均线", "双均线", "金叉", "死叉", "ma", "移动平均"],
                "parameters": [
                    StrategyParameter("fast_period", "快线周期", 20, 5, 60, 1, "快速移动平均线周期"),
                    StrategyParameter("slow_period", "慢线周期", 60, 20, 120, 1, "慢速移动平均线周期"),
                ],
                "logic": StrategyLogic(
                    entry_conditions=["快线上穿慢线"],
                    exit_conditions=["快线下穿慢线"],
                    position_sizing="固定比例",
                ),
                "suitable": "适合趋势明显的市场",
                "risk": "震荡市场可能频繁止损",
            },
            "rsi": {
                "name": "RSI策略",
                "type": StrategyType.MEAN_REVERSION,
                "category": StrategyCategory.SIMPLE,
                "keywords": ["rsi", "相对强弱", "超买", "超卖"],
                "parameters": [
                    StrategyParameter("period", "RSI周期", 14, 5, 30, 1, "RSI计算周期"),
                    StrategyParameter("oversold", "超卖阈值", 30, 20, 40, 1, "超卖线"),
                    StrategyParameter("overbought", "超买阈值", 70, 60, 80, 1, "超买线"),
                ],
                "logic": StrategyLogic(
                    entry_conditions=["RSI低于超卖线"],
                    exit_conditions=["RSI高于超买线"],
                    position_sizing="固定比例",
                ),
                "suitable": "适合震荡市场",
                "risk": "趋势市场可能逆势操作",
            },
            "macd": {
                "name": "MACD策略",
                "type": StrategyType.TREND_FOLLOWING,
                "category": StrategyCategory.SIMPLE,
                "keywords": ["macd", "异同移动平均", "dif", "dea"],
                "parameters": [
                    StrategyParameter("fast_period", "快线周期", 12, 8, 20, 1, "MACD快线周期"),
                    StrategyParameter("slow_period", "慢线周期", 26, 20, 40, 1, "MACD慢线周期"),
                    StrategyParameter("signal_period", "信号线周期", 9, 5, 15, 1, "信号线周期"),
                ],
                "logic": StrategyLogic(
                    entry_conditions=["DIF上穿DEA"],
                    exit_conditions=["DIF下穿DEA"],
                    position_sizing="固定比例",
                ),
                "suitable": "适合趋势市场",
                "risk": "震荡市场信号可能频繁",
            },
            "bollinger": {
                "name": "布林带策略",
                "type": StrategyType.MEAN_REVERSION,
                "category": StrategyCategory.SIMPLE,
                "keywords": ["布林", "bollinger", "boll", "上轨", "下轨"],
                "parameters": [
                    StrategyParameter("period", "计算周期", 20, 10, 30, 1, "布林带计算周期"),
                    StrategyParameter("std_dev", "标准差倍数", 2.0, 1.5, 3.0, 0.1, "标准差倍数"),
                ],
                "logic": StrategyLogic(
                    entry_conditions=["价格触及下轨"],
                    exit_conditions=["价格触及上轨"],
                    position_sizing="固定比例",
                ),
                "suitable": "适合震荡市场",
                "risk": "趋势突破时可能亏损",
            },
            "kdj": {
                "name": "KDJ策略",
                "type": StrategyType.MEAN_REVERSION,
                "category": StrategyCategory.SIMPLE,
                "keywords": ["kdj", "随机指标"],
                "parameters": [
                    StrategyParameter("n", "N周期", 9, 5, 20, 1, "RSV计算周期"),
                    StrategyParameter("m1", "M1周期", 3, 2, 10, 1, "K值平滑周期"),
                    StrategyParameter("m2", "M2周期", 3, 2, 10, 1, "D值平滑周期"),
                ],
                "logic": StrategyLogic(
                    entry_conditions=["K线上穿D线且J值<20"],
                    exit_conditions=["K线下穿D线且J值>80"],
                    position_sizing="固定比例",
                ),
                "suitable": "适合震荡市场",
                "risk": "趋势市场信号可能失真",
            },
            "breakout": {
                "name": "突破策略",
                "type": StrategyType.BREAKOUT,
                "category": StrategyCategory.SIMPLE,
                "keywords": ["突破", "新高", "新低", "区间"],
                "parameters": [
                    StrategyParameter("lookback", "回看周期", 20, 10, 60, 1, "突破判断周期"),
                    StrategyParameter("confirm_days", "确认天数", 3, 1, 5, 1, "突破确认天数"),
                ],
                "logic": StrategyLogic(
                    entry_conditions=["价格突破N日高点"],
                    exit_conditions=["价格跌破N日低点"],
                    position_sizing="固定比例",
                ),
                "suitable": "适合趋势启动阶段",
                "risk": "假突破可能导致亏损",
            },
            "momentum": {
                "name": "动量策略",
                "type": StrategyType.MOMENTUM,
                "category": StrategyCategory.SIMPLE,
                "keywords": ["动量", "momentum", "涨跌幅"],
                "parameters": [
                    StrategyParameter("lookback", "回看周期", 20, 10, 60, 1, "动量计算周期"),
                    StrategyParameter("threshold", "动量阈值", 5.0, 1.0, 20.0, 0.5, "动量阈值(%)"),
                ],
                "logic": StrategyLogic(
                    entry_conditions=["动量超过阈值"],
                    exit_conditions=["动量转负"],
                    position_sizing="固定比例",
                ),
                "suitable": "适合趋势市场",
                "risk": "动量衰减时可能回调",
            },
            "rotation": {
                "name": "轮动策略",
                "type": StrategyType.ROTATION,
                "category": StrategyCategory.COMPOUND,
                "keywords": ["轮动", "rotation", "etf", "多标的"],
                "parameters": [
                    StrategyParameter("momentum_period", "动量周期", 20, 10, 60, 1, "动量计算周期"),
                    StrategyParameter("top_n", "持有数量", 1, 1, 5, 1, "持有标的数量"),
                    StrategyParameter("rebalance_days", "调仓周期", 5, 1, 20, 1, "调仓间隔天数"),
                ],
                "logic": StrategyLogic(
                    entry_conditions=["选择动量最强的N个标的"],
                    exit_conditions=["标的动量排名下降"],
                    position_sizing="等权分配",
                    rebalance_frequency="定期调仓",
                ),
                "suitable": "适合多标的配置",
                "risk": "震荡市场可能频繁换仓",
            },
            "grid": {
                "name": "网格策略",
                "type": StrategyType.MEAN_REVERSION,
                "category": StrategyCategory.SIMPLE,
                "keywords": ["网格", "grid", "分批"],
                "parameters": [
                    StrategyParameter("grid_num", "网格数量", 10, 5, 20, 1, "网格数量"),
                    StrategyParameter("grid_pct", "网格间距(%)", 5.0, 1.0, 10.0, 0.5, "网格间距百分比"),
                ],
                "logic": StrategyLogic(
                    entry_conditions=["价格下跌一格买入"],
                    exit_conditions=["价格上涨一格卖出"],
                    position_sizing="网格仓位",
                ),
                "suitable": "适合震荡市场",
                "risk": "单边行情可能被套",
            },
        }
    
    def _init_indicator_patterns(self) -> Dict[str, str]:
        """初始化指标模式"""
        return {
            r"(\d+)[日天]\s*(?:均线|ma)": "ma_period",
            r"快线\s*(\d+)": "fast_period",
            r"慢线\s*(\d+)": "slow_period",
            r"周期\s*(\d+)": "period",
            r"超买\s*(\d+)": "overbought",
            r"超卖\s*(\d+)": "oversold",
            r"rsi\s*(\d+)": "rsi_period",
            r"止损\s*(\d+)": "stop_loss_pct",
            r"止盈\s*(\d+)": "take_profit_pct",
        }
    
    def generate(self, description: str) -> GeneratedStrategy:
        """
        生成策略
        
        Args:
            description: 策略描述
            
        Returns:
            GeneratedStrategy对象
        """
        template_key, confidence = self._match_template(description)
        
        params = self._extract_parameters(description, template_key)
        
        if template_key and confidence > 0.5:
            strategy = self._generate_from_template(template_key, params, description)
        else:
            strategy = self._generate_custom(description, params)
        
        strategy.code = self._generate_code(strategy, params)
        
        errors = self._validate_code(strategy.code)
        strategy.validation_errors = errors
        
        return strategy
    
    def _match_template(self, description: str) -> Tuple[Optional[str], float]:
        """匹配策略模板"""
        description_lower = description.lower()
        
        scores = {}
        
        for key, template in self._strategy_templates.items():
            score = 0
            for keyword in template["keywords"]:
                if keyword in description_lower:
                    score += 1
            
            if score > 0:
                scores[key] = score / len(template["keywords"])
        
        if not scores:
            return None, 0.0
        
        best_key = max(scores, key=scores.get)
        return best_key, scores[best_key]
    
    def _extract_parameters(self, description: str, template_key: Optional[str]) -> Dict[str, Any]:
        """从描述中提取参数"""
        params = {}
        
        for pattern, param_name in self._indicator_patterns.items():
            matches = re.findall(pattern, description, re.IGNORECASE)
            if matches:
                params[param_name] = int(matches[0])
        
        numbers = re.findall(r'\d+', description)
        
        if template_key and template_key in self._strategy_templates:
            template_params = self._strategy_templates[template_key]["parameters"]
            
            for i, param in enumerate(template_params):
                if param.name not in params and i < len(numbers):
                    if "period" in param.name.lower() or "周期" in param.display_name:
                        params[param.name] = int(numbers[i])
        
        return params
    
    def _generate_from_template(
        self,
        template_key: str,
        params: Dict[str, Any],
        description: str
    ) -> GeneratedStrategy:
        """从模板生成策略"""
        template = self._strategy_templates[template_key]
        
        parameters = []
        for param in template["parameters"]:
            new_param = StrategyParameter(
                name=param.name,
                display_name=param.display_name,
                default_value=params.get(param.name, param.default_value),
                min_value=param.min_value,
                max_value=param.max_value,
                step=param.step,
                description=param.description,
                param_type=param.param_type,
            )
            parameters.append(new_param)
        
        class_name = self._generate_class_name(template["name"])
        
        return GeneratedStrategy(
            name=template["name"],
            class_name=class_name,
            category=template["category"],
            strategy_type=template["type"],
            description=description,
            code="",
            parameters=parameters,
            logic=template["logic"],
            suitable_market=template["suitable"],
            risk_warning=template["risk"],
            dependencies=["numpy", "pandas"],
        )
    
    def _generate_custom(self, description: str, params: Dict[str, Any]) -> GeneratedStrategy:
        """生成自定义策略"""
        strategy_type = self._infer_strategy_type(description)
        
        parameters = self._infer_parameters(description, params)
        
        logic = self._infer_logic(description)
        
        class_name = self._generate_class_name("自定义策略")
        
        return GeneratedStrategy(
            name="自定义策略",
            class_name=class_name,
            category=StrategyCategory.SIMPLE,
            strategy_type=strategy_type,
            description=description,
            code="",
            parameters=parameters,
            logic=logic,
            suitable_market="请根据策略特点填写",
            risk_warning="请根据策略风险填写",
            dependencies=["numpy", "pandas"],
        )
    
    def _infer_strategy_type(self, description: str) -> StrategyType:
        """推断策略类型"""
        description_lower = description.lower()
        
        if any(kw in description_lower for kw in ["趋势", "均线", "macd"]):
            return StrategyType.TREND_FOLLOWING
        elif any(kw in description_lower for kw in ["rsi", "布林", "震荡", "回归"]):
            return StrategyType.MEAN_REVERSION
        elif any(kw in description_lower for kw in ["动量", "momentum"]):
            return StrategyType.MOMENTUM
        elif any(kw in description_lower for kw in ["突破", "新高"]):
            return StrategyType.BREAKOUT
        elif any(kw in description_lower for kw in ["轮动", "rotation"]):
            return StrategyType.ROTATION
        else:
            return StrategyType.CUSTOM
    
    def _infer_parameters(self, description: str, extracted_params: Dict[str, Any]) -> List[StrategyParameter]:
        """推断策略参数"""
        parameters = []
        
        if "period" not in extracted_params and "周期" in description:
            parameters.append(StrategyParameter(
                name="period",
                display_name="计算周期",
                default_value=20,
                min_value=5,
                max_value=60,
                step=1,
                description="指标计算周期",
            ))
        
        if "止损" in description:
            parameters.append(StrategyParameter(
                name="stop_loss_pct",
                display_name="止损比例(%)",
                default_value=extracted_params.get("stop_loss_pct", 5),
                min_value=1,
                max_value=20,
                step=1,
                description="止损百分比",
            ))
        
        if "止盈" in description:
            parameters.append(StrategyParameter(
                name="take_profit_pct",
                display_name="止盈比例(%)",
                default_value=extracted_params.get("take_profit_pct", 10),
                min_value=1,
                max_value=50,
                step=1,
                description="止盈百分比",
            ))
        
        if not parameters:
            parameters.append(StrategyParameter(
                name="lookback",
                display_name="回看周期",
                default_value=20,
                min_value=5,
                max_value=60,
                step=1,
                description="策略计算周期",
            ))
        
        return parameters
    
    def _infer_logic(self, description: str) -> StrategyLogic:
        """推断策略逻辑"""
        entry_conditions = []
        exit_conditions = []
        
        if "买入" in description:
            buy_match = re.search(r"买入[：:]*([^，。；]+)", description)
            if buy_match:
                entry_conditions.append(buy_match.group(1).strip())
        
        if "卖出" in description:
            sell_match = re.search(r"卖出[：:]*([^，。；]+)", description)
            if sell_match:
                exit_conditions.append(sell_match.group(1).strip())
        
        if not entry_conditions:
            entry_conditions = ["根据指标信号买入"]
        if not exit_conditions:
            exit_conditions = ["根据指标信号卖出"]
        
        return StrategyLogic(
            entry_conditions=entry_conditions,
            exit_conditions=exit_conditions,
            position_sizing="固定比例",
        )
    
    def _generate_class_name(self, name: str) -> str:
        """生成类名"""
        class_name = re.sub(r'[^\w\s]', '', name)
        words = class_name.split()
        class_name = ''.join(word.capitalize() for word in words)
        
        if not class_name.endswith("Strategy"):
            class_name += "Strategy"
        
        return class_name
    
    def _generate_code(self, strategy: GeneratedStrategy, params: Dict[str, Any]) -> str:
        """生成策略代码"""
        code_template = self._get_code_template(strategy)
        
        code = code_template.format(
            class_name=strategy.class_name,
            description=strategy.description,
            strategy_type=strategy.strategy_type.value,
            params_info=self._format_params_info(strategy.parameters),
            init_params=self._format_init_params(strategy.parameters),
            set_params=self._format_set_params(strategy.parameters),
            entry_logic=self._format_entry_logic(strategy.logic),
            exit_logic=self._format_exit_logic(strategy.logic),
            suitable=strategy.suitable_market,
            risk=strategy.risk_warning,
        )
        
        return code
    
    def _get_code_template(self, strategy: GeneratedStrategy) -> str:
        """获取代码模板"""
        if strategy.strategy_type == StrategyType.TREND_FOLLOWING:
            return self._get_trend_template()
        elif strategy.strategy_type == StrategyType.MEAN_REVERSION:
            return self._get_reversion_template()
        elif strategy.strategy_type == StrategyType.ROTATION:
            return self._get_rotation_template()
        else:
            return self._get_custom_template()
    
    def _get_trend_template(self) -> str:
        """获取趋势策略模板"""
        return '''
class {class_name}(StrategyBase):
    """{description}
    
    策略类型: {strategy_type}
    """
    
    category = StrategyCategory.SIMPLE
    display_name = "{class_name}"
    description = "{description}"
    logic = {entry_logic}
    suitable = "{suitable}"
    risk = "{risk}"
    params_info = {params_info}
    
    def __init__(self):
        super().__init__()
{init_params}
    
    def initialize(self) -> None:
{set_params}
    
    def on_bar(self, bar: BarData) -> None:
        code = bar.code
        
        closes = self.get_prices(code, 100)
        if len(closes) < 60:
            return
        
        ma_fast = self.SMA(closes, self._fast_period)
        ma_slow = self.SMA(closes, self._slow_period)
        
        if np.isnan(ma_fast[-1]) or np.isnan(ma_slow[-1]):
            return
        
        current_fast = ma_fast[-1]
        current_slow = ma_slow[-1]
        prev_fast = ma_fast[-2]
        prev_slow = ma_slow[-2]
        
        if prev_fast <= prev_slow and current_fast > current_slow:
            if not self.has_position(code):
                self.buy(code, ratio=0.95)
                self.log(f"金叉买入: 快线{{current_fast:.2f}} > 慢线{{current_slow:.2f}}")
        
        elif prev_fast >= prev_slow and current_fast < current_slow:
            if self.has_position(code):
                self.sell_all(code)
                self.log(f"死叉卖出: 快线{{current_fast:.2f}} < 慢线{{current_slow:.2f}}")
'''
    
    def _get_reversion_template(self) -> str:
        """获取均值回归策略模板"""
        return '''
class {class_name}(StrategyBase):
    """{description}
    
    策略类型: {strategy_type}
    """
    
    category = StrategyCategory.SIMPLE
    display_name = "{class_name}"
    description = "{description}"
    logic = {entry_logic}
    suitable = "{suitable}"
    risk = "{risk}"
    params_info = {params_info}
    
    def __init__(self):
        super().__init__()
{init_params}
    
    def initialize(self) -> None:
{set_params}
    
    def on_bar(self, bar: BarData) -> None:
        code = bar.code
        
        closes = self.get_prices(code, 50)
        if len(closes) < 30:
            return
        
        rsi = self.RSI(closes, self._period)
        current_rsi = rsi[-1]
        
        if np.isnan(current_rsi):
            return
        
        if current_rsi < self._oversold:
            if not self.has_position(code):
                self.buy(code, ratio=0.95)
                self.log(f"RSI超卖买入: RSI={{current_rsi:.2f}}")
        
        elif current_rsi > self._overbought:
            if self.has_position(code):
                self.sell_all(code)
                self.log(f"RSI超买卖出: RSI={{current_rsi:.2f}}")
'''
    
    def _get_rotation_template(self) -> str:
        """获取轮动策略模板"""
        return '''
class {class_name}(StrategyBase):
    """{description}
    
    策略类型: {strategy_type}
    """
    
    category = StrategyCategory.COMPOUND
    display_name = "{class_name}"
    description = "{description}"
    logic = {entry_logic}
    suitable = "{suitable}"
    risk = "{risk}"
    params_info = {params_info}
    
    def __init__(self):
        super().__init__()
{init_params}
        self._last_rebalance = None
    
    def initialize(self) -> None:
{set_params}
        self._last_rebalance = None
    
    def on_bar(self, bar: BarData) -> None:
        if self._last_rebalance is None:
            days_since = self._rebalance_days
        else:
            days_since = (self._current_date - self._last_rebalance).days
        
        if days_since < self._rebalance_days:
            return
        
        self._last_rebalance = self._current_date
        
        momentum_scores = {{}}
        for code in self._data.keys():
            closes = self.get_prices(code, self._momentum_period + 5)
            if len(closes) >= self._momentum_period:
                momentum = (closes[-1] / closes[-self._momentum_period] - 1) * 100
                momentum_scores[code] = momentum
        
        sorted_codes = sorted(momentum_scores.keys(), key=lambda x: momentum_scores[x], reverse=True)
        target_codes = sorted_codes[:self._top_n]
        
        for code in list(self._portfolio.positions.keys()):
            if code not in target_codes:
                self.sell_all(code)
        
        for code in target_codes:
            if not self.has_position(code):
                self.buy(code, ratio=0.95 / self._top_n)
'''
    
    def _get_custom_template(self) -> str:
        """获取自定义策略模板"""
        return '''
class {class_name}(StrategyBase):
    """{description}
    
    策略类型: {strategy_type}
    """
    
    category = StrategyCategory.SIMPLE
    display_name = "{class_name}"
    description = "{description}"
    logic = {entry_logic}
    suitable = "{suitable}"
    risk = "{risk}"
    params_info = {params_info}
    
    def __init__(self):
        super().__init__()
{init_params}
    
    def initialize(self) -> None:
{set_params}
    
    def on_bar(self, bar: BarData) -> None:
        code = bar.code
        
        closes = self.get_prices(code, 60)
        if len(closes) < 20:
            return
        
        ma20 = self.SMA(closes, 20)
        ma60 = self.SMA(closes, 60)
        
        if np.isnan(ma20[-1]) or np.isnan(ma60[-1]):
            return
        
        if ma20[-1] > ma60[-1] and not self.has_position(code):
            self.buy(code, ratio=0.95)
            self.log("买入信号触发")
        
        elif ma20[-1] < ma60[-1] and self.has_position(code):
            self.sell_all(code)
            self.log("卖出信号触发")
'''
    
    def _format_params_info(self, parameters: List[StrategyParameter]) -> str:
        """格式化参数信息"""
        if not parameters:
            return "{}"
        
        lines = ["{"]
        for param in parameters:
            lines.append(f'            "{param.name}": {{')
            lines.append(f'                "default": {param.default_value},')
            lines.append(f'                "min": {param.min_value},')
            lines.append(f'                "max": {param.max_value},')
            lines.append(f'                "description": "{param.description}"')
            lines.append('            },')
        lines.append('        }')
        
        return '\n'.join(lines)
    
    def _format_init_params(self, parameters: List[StrategyParameter]) -> str:
        """格式化初始化参数"""
        if not parameters:
            return "        pass"
        
        lines = []
        for param in parameters:
            lines.append(f'        self._{param.name} = {param.default_value}')
        
        return '\n'.join(lines)
    
    def _format_set_params(self, parameters: List[StrategyParameter]) -> str:
        """格式化设置参数"""
        if not parameters:
            return "        pass"
        
        lines = []
        for param in parameters:
            lines.append(f'        self._{param.name} = self.get_param("{param.name}", {param.default_value})')
        
        return '\n'.join(lines)
    
    def _format_entry_logic(self, logic: StrategyLogic) -> str:
        """格式化入场逻辑"""
        if not logic or not logic.entry_conditions:
            return '["根据指标信号买入"]'
        
        conditions = [f'"{cond}"' for cond in logic.entry_conditions]
        return '[' + ', '.join(conditions) + ']'
    
    def _format_exit_logic(self, logic: StrategyLogic) -> str:
        """格式化出场逻辑"""
        if not logic or not logic.exit_conditions:
            return '["根据指标信号卖出"]'
        
        conditions = [f'"{cond}"' for cond in logic.exit_conditions]
        return '[' + ', '.join(conditions) + ']'
    
    def _validate_code(self, code: str) -> List[str]:
        """验证代码"""
        errors = []
        
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"语法错误: {str(e)}")
        
        required_imports = ["StrategyBase", "BarData", "StrategyCategory"]
        for imp in required_imports:
            if imp not in code:
                errors.append(f"缺少必要导入: {imp}")
        
        required_methods = ["def initialize", "def on_bar"]
        for method in required_methods:
            if method not in code:
                errors.append(f"缺少必要方法: {method}")
        
        return errors
    
    def get_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用模板"""
        return {
            key: {
                "name": template["name"],
                "type": template["type"].value,
                "category": template["category"].value,
                "keywords": template["keywords"],
                "parameters": [p.to_dict() for p in template["parameters"]],
                "suitable": template["suitable"],
                "risk": template["risk"],
            }
            for key, template in self._strategy_templates.items()
        }
    
    def suggest_improvements(self, strategy: GeneratedStrategy) -> List[str]:
        """建议策略改进"""
        suggestions = []
        
        if not strategy.parameters:
            suggestions.append("建议添加可调参数，提高策略灵活性")
        
        if strategy.logic and not strategy.logic.stop_loss:
            suggestions.append("建议添加止损机制，控制风险")
        
        if strategy.logic and not strategy.logic.take_profit:
            suggestions.append("建议添加止盈机制，锁定利润")
        
        if strategy.strategy_type == StrategyType.TREND_FOLLOWING:
            suggestions.append("趋势策略建议添加趋势过滤，避免震荡市场假信号")
        elif strategy.strategy_type == StrategyType.MEAN_REVERSION:
            suggestions.append("均值回归策略建议添加趋势过滤，避免逆势操作")
        
        if strategy.validation_errors:
            suggestions.append("请修复代码验证错误后再使用")
        
        return suggestions
