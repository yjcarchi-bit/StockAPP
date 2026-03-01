"""Tushare 宏观数据客户端封装。

职责定位：
1. 统一初始化 `tushare.pro_api`（token 与超时管理）
2. 屏蔽 DataFrame 细节，统一返回 `List[Dict]`
3. 对返回值做 JSON 兼容清洗（NaN/时间/NumPy 标量）
"""

from __future__ import annotations

import math
import os
from datetime import date, datetime
from typing import Any, Dict, List

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import tushare as ts
except ImportError:
    ts = None


class TushareMacroClient:
    """Tushare 宏观接口轻量客户端。

    该类不关心业务规则，仅负责“可靠请求 + 类型清洗”。
    业务层（例如参数默认值、落库策略）由 `MacroDataService` 负责。
    """

    def __init__(self, token: str | None = None, timeout: int = 30):
        """初始化客户端。

        参数说明：
        - token: 显式传入 token；为空时回退到环境变量 `TUSHARE_TOKEN`
        - timeout: HTTP 超时秒数，最小为 1
        """
        self._token = (token or os.getenv("TUSHARE_TOKEN", "")).strip()
        self._timeout = max(int(timeout or 30), 1)
        if ts is None:
            raise RuntimeError("未安装 tushare，请先安装: pip install tushare")
        if not self._token:
            raise ValueError("未配置 TUSHARE_TOKEN")
        self._pro = ts.pro_api(self._token, timeout=self._timeout)

    def query(self, api_name: str, **params: Any) -> List[Dict[str, Any]]:
        """调用单个宏观接口并返回 JSON 友好的行数据。

        参数说明：
        - api_name: Tushare 接口名（例如 `shibor`、`cn_gdp`）
        - params: 透传给 `pro.query` 的参数（空值会被自动剔除）

        返回值：
        - `List[Dict[str, Any]]`，每个字典是一行记录
        - 若接口无数据，返回空列表
        """
        name = (api_name or "").strip()
        if not name:
            raise ValueError("api_name 不能为空")

        # 去掉 None 和空字符串，避免向 Tushare 传递无效参数。
        clean_params = {k: v for k, v in params.items() if v is not None and str(v).strip() != ""}
        df = self._pro.query(name, **clean_params)
        if df is None or df.empty:
            return []

        # 将 DataFrame 统一转换为“行字典”，再做值级别清洗。
        rows = df.to_dict(orient="records")
        return [self._normalize_row(row) for row in rows]

    @staticmethod
    def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
        """将单行数据转换为 JSON 兼容字典。"""
        return {str(k): TushareMacroClient._normalize_value(v) for k, v in row.items()}

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        """清洗单个字段值，确保可序列化且语义稳定。

        处理策略：
        - `NaN/Inf` -> `None`
        - `datetime/date` -> 字符串
        - NumPy/pandas 标量 -> Python 原生标量
        """
        if value is None:
            return None
        if isinstance(value, (str, int, bool)):
            return value
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
            return value
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, date):
            return value.isoformat()
        if pd is not None:
            try:
                if pd.isna(value):
                    return None
            except Exception:
                pass
        if hasattr(value, "item"):
            try:
                return TushareMacroClient._normalize_value(value.item())
            except Exception:
                pass
        return value
