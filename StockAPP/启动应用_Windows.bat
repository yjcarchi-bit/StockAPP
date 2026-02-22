@echo off
chcp 65001 >nul 2>&1
title StockAPP 量化回测平台

cls
echo ==========================================
echo       StockAPP 量化回测平台
echo          (Windows 版本)
echo ==========================================
echo.

cd /d "%~dp0"

echo 工作目录: %cd%
echo.

:: ============================================
:: 查找 Python
:: ============================================
set PYTHON_CMD=
set PYTHON_VERSION=

:find_python
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    set PYTHON_CMD=python
    goto :check_python_version
)

where python3 >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
    set PYTHON_CMD=python3
    goto :check_python_version
)

:: 尝试常见安装路径
if exist "%LOCALAPPDATA%\Programs\Python\Python3*\python.exe" (
    for /d %%i in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
        set PYTHON_CMD=%%i\python.exe
        goto :python_found
    )
)

if exist "C:\Python3*\python.exe" (
    for /d %%i in ("C:\Python3*") do (
        set PYTHON_CMD=%%i\python.exe
        goto :python_found
    )
)

goto :install_python

:check_python_version
:: 检查版本是否 >= 3.8
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)
if %PY_MAJOR% lss 3 goto :install_python
if %PY_MAJOR% equ 3 if %PY_MINOR% lss 8 goto :install_python

:python_found
echo 使用 Python: %PYTHON_VERSION%
echo.
goto :find_node

:install_python
echo.
echo Python 未找到或版本过低 (需要 3.8+)
echo.
echo 请选择安装方式:
echo   1) 自动下载并安装 Python (推荐)
echo   2) 手动下载安装
echo   3) 跳过 (退出)
echo.
set /p choice="请输入选择 [1-3]: "

if "%choice%"=="1" goto :auto_install_python
if "%choice%"=="2" goto :manual_install_python
if "%choice%"=="3" goto :exit_script
echo 无效选择
goto :exit_script

:auto_install_python
echo.
echo 正在下载 Python 安装程序...
echo 请在安装时勾选 "Add Python to PATH"
echo.

:: 使用 winget 安装 (Windows 10/11)
where winget >nul 2>&1
if %errorlevel% equ 0 (
    echo 使用 winget 安装 Python...
    winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    echo.
    echo Python 安装完成!
    echo 请关闭此窗口并重新运行脚本
    pause
    exit /b 0
)

:: 使用 PowerShell 下载
set PYTHON_INSTALLER=%TEMP%\python-installer.exe
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe' -OutFile '%PYTHON_INSTALLER%'"

if exist "%PYTHON_INSTALLER%" (
    echo 正在启动 Python 安装程序...
    echo 请在安装时勾选 "Add Python to PATH"
    start /wait "" "%PYTHON_INSTALLER%" /passive InstallAllUsers=1 PrependPath=1
    del "%PYTHON_INSTALLER%"
    echo.
    echo Python 安装完成!
    echo 请关闭此窗口并重新运行脚本
    pause
    exit /b 0
) else (
    echo 下载失败，请手动安装
    goto :manual_install_python
)

:manual_install_python
echo.
echo 请访问以下网址下载并安装 Python 3.8 或更高版本:
echo   https://www.python.org/downloads/
echo.
echo 安装时请务必勾选 "Add Python to PATH"
echo.
echo 安装完成后，请重新运行此脚本
pause
exit /b 1

:: ============================================
:: 查找 Node.js
:: ============================================
:find_node
set NODE_CMD=
set NODE_VERSION=

where node >nul 2>&1
if %errorlevel% equ 0 (
    set NODE_CMD=node
    for /f "tokens=1 delims=v" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
    goto :node_found
)

:: 尝试常见安装路径
if exist "%ProgramFiles%\nodejs\node.exe" (
    set NODE_CMD=%ProgramFiles%\nodejs\node.exe
    goto :node_found
)

if exist "%ProgramFiles(x86)%\nodejs\node.exe" (
    set NODE_CMD=%ProgramFiles(x86)%\nodejs\node.exe
    goto :node_found
)

if exist "%LOCALAPPDATA%\Programs\nodejs\node.exe" (
    set NODE_CMD=%LOCALAPPDATA%\Programs\nodejs\node.exe
    goto :node_found
)

goto :install_node

:node_found
echo 使用 Node.js: v%NODE_VERSION%
echo.
goto :check_dependencies

