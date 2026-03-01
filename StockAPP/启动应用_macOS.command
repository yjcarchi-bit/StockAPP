#!/bin/bash
# StockAPP macOS 启动脚本
# 双击此文件启动应用 (React + FastAPI 版本)
# 支持单实例模式，防止重复启动

clear

echo "=========================================="
echo "      StockAPP 量化回测平台"
echo "         (macOS 版本)"
echo "=========================================="
echo ""

# 切换到脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 应用目录（脚本所在目录即为应用根目录）
APP_DIR="$SCRIPT_DIR"

# PID 文件路径
PID_FILE="/tmp/stockapp.pid"

# 停止已有实例
stop_existing_instance() {
    local backend_running=0
    local frontend_running=0
    
    # 检查后端端口
    if lsof -i:8000 > /dev/null 2>&1; then
        backend_running=1
    fi
    
    # 检查前端端口
    if lsof -i:5173 > /dev/null 2>&1; then
        frontend_running=1
    fi
    
    # 如果有端口被占用，停止旧实例
    if [ $backend_running -eq 1 ] || [ $frontend_running -eq 1 ]; then
        echo "检测到已有实例运行，正在停止..."
        
        # 停止占用端口的进程
        lsof -ti:8000 | xargs kill -9 2>/dev/null
        lsof -ti:5173 | xargs kill -9 2>/dev/null
        
        # 等待端口释放
        sleep 2
        echo "旧实例已停止"
        echo ""
    fi
}

# 写入 PID 文件
write_pid() {
    echo $$ > "$PID_FILE"
}

# 清理函数
cleanup() {
    echo ""
    echo "正在停止服务..."
    
    # 停止后端和前端进程
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    
    # 清理 PID 文件
    rm -f "$PID_FILE"
    
    # 清理端口
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    lsof -ti:5173 | xargs kill -9 2>/dev/null
    
    echo "服务已停止"
    exit 0
}

# 停止已有实例
stop_existing_instance

# 写入当前 PID
write_pid

# 设置退出信号处理
trap cleanup SIGINT SIGTERM EXIT

echo "工作目录: $(pwd)"
echo ""

# 检查 Homebrew
check_homebrew() {
    if command -v brew &> /dev/null; then
        return 0
    fi
    return 1
}

install_homebrew() {
    echo "正在安装 Homebrew..."
    echo "这可能需要几分钟，请耐心等待..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    if [[ -d "/opt/homebrew" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
}

# 查找 Python
PYTHON_CMD=""
PYTHON_VERSION=""

find_python() {
    if command -v python3 &> /dev/null; then
        local ver=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        local major=$(echo $ver | cut -d. -f1)
        local minor=$(echo $ver | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
            PYTHON_CMD="python3"
            PYTHON_VERSION="$ver"
            return 0
        fi
    fi
    
    if command -v python &> /dev/null; then
        local ver=$(python --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        local major=$(echo $ver | cut -d. -f1)
        local minor=$(echo $ver | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
            PYTHON_CMD="python"
            PYTHON_VERSION="$ver"
            return 0
        fi
    fi
    
    if [ -x "/opt/homebrew/bin/python3" ]; then
        PYTHON_CMD="/opt/homebrew/bin/python3"
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        return 0
    fi
    
    if [ -x "/usr/local/bin/python3" ]; then
        PYTHON_CMD="/usr/local/bin/python3"
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        return 0
    fi
    
    return 1
}

install_python() {
    echo ""
    echo "Python 未找到或版本过低 (需要 3.8+)"
    echo ""
    echo "请选择安装方式:"
    echo "  1) 使用 Homebrew 安装 (推荐)"
    echo "  2) 手动下载安装"
    echo "  3) 跳过 (退出)"
    echo ""
    read -p "请输入选择 [1-3]: " choice
    
    case $choice in
        1)
            if ! check_homebrew; then
                echo ""
                echo "Homebrew 未安装，需要先安装 Homebrew"
                read -p "是否安装 Homebrew? [y/N]: " install_brew
                if [[ "$install_brew" =~ ^[Yy]$ ]]; then
                    install_homebrew
                else
                    echo "已取消安装"
                    exit 1
                fi
            fi
            
            echo ""
            echo "正在通过 Homebrew 安装 Python..."
            brew install python3
            
            if find_python; then
                echo "Python 安装成功!"
            else
                echo "安装后仍无法找到 Python，请手动安装"
                exit 1
            fi
            ;;
        2)
            echo ""
            echo "请访问以下网址下载并安装 Python 3.8 或更高版本:"
            echo "  https://www.python.org/downloads/"
            echo ""
            echo "安装完成后，请重新运行此脚本"
            read -p "按回车键退出..."
            exit 1
            ;;
        3)
            echo "已取消"
            exit 1
            ;;
        *)
            echo "无效选择"
            exit 1
            ;;
    esac
}

