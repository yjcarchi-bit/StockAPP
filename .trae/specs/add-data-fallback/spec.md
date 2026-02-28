# 数据获取故障转移机制 Spec

## Why
当前系统仅依赖 efinance API 获取数据，当 efinance 服务不可用或额度用完时，数据获取会直接失败。需要实现自动故障转移机制，在 efinance 失败时自动切换到 akshare-proxy-patch 作为备用数据源。

## What Changes
- 修改 `get_history` 方法，添加故障转移逻辑
- 添加 `_try_efinance` 和 `_try_akshare_fallback` 私有方法
- 在 `DataConfig` 中添加 `enable_fallback` 配置选项
- 添加故障转移状态跟踪

## Impact
- Affected specs: 数据获取模块
- Affected code: 
  - `StockAPP/core/data_source.py`

## ADDED Requirements

### Requirement: 自动故障转移
系统 SHALL 在 efinance 数据获取失败时自动切换到 akshare-proxy-patch 备用数据源。

#### Scenario: efinance 成功
- **GIVEN** efinance 服务正常可用
- **WHEN** 调用数据获取方法
- **THEN** 使用 efinance 返回数据，不触发故障转移

#### Scenario: efinance 失败自动切换
- **GIVEN** efinance 服务不可用或返回空数据
- **AND** akshare-proxy-patch 已安装并配置
- **WHEN** 调用数据获取方法
- **THEN** 系统自动切换到 akshare-proxy-patch 获取数据
- **AND** 打印故障转移日志

#### Scenario: 所有数据源都失败
- **GIVEN** efinance 和 akshare-proxy-patch 都不可用
- **WHEN** 调用数据获取方法
- **THEN** 返回 None 并打印错误日志

#### Scenario: 故障转移被禁用
- **GIVEN** 配置中 `enable_fallback` 设为 False
- **WHEN** efinance 获取失败
- **THEN** 直接返回 None，不尝试备用数据源

### Requirement: 故障转移配置
系统 SHALL 提供故障转移功能的配置选项。

#### Scenario: 配置参数
- **WHEN** 用户配置故障转移时
- **THEN** 可以设置 `enable_fallback: bool` 控制是否启用故障转移

## MODIFIED Requirements

### Requirement: 数据获取方法
`get_history` 方法 SHALL 支持故障转移机制。

**修改内容**:
- 在 efinance 获取失败时，检查是否启用故障转移
- 如果启用故障转移且 akshare-proxy-patch 可用，尝试使用备用数据源
- 记录故障转移事件用于监控

## REMOVED Requirements
无移除的需求。