:install_node
echo.
echo Node.js 未找到
echo.
echo 请选择安装方式:
echo   1) 自动下载并安装 Node.js (推荐)
echo   2) 手动下载安装
echo   3) 跳过 (退出)
echo.
set /p choice="请输入选择 [1-3]: "

if "%choice%"=="1" goto :auto_install_node
if "%choice%"=="2" goto :manual_install_node
if "%choice%"=="3" goto :exit_script
echo 无效选择
goto :exit_script

:auto_install_node
echo.
echo 正在下载 Node.js 安装程序...

:: 使用 winget 安装 (Windows 10/11)
where winget >nul 2>&1
if %errorlevel% equ 0 (
    echo 使用 winget 安装 Node.js...
    winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
    echo.
    echo Node.js 安装完成!
    echo 请关闭此窗口并重新运行脚本
    pause
    exit /b 0
)

:: 使用 PowerShell 下载
set NODE_INSTALLER=%TEMP%\node-installer.msi
powershell -Command "Invoke-WebRequest -Uri 'https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi' -OutFile '%NODE_INSTALLER%'"

if exist "%NODE_INSTALLER%" (
    echo 正在启动 Node.js 安装程序...
    start /wait msiexec /i "%NODE_INSTALLER%" /passive
    del "%NODE_INSTALLER%"
    echo.
    echo Node.js 安装完成!
    echo 请关闭此窗口并重新运行脚本
    pause
    exit /b 0
) else (
    echo 下载失败，请手动安装
    goto :manual_install_node
)

:manual_install_node
echo.
echo 请访问以下网址下载并安装 Node.js LTS 版本:
echo   https://nodejs.org/
echo.
echo 安装完成后，请重新运行此脚本
pause
exit /b 1

:: ============================================
:: 检查依赖
:: ============================================
:check_dependencies

:: 检查后端依赖
echo 检查后端依赖...
cd /d "%~dp0backend"
%PYTHON_CMD% -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装后端依赖，请稍候...
    %PYTHON_CMD% -m pip install -r requirements.txt -q
)

:: 检查前端依赖
echo 检查前端依赖...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo 正在安装前端依赖，请稍候...
    npm install
)

echo 依赖检查完成
echo.

:: ============================================
:: 启动服务
:: ============================================

:: 清理可能占用的端口
echo 清理端口...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
timeout /t 1 /nobreak >nul

:: 启动后端
echo 正在启动后端服务...
cd /d "%~dp0backend"
start /b "" %PYTHON_CMD% run.py

:: 等待后端启动
echo 等待后端服务启动...
set MAX_WAIT=15
set WAIT_COUNT=0
:check_backend
curl -s http://localhost:8000/docs >nul 2>&1
if %errorlevel% equ 0 (
    echo 后端服务启动成功!
    goto :start_frontend
)
set /a WAIT_COUNT+=1
if %WAIT_COUNT% lss %MAX_WAIT% (
    timeout /t 1 /nobreak >nul
    goto :check_backend
)
echo 警告: 后端服务启动可能较慢，继续启动前端...

:start_frontend
:: 启动前端
echo 正在启动前端服务...
cd /d "%~dp0frontend"
start /b "" npm run dev

:: 等待前端启动
echo 等待前端服务启动...
set WAIT_COUNT=0
:check_frontend
curl -s http://localhost:5173 >nul 2>&1
if %errorlevel% equ 0 (
    echo 前端服务启动成功!
    goto :open_browser
)
set /a WAIT_COUNT+=1
if %WAIT_COUNT% lss %MAX_WAIT% (
    timeout /t 1 /nobreak >nul
    goto :check_frontend
)
echo 警告: 前端服务启动可能较慢，请稍候...

:open_browser
:: 自动打开浏览器
echo 正在打开浏览器...
timeout /t 2 /nobreak >nul
start http://localhost:5173

echo.
echo ==========================================
echo   服务已启动，浏览器已打开
echo   前端地址: http://localhost:5173
echo   后端地址: http://localhost:8000
echo   API文档:  http://localhost:8000/docs
echo   关闭此窗口将停止应用
echo ==========================================
echo.

:: 保持窗口打开，等待用户操作
echo 按任意键停止应用...
pause >nul

:: 停止进程
echo 正在停止服务...
taskkill /f /im node.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1

echo 应用已停止
timeout /t 2 /nobreak >nul
exit /b 0

:exit_script
echo 已取消
pause
exit /b 1