# 查找 Node.js
NODE_CMD=""
NODE_VERSION=""

find_node() {
    local NODE_PATHS=(
        "$HOME/.trae-cn/binaries/node/versions/24.13.1/bin"
        "$HOME/.trae-cn/binaries/node/versions/*/bin"
        "$HOME/.nvm/versions/node/*/bin"
        "/opt/homebrew/bin"
        "/usr/local/bin"
        "$HOME/.local/bin"
    )
    
    for path_pattern in "${NODE_PATHS[@]}"; do
        for node_path in $path_pattern; do
            if [ -d "$node_path" ]; then
                export PATH="$node_path:$PATH"
            fi
        done
    done
    
    if [ -f "$HOME/.zshrc" ]; then
        source "$HOME/.zshrc" 2>/dev/null || true
    elif [ -f "$HOME/.bash_profile" ]; then
        source "$HOME/.bash_profile" 2>/dev/null || true
    fi
    
    if command -v node &> /dev/null; then
        NODE_CMD="node"
        NODE_VERSION=$(node --version 2>&1 | sed 's/v//')
        return 0
    fi
    
    if [ -x "$HOME/.trae-cn/binaries/node/versions/24.13.1/bin/node" ]; then
        NODE_CMD="$HOME/.trae-cn/binaries/node/versions/24.13.1/bin/node"
        export PATH="$HOME/.trae-cn/binaries/node/versions/24.13.1/bin:$PATH"
        NODE_VERSION=$($NODE_CMD --version 2>&1 | sed 's/v//')
        return 0
    fi
    
    if [ -x "/opt/homebrew/bin/node" ]; then
        NODE_CMD="/opt/homebrew/bin/node"
        NODE_VERSION=$($NODE_CMD --version 2>&1 | sed 's/v//')
        return 0
    fi
    
    if [ -x "/usr/local/bin/node" ]; then
        NODE_CMD="/usr/local/bin/node"
        NODE_VERSION=$($NODE_CMD --version 2>&1 | sed 's/v//')
        return 0
    fi
    
    return 1
}

install_node() {
    echo ""
    echo "Node.js 未找到"
    echo ""
    echo "请选择安装方式:"
    echo "  1) 使用 Homebrew 安装 (推荐)"
    echo "  2) 使用 nvm 安装 (推荐给开发者)"
    echo "  3) 手动下载安装"
    echo "  4) 跳过 (退出)"
    echo ""
    read -p "请输入选择 [1-4]: " choice
    
    case $choice in
        1)
            if ! check_homebrew; then
                echo ""
                echo "Homebrew 未安装，需要先安装 Homebrew"
                read -p "是否安装 Homebrew? [y/N]: " install_brew
                if [[ "$install_brew" =~ ^[Yy]$ ]]; then
                    install_homebrew
                else
                    echo "已取消安装"
                    exit 1
                fi
            fi
            
            echo ""
            echo "正在通过 Homebrew 安装 Node.js..."
            brew install node
            
            if find_node; then
                echo "Node.js 安装成功!"
            else
                echo "安装后仍无法找到 Node.js，请手动安装"
                exit 1
            fi
            ;;
        2)
            echo ""
            echo "正在安装 nvm (Node Version Manager)..."
            
            curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
            
            export NVM_DIR="$HOME/.nvm"
            [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
            
            echo ""
            echo "正在通过 nvm 安装 Node.js LTS 版本..."
            nvm install --lts
            nvm use --lts
            
            if find_node; then
                echo "Node.js 安装成功!"
            else
                echo "安装后仍无法找到 Node.js，请重启终端后重试"
                exit 1
            fi
            ;;
        3)
            echo ""
            echo "请访问以下网址下载并安装 Node.js LTS 版本:"
            echo "  https://nodejs.org/"
            echo ""
            echo "安装完成后，请重新运行此脚本"
            read -p "按回车键退出..."
            exit 1
            ;;
        4)
            echo "已取消"
            exit 1
            ;;
        *)
            echo "无效选择"
            exit 1
            ;;
    esac
}

