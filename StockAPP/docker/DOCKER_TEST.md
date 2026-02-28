# Docker 环境测试文档

## 测试环境

- 操作系统: macOS / Windows
- Docker Desktop: 最新版本
- 项目路径: StockAPP/

---

## 1. 配置文件检查清单

### 1.1 Docker 配置文件

| 文件 | 状态 | 说明 |
|------|------|------|
| `docker-compose.yml` | ✅ 已验证 | 容器编排配置 |
| `Dockerfile.backend` | ✅ 已验证 | Python 后端镜像 |
| `Dockerfile.frontend` | ✅ 已验证 | Node.js 前端镜像 |
| `nginx.conf` | ✅ 已验证 | Nginx 反向代理 |
| `.dockerignore` | ✅ 已验证 | 构建排除规则 |
| `frontend/.env.production` | ✅ 已验证 | 生产环境变量 |

### 1.2 启动脚本

| 文件 | 状态 | 说明 |
|------|------|------|
| `启动Docker环境_Windows.bat` | ✅ 已创建 | Windows 自动安装脚本 |
| `启动Docker环境_macOS.command` | ✅ 已创建 | macOS 自动安装脚本 |

---

## 2. 构建测试

### 2.1 构建镜像

```bash
cd StockAPP
docker-compose build --no-cache
```

**预期结果:**
- 后端镜像构建成功 (python:3.11-slim)
- 前端镜像构建成功 (node:20-alpine + nginx:alpine)

### 2.2 检查镜像大小

```bash
docker images | grep stockapp
```

**预期结果:**
- backend: ~500MB
- frontend: ~50MB

---

## 3. 启动测试

### 3.1 启动服务

```bash
docker-compose up -d
```

### 3.2 检查容器状态

```bash
docker-compose ps
```

**预期结果:**
```
NAME                  STATUS                   PORTS
stockapp-backend      Up (healthy)             0.0.0.0:8000->8000/tcp
stockapp-frontend     Up (healthy)             0.0.0.0:80->80/tcp
```

### 3.3 查看日志

```bash
# 后端日志
docker-compose logs backend

# 前端日志
docker-compose logs frontend
```

---

## 4. API 端点测试

### 4.1 健康检查

```bash
curl http://localhost:8000/health
```

**预期响应:**
```json
{"status": "healthy"}
```

### 4.2 根端点

```bash
curl http://localhost:8000/
```

**预期响应:**
```json
{
  "name": "StockAPP API",
  "version": "2.0.0",
  "status": "running"
}
```

### 4.3 API 文档

```bash
curl <BACKEND_BASE_URL>/docs
```

**预期结果:** 返回 Swagger UI HTML

### 4.4 数据端点测试

```bash
# 获取 ETF 列表
curl <BACKEND_BASE_URL>/api/data/etf/list

# 获取策略列表
curl <BACKEND_BASE_URL>/api/strategies

# 获取数据更新状态
curl <BACKEND_BASE_URL>/api/data-update/status
```

---

## 5. 前端测试

### 5.1 访问前端

打开浏览器访问: http://localhost

**预期结果:**
- 页面正常加载
- 无控制台错误
- API 请求正常

### 5.2 功能测试

| 功能 | 测试步骤 | 预期结果 |
|------|----------|----------|
| 首页 | 访问 http://localhost | 显示仪表盘 |
| 策略回测 | 选择策略 → 设置参数 → 运行 | 显示回测结果 |
| 数据管理 | 点击数据管理 | 显示数据状态 |
| 参数优化 | 选择策略 → 优化参数 | 显示优化进度 |

---

## 6. Nginx 代理测试

### 6.1 API 代理

```bash
# 通过 Nginx 访问后端 API
curl http://localhost/api/data/etf/list
```

**预期结果:** 返回 ETF 列表数据

### 6.2 WebSocket 代理

