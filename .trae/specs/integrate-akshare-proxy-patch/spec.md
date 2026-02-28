# 集成 akshare_proxy_patch 数据源代理 Spec

## Why
测试策略中已成功使用 `akshare_proxy_patch` 解决东方财富API连接问题，需要将此方案统一集成到 StockAPP 主项目中，确保数据获取的稳定性和一致性。

## What Changes
- 在 `core/data_source.py` 中集成 `akshare_proxy_patch` 支持
- 在 `backend/requirements.txt` 中添加 `akshare-proxy-patch` 依赖
- 添加配置选项控制是否启用代理补丁
- 保持向后兼容，当 `akshare_proxy_patch` 未安装时自动降级

## Impact
- Affected specs: 数据获取模块
- Affected code: 
  - `StockAPP/core/data_source.py`
  - `StockAPP/backend/requirements.txt`
  - `StockAPP/config/settings.py` (新增配置项)

## ADDED Requirements

### Requirement: 代理补丁集成
系统 SHALL 支持 `akshare_proxy_patch` 代理补丁，用于解决东方财富API连接问题。

#### Scenario: 启用代理补丁
- **GIVEN** 系统配置了代理服务器地址和授权码
- **WHEN** 初始化数据源时
- **THEN** 系统自动安装代理补丁，所有 efinance 请求通过代理服务器

#### Scenario: 未安装代理补丁包
- **GIVEN** `akshare_proxy_patch` 包未安装
- **WHEN** 初始化数据源时
- **THEN** 系统打印警告信息，继续使用直接连接方式

#### Scenario: 代理补丁配置禁用
- **GIVEN** 配置中禁用了代理补丁功能
- **WHEN** 初始化数据源时
- **THEN** 系统不加载代理补丁，使用直接连接方式

### Requirement: 配置管理
系统 SHALL 提供代理补丁的配置选项。

#### Scenario: 配置参数
- **WHEN** 用户配置代理补丁时
- **THEN** 可以设置以下参数：
  - `proxy_host`: 代理服务器地址
  - `proxy_auth_code`: 授权码
  - `proxy_timeout`: 超时时间（秒）
  - `enable_proxy`: 是否启用代理

## MODIFIED Requirements

### Requirement: 数据源初始化
数据源初始化时 SHALL 检查并可选地加载代理补丁。

**修改内容**:
- 在 `DataSource.__init__` 方法中添加代理补丁初始化逻辑
- 添加 `_init_proxy_patch` 私有方法处理补丁加载
- 在 `DataConfig` 数据类中添加代理相关配置字段

## REMOVED Requirements
无移除的需求。