# 检查并安装 Python
echo "检查 Python..."
if ! find_python; then
    install_python
fi
echo "使用 Python: $($PYTHON_CMD --version 2>&1)"
echo ""

# 检查并安装 Node.js
echo "检查 Node.js..."
if ! find_node; then
    install_node
fi
echo "使用 Node.js: v$NODE_VERSION"
echo ""

# 检查后端依赖
echo "检查后端依赖..."
cd "$APP_DIR/backend"

check_backend_deps() {
    local missing_deps=()
    
    for dep in fastapi uvicorn pydantic pandas numpy efinance apscheduler sqlalchemy pymysql; do
        $PYTHON_CMD -c "import $dep" 2>/dev/null
        if [ $? -ne 0 ]; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo "缺少以下依赖: ${missing_deps[*]}"
        return 1
    fi
    return 0
}

if ! check_backend_deps; then
    echo "正在安装后端依赖，请稍候..."
    $PYTHON_CMD -m pip install -r requirements.txt --quiet --user
    echo "后端依赖安装完成"
else
    echo "后端依赖已就绪"
fi

# 检查前端依赖
echo "检查前端依赖..."
cd "$APP_DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "正在安装前端依赖，请稍候..."
    npm install
fi

echo "依赖检查完成"
echo ""

# 清理可能占用的端口
echo "清理端口..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
sleep 1

# 启动后端
echo "正在启动后端服务..."
cd "$APP_DIR/backend"
$PYTHON_CMD run.py &
BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"

# 等待后端启动
echo "等待后端服务启动..."
for i in {1..15}; do
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        echo "后端服务启动成功!"
        break
    fi
    sleep 1
done

# 启动前端
echo "正在启动前端服务..."
cd "$APP_DIR/frontend"
npm run dev 2>&1 | tee /tmp/vite_output.log &
FRONTEND_PID=$!
echo "前端 PID: $FRONTEND_PID"

# 等待前端启动并检测实际端口
echo "等待前端服务启动..."
FRONTEND_PORT=""
for i in {1..20}; do
    # 尝试从 Vite 输出中获取实际端口
    if [ -z "$FRONTEND_PORT" ]; then
        FRONTEND_PORT=$(grep -oE 'localhost:[0-9]+' /tmp/vite_output.log 2>/dev/null | head -1 | grep -oE '[0-9]+$')
    fi
    
    # 如果找到了端口，验证服务是否可用
    if [ -n "$FRONTEND_PORT" ]; then
        if curl -s "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
            echo "前端服务启动成功! 端口: $FRONTEND_PORT"
            break
        fi
    fi
    sleep 1
done

# 如果没有检测到端口，使用默认值
if [ -z "$FRONTEND_PORT" ]; then
    FRONTEND_PORT="5173"
fi

# 自动打开浏览器
echo "正在打开浏览器..."
sleep 2
open "http://localhost:$FRONTEND_PORT"

echo ""
echo "=========================================="
echo "  服务已启动，浏览器已打开"
echo "  前端地址: http://localhost:$FRONTEND_PORT"
echo "  后端地址: http://localhost:8000"
echo "  API文档:  http://localhost:8000/docs"
echo "  关闭此窗口将停止应用"
echo "=========================================="
echo ""

# 等待进程
wait $BACKEND_PID $FRONTEND_PID