```javascript
// 在浏览器控制台测试
const ws = new WebSocket('ws://localhost/ws/realtime');
ws.onopen = () => console.log('WebSocket connected');
ws.onmessage = (e) => console.log('Message:', e.data);
```

**预期结果:** WebSocket 连接成功

### 6.3 API 文档代理

```bash
curl http://localhost/docs
```

**预期结果:** 返回 Swagger UI

---

## 7. 数据持久化测试

### 7.1 检查数据挂载

```bash
docker-compose exec backend ls -la /app/data
```

**预期结果:** 显示本地 data 目录内容

### 7.2 缓存测试

```bash
# 创建测试缓存
docker-compose exec backend python -c "
import pickle
with open('/app/data/.cache/test.pkl', 'wb') as f:
    pickle.dump({'test': 'data'}, f)
print('Cache created')
"

# 验证本地文件
ls -la data/.cache/test.pkl
```

**预期结果:** 本地 data/.cache 目录存在 test.pkl 文件

---

## 8. 容错测试

### 8.1 后端重启测试

```bash
# 重启后端
docker-compose restart backend

# 等待健康检查通过
docker-compose ps
```

**预期结果:** 后端自动重启并恢复健康

### 8.2 前端依赖测试

```bash
# 停止后端
docker-compose stop backend

# 访问前端
curl http://localhost
```

**预期结果:** 前端静态页面正常显示，API 请求失败

### 8.3 完全重启测试

```bash
docker-compose down
docker-compose up -d
```

**预期结果:** 所有服务正常启动

---

## 9. 性能测试

### 9.1 内存使用

```bash
docker stats --no-stream
```

**预期结果:**
- backend: < 500MB
- frontend: < 20MB

### 9.2 响应时间

```bash
# 测试 API 响应时间
curl -o /dev/null -s -w "%{time_total}\n" <BACKEND_BASE_URL>/api/data/etf/list
```

**预期结果:** < 1 秒

---

## 10. 清理测试

### 10.1 停止服务

```bash
docker-compose down
```

### 10.2 清理镜像

```bash
docker-compose down --rmi all -v
```

### 10.3 完全清理

```bash
docker system prune -a --volumes
```

---

## 11. 常见问题排查

### 问题 1: 端口被占用

```bash
# 检查端口占用
lsof -i :80
lsof -i :8000

# 终止占用进程
kill -9 <PID>
```

### 问题 2: 镜像构建失败

```bash
# 清理 Docker 缓存
docker builder prune

# 重新构建
docker-compose build --no-cache
```

### 问题 3: 容器无法启动

```bash
# 查看详细日志
docker-compose logs --tail=100

# 检查容器状态
docker inspect stockapp-backend
```

### 问题 4: 网络问题

```bash
# 检查 Docker 网络
docker network ls
docker network inspect stockapp-network

# 重建网络
docker-compose down
docker-compose up -d
```

---

## 12. 测试结果汇总

| 测试项 | 状态 | 备注 |
|--------|------|------|
| 配置文件验证 | ✅ | 所有文件语法正确 |
| 镜像构建 | ⏳ | 需要 Docker 环境 |
| 服务启动 | ⏳ | 需要 Docker 环境 |
| API 测试 | ⏳ | 需要 Docker 环境 |
| 前端测试 | ⏳ | 需要 Docker 环境 |
| 代理测试 | ⏳ | 需要 Docker 环境 |
| 数据持久化 | ⏳ | 需要 Docker 环境 |
| 容错测试 | ⏳ | 需要 Docker 环境 |

---

## 13. 下一步操作

1. **安装 Docker Desktop**
   - macOS: 运行 `./启动Docker环境_macOS.command`
   - Windows: 运行 `启动Docker环境_Windows.bat`

2. **运行测试**
   ```bash
   cd StockAPP
   docker-compose up -d --build
   ```

3. **验证服务**
   - 访问 http://localhost
   - 访问 http://localhost:8000/docs

---

*文档生成时间: 2026-02-23*
