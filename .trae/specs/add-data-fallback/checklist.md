# Checklist

## 配置扩展
- [x] `DataConfig` 数据类包含 `enable_fallback` 配置字段
- [x] 配置字段默认值为 True（启用故障转移）

## 故障转移逻辑
- [x] `get_history` 方法支持故障转移
- [x] efinance 失败时自动尝试 akshare-proxy-patch
- [x] 故障转移时打印日志信息
- [x] 所有数据源失败时返回 None

## 配置控制
- [x] `enable_fallback=False` 时不触发故障转移
- [x] `enable_fallback=True` 时正常触发故障转移

## 代码质量
- [x] 代码遵循项目现有风格
- [x] 添加必要的注释说明
- [x] 无语法错误
