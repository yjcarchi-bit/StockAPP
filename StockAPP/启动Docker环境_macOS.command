#!/bin/bash

clear
echo "=========================================="
echo "      StockAPP Docker 环境安装"
echo "         (macOS 版本)"
echo "=========================================="
echo ""

# 切换到脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Docker 配置目录
DOCKER_DIR="$SCRIPT_DIR/StockAPP/docker"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}→ $1${NC}"; }

check_docker() {
    if command -v docker &> /dev/null; then
        if docker info &> /dev/null; then
            return 0
        fi
    fi
    return 1
}

install_docker_homebrew() {
    print_info "正在使用 Homebrew 安装 Docker Desktop..."
    
    if ! command -v brew &> /dev/null; then
        print_error "Homebrew 未安装"
        print_info "正在安装 Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    brew install --cask docker
    
    if [ $? -eq 0 ]; then
        print_success "Docker Desktop 安装成功"
        return 0
    else
        return 1
    fi
}

install_docker_manual() {
    echo ""
    echo "请手动下载并安装 Docker Desktop:"
    echo "  https://www.docker.com/products/docker-desktop/"
    echo ""
    echo "安装步骤:"
    echo "  1. 下载 Docker.dmg"
    echo "  2. 拖拽到 Applications 文件夹"
    echo "  3. 启动 Docker Desktop"
    echo "  4. 重新运行此脚本"
    echo ""
    
    open "https://www.docker.com/products/docker-desktop/"
    exit 0
}

start_docker() {
    print_info "正在启动 Docker Desktop..."
    open -a Docker
    
    print_info "等待 Docker 启动..."
    local max_wait=60
    local count=0
    
    while [ $count -lt $max_wait ]; do
        if docker info &> /dev/null; then
            print_success "Docker 已就绪"
            return 0
        fi
        sleep 2
        count=$((count + 1))
        printf "\r等待中... (%d/%d)  " $count $max_wait
    done
    
    print_error "Docker 启动超时"
    return 1
}

start_app() {
    echo ""
    echo "=========================================="
    echo "  Docker 环境已就绪"
    echo "=========================================="
    echo ""
    
    echo "请选择操作:"
    echo "  1) 启动 StockAPP"
    echo "  2) 查看状态"
    echo "  3) 停止 StockAPP"
    echo "  4) 退出"
    echo ""
    read -p "请输入选择 [1-4]: " action
    
    case $action in
        1) run_app ;;
        2) show_status ;;
        3) stop_app ;;
        4) exit 0 ;;
        *) echo "无效选择"; exit 1 ;;
    esac
}

run_app() {
    echo ""
    print_info "正在构建并启动 StockAPP..."
    echo "首次构建可能需要几分钟..."
    echo ""
    
    cd "$DOCKER_DIR"
    docker-compose up -d --build
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "=========================================="
        echo "  StockAPP 启动成功！"
        echo "=========================================="
        echo ""
        echo "  前端地址: http://localhost"
        echo "  后端地址: http://localhost:8000"
        echo "  API文档:  http://localhost:8000/docs"
        echo ""
        echo "=========================================="
        echo ""
        
        sleep 3
        open "http://localhost"
    else
        print_error "启动失败，请检查日志:"
        echo "  docker-compose logs"
    fi
}

show_status() {
    echo ""
    echo "容器状态:"
    cd "$DOCKER_DIR"
    docker-compose ps
    echo ""
    echo "服务健康检查:"
    curl -s http://localhost:8000/health 2>/dev/null || echo "后端服务未响应"
    echo ""
    read -p "按回车继续..."
    start_app
}

stop_app() {
    echo ""
    print_info "正在停止 StockAPP..."
    cd "$DOCKER_DIR"
    docker-compose down
    print_success "应用已停止"
    exit 0
}

echo "检查 Docker Desktop..."
if check_docker; then
    print_success "Docker Desktop 已安装并运行中"
    start_app
    exit 0
fi

if [ -d "/Applications/Docker.app" ]; then
    print_info "Docker Desktop 已安装，正在启动..."
    start_docker
    if [ $? -eq 0 ]; then
        start_app
        exit 0
    fi
fi

echo ""
echo "Docker Desktop 未安装"
echo ""
echo "请选择安装方式:"
echo "  1) 使用 Homebrew 安装 (推荐)"
echo "  2) 手动下载安装"
echo "  3) 退出"
echo ""
read -p "请输入选择 [1-3]: " choice

case $choice in
    1) 
        install_docker_homebrew
        if [ $? -eq 0 ]; then
            start_docker
            start_app
        fi
        ;;
    2) install_docker_manual ;;
    3) exit 0 ;;
    *) echo "无效选择"; exit 1 ;;
esac
