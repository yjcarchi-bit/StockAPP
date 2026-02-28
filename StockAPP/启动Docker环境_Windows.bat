@echo off
chcp 65001 >nul 2>&1
title StockAPP Docker 环境安装

cls
echo ==========================================
echo       StockAPP Docker 环境安装
echo          (Windows 版本)
echo ==========================================
echo.

cd /d "%~dp0"

set DOCKER_DIR=%~dp0StockAPP\docker

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 需要管理员权限，正在请求提升权限...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: 检查 WSL2
echo 检查 WSL2 环境...
wsl --status >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo WSL2 未安装，正在安装...
    echo 这可能需要几分钟，请耐心等待...
    echo.
    
    wsl --install -d Ubuntu --no-launch
    
    if %errorlevel% neq 0 (
        echo.
        echo WSL2 安装遇到问题，尝试启用功能...
        dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
        dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
        
        echo.
        echo 需要重启电脑以完成 WSL2 安装
        echo 重启后请重新运行此脚本
        echo.
        set /p restart="是否立即重启？(Y/N): "
        if /i "%restart%"=="Y" (
            shutdown /r /t 10
        )
        pause
        exit /b 0
    )
)

echo WSL2 已就绪
echo.

:: 检查 Docker Desktop
echo 检查 Docker Desktop...
where docker >nul 2>&1
if %errorlevel% equ 0 (
    docker info >nul 2>&1
    if %errorlevel% equ 0 (
        echo Docker Desktop 已安装并运行中
        echo.
        goto :start_app
    )
)

:: 检查 Docker Desktop 安装路径
set "DOCKER_PATH=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
set "DOCKER_PATH2=%LOCALAPPDATA%\Docker\Docker Desktop.exe"

if exist "%DOCKER_PATH%" (
    echo Docker Desktop 已安装，正在启动...
    start "" "%DOCKER_PATH%"
    goto :wait_docker
)

if exist "%DOCKER_PATH2%" (
    echo Docker Desktop 已安装，正在启动...
    start "" "%DOCKER_PATH2%"
    goto :wait_docker
)

:: 安装 Docker Desktop
echo Docker Desktop 未安装
echo.
echo 请选择安装方式:
echo   1) 自动下载并安装 Docker Desktop (推荐)
echo   2) 使用 winget 安装 (Windows 11/10)
echo   3) 手动下载安装
echo   4) 退出
echo.
set /p choice="请输入选择 [1-4]: "

if "%choice%"=="1" goto :download_install
if "%choice%"=="2" goto :winget_install
if "%choice%"=="3" goto :manual_install
if "%choice%"=="4" goto :exit_script
echo 无效选择
goto :exit_script

:download_install
echo.
echo 正在下载 Docker Desktop...
echo 文件较大，请耐心等待...
echo.

set "DOCKER_INSTALLER=%TEMP%\DockerDesktopInstaller.exe"

:: 使用 PowerShell 下载
powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe' -OutFile '%DOCKER_INSTALLER%' -UseBasicParsing }"

if not exist "%DOCKER_INSTALLER%" (
    echo.
    echo 下载失败！
    echo 请检查网络连接或尝试使用 winget 安装
    goto :winget_install
)

echo.
echo 下载完成，正在安装 Docker Desktop...
echo 安装过程中请勿关闭窗口...
echo.

:: 安装 Docker Desktop（静默安装）
"%DOCKER_INSTALLER%" install --quiet --accept-license --backend=wsl-2

if %errorlevel% equ 0 (
    echo.
    echo Docker Desktop 安装成功！
    del "%DOCKER_INSTALLER%" >nul 2>&1
    
    echo.
    echo 正在启动 Docker Desktop...
    start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    
    goto :wait_docker
) else (
    echo.
    echo 安装失败，错误代码: %errorlevel%
    echo 请尝试手动安装
    goto :manual_install
)

:winget_install
echo.
where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo winget 不可用，请使用其他安装方式
    goto :download_install
)

echo 正在使用 winget 安装 Docker Desktop...
echo 这可能需要几分钟...
echo.

winget install Docker.DockerDesktop --accept-package-agreements --accept-source-agreements

if %errorlevel% equ 0 (
    echo.
    echo Docker Desktop 安装成功！
    
    :: 刷新环境变量
    call refreshenv >nul 2>&1
    
    echo 正在启动 Docker Desktop...
    start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    
    goto :wait_docker
) else (
    echo.
    echo winget 安装失败，请尝试手动安装
    goto :manual_install
)

:manual_install
echo.
echo 请手动下载并安装 Docker Desktop:
echo   https://www.docker.com/products/docker-desktop/
echo.
echo 安装步骤:
echo   1. 下载 Docker Desktop Installer
echo   2. 运行安装程序
echo   3. 安装完成后重启电脑
echo   4. 启动 Docker Desktop
echo   5. 重新运行此脚本
echo.
pause
exit /b 0

:wait_docker
echo.
echo 等待 Docker 启动...
echo 首次启动可能需要 1-2 分钟...
echo.

set MAX_WAIT=60
set WAIT_COUNT=0

:check_docker
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo Docker 已就绪！
    echo.
    goto :start_app
)

set /a WAIT_COUNT+=1
if %WAIT_COUNT% lss %MAX_WAIT% (
    timeout /t 2 /nobreak >nul
    echo 等待中... (%WAIT_COUNT%/%MAX_WAIT%)
    goto :check_docker
)

echo.
echo Docker 启动超时
echo 请手动启动 Docker Desktop 后重新运行此脚本
pause
exit /b 1

:start_app
echo ==========================================
echo   Docker 环境已就绪
echo ==========================================
echo.

echo 请选择操作:
echo   1) 启动 StockAPP
echo   2) 查看状态
echo   3) 停止 StockAPP
echo   4) 退出
echo.
set /p action="请输入选择 [1-4]: "

if "%action%"=="1" goto :run_app
if "%action%"=="2" goto :show_status
if "%action%"=="3" goto :stop_app
if "%action%"=="4" goto :exit_script
echo 无效选择
goto :exit_script

:run_app
echo.
echo 正在构建并启动 StockAPP...
echo 首次构建可能需要几分钟...
echo.

cd /d "%DOCKER_DIR%"
docker-compose up -d --build

if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo   StockAPP 启动成功！
    echo ==========================================
    echo.
    echo   前端地址: http://localhost
    echo   后端地址: http://localhost:8000
    echo   API文档:  http://localhost:8000/docs
    echo.
    echo ==========================================
    echo.
    
    timeout /t 3 /nobreak >nul
    start http://localhost
) else (
    echo.
    echo 启动失败，请检查日志:
    echo   docker-compose logs
)

pause
exit /b 0

:show_status
echo.
echo 容器状态:
cd /d "%DOCKER_DIR%"
docker-compose ps
echo.
echo 服务健康检查:
docker-compose exec -T backend curl -s http://localhost:8000/health 2>nul
echo.
pause
goto :start_app

:stop_app
echo.
echo 正在停止 StockAPP...
cd /d "%DOCKER_DIR%"
docker-compose down
echo 应用已停止
pause
exit /b 0

:exit_script
echo 已取消
pause
exit /b 0
