@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title StockAPP 量化回测平台

cls
echo ==========================================
echo       StockAPP 量化回测平台
echo          (Windows 版本)
echo ==========================================
echo.

cd /d "%~dp0"
set APP_DIR=%~dp0StockAPP

:: 停止已有实例
echo 检查是否有旧实例运行...

:: 停止占用端口8000的进程
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    echo 正在停止后端进程 PID: %%a
    taskkill /f /pid %%a >nul 2>&1
)

:: 停止占用端口5173的进程
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING 2^>nul') do (
    echo 正在停止前端进程 PID: %%a
    taskkill /f /pid %%a >nul 2>&1
)

:: 等待端口释放
timeout /t 2 /nobreak >nul
echo.

echo 工作目录: %cd%
echo.

:: ============================================
:: 查找 Python
:: ============================================
:find_python
echo 检查 Python...
set PYTHON_CMD=

:: 检查常见 Python 路径
for %%p in (
    "python"
    "python3"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "C:\Python39\python.exe"
) do (
    %%p --version >nul 2>&1
    if !errorlevel! equ 0 (
        set PYTHON_CMD=%%p
        goto :python_found
    )
)

:: Python 未找到
echo Python 未找到或版本过低 (需要 3.8+)
echo.
echo 请选择安装方式:
echo   1) 自动下载并安装 Python (推荐)
echo   2) 使用 winget 安装 (Windows 11/10)
echo   3) 手动下载安装
echo   4) 退出
echo.
set /p choice="请输入选择 [1-4]: "

if "%choice%"=="1" goto :download_python
if "%choice%"=="2" goto :winget_python
if "%choice%"=="3" goto :manual_python
if "%choice%"=="4" goto :exit_script
echo 无效选择
goto :exit_script

:download_python
echo.
echo 正在下载 Python...
powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe' -OutFile '%TEMP%\python_installer.exe' -UseBasicParsing }"

if exist "%TEMP%\python_installer.exe" (
    echo 正在安装 Python...
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1
    echo 安装完成，请重新运行此脚本
    del "%TEMP%\python_installer.exe" >nul 2>&1
    pause
    exit /b 0
) else (
    echo 下载失败，请手动安装
    goto :manual_python
)

:winget_python
where winget >nul 2>&1
if !errorlevel! neq 0 (
    echo winget 不可用，请使用其他安装方式
    goto :download_python
)

echo 正在使用 winget 安装 Python...
winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
echo 安装完成，请重新运行此脚本
pause
exit /b 0

:manual_python
echo.
echo 请手动下载并安装 Python 3.8 或更高版本:
echo   https://www.python.org/downloads/
echo.
echo 安装时请勾选 "Add Python to PATH"
echo.
pause
exit /b 0

:python_found
for /f "tokens=2" %%v in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%v
echo 使用 Python: %PYTHON_VERSION%
echo.

:: ============================================
:: 查找 Node.js
:: ============================================
:find_node
echo 检查 Node.js...
set NODE_CMD=

:: 检查常见 Node.js 路径
for %%p in (
    "node"
    "%ProgramFiles%\nodejs\node.exe"
    "%LOCALAPPDATA%\Programs\node\node.exe"
    "%USERPROFILE%\.trae-cn\binaries\node\versions\24.13.1\bin\node.exe"
) do (
    %%p --version >nul 2>&1
    if !errorlevel! equ 0 (
        set NODE_CMD=%%p
        goto :node_found
    )
)

:: Node.js 未找到
echo Node.js 未找到
echo.
echo 请选择安装方式:
echo   1) 自动下载并安装 Node.js (推荐)
echo   2) 使用 winget 安装 (Windows 11/10)
echo   3) 手动下载安装
echo   4) 退出
echo.
set /p choice="请输入选择 [1-4]: "

if "%choice%"=="1" goto :download_node
if "%choice%"=="2" goto :winget_node
if "%choice%"=="3" goto :manual_node
if "%choice%"=="4" goto :exit_script
echo 无效选择
goto :exit_script

:download_node
echo.
echo 正在下载 Node.js LTS...
powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://nodejs.org/dist/v20.10.0/node-v20.10.0-x64.msi' -OutFile '%TEMP%\node_installer.msi' -UseBasicParsing }"

if exist "%TEMP%\node_installer.msi" (
    echo 正在安装 Node.js...
    msiexec /i "%TEMP%\node_installer.msi" /quiet /norestart
    echo 安装完成，请重新运行此脚本
    del "%TEMP%\node_installer.msi" >nul 2>&1
    pause
    exit /b 0
) else (
    echo 下载失败，请手动安装
    goto :manual_node
)

:winget_node
where winget >nul 2>&1
if !errorlevel! neq 0 (
    echo winget 不可用，请使用其他安装方式
    goto :download_node
)

echo 正在使用 winget 安装 Node.js...
winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
echo 安装完成，请重新运行此脚本
pause
exit /b 0

:manual_node
echo.
echo 请手动下载并安装 Node.js LTS 版本:
echo   https://nodejs.org/
echo.
pause
exit /b 0

:node_found
for /f "tokens=1" %%v in ('%NODE_CMD% --version 2^>^&1') do set NODE_VERSION=%%v
echo 使用 Node.js: %NODE_VERSION%
echo.

:: ============================================
:: 检查依赖
:: ============================================
:check_dependencies

echo 检查后端依赖...
cd /d "%APP_DIR%\backend"

set MISSING_DEPS=

for %%d in (fastapi uvicorn pydantic pandas numpy efinance apscheduler sqlalchemy pymysql) do (
    %PYTHON_CMD% -c "import %%d" >nul 2>&1
    if !errorlevel! neq 0 (
        if "!MISSING_DEPS!"=="" (
            set MISSING_DEPS=%%d
        ) else (
            set MISSING_DEPS=!MISSING_DEPS! %%d
        )
    )
)

if not "!MISSING_DEPS!"=="" (
    echo 缺少以下依赖: !MISSING_DEPS!
    echo 正在安装后端依赖，请稍候...
    %PYTHON_CMD% -m pip install -r requirements.txt --quiet --user
    echo 后端依赖安装完成
) else (
    echo 后端依赖已就绪
)

echo 检查前端依赖...
cd /d "%APP_DIR%\frontend"
if not exist "node_modules" (
    echo 正在安装前端依赖，请稍候...
    npm install
)

echo 依赖检查完成
echo.

:: ============================================
:: 启动服务
:: ============================================
:start_services

echo 清理端口...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING 2^>nul') do taskkill /f /pid %%a >nul 2>&1
timeout /t 1 /nobreak >nul

echo 正在启动后端服务...
cd /d "%APP_DIR%\backend"
start "StockAPP Backend" %PYTHON_CMD% run.py

echo 等待后端服务启动...
set WAIT_COUNT=0
:wait_backend
timeout /t 1 /nobreak >nul
set /a WAIT_COUNT+=1
curl -s http://localhost:8000/docs >nul 2>&1
if !errorlevel! equ 0 (
    echo 后端服务启动成功!
    goto :start_frontend
)
if %WAIT_COUNT% lss 15 goto :wait_backend
echo 后端服务启动超时，请检查日志
goto :exit_script

:start_frontend
echo 正在启动前端服务...
cd /d "%APP_DIR%\frontend"
start "StockAPP Frontend" npm run dev

echo 等待前端服务启动...
set WAIT_COUNT=0
:wait_frontend
timeout /t 1 /nobreak >nul
set /a WAIT_COUNT+=1
curl -s http://localhost:5173 >nul 2>&1
if !errorlevel! equ 0 (
    echo 前端服务启动成功!
    goto :open_browser
)
if %WAIT_COUNT% lss 15 goto :wait_frontend
echo 前端服务启动超时，请检查日志
goto :exit_script

:open_browser
timeout /t 2 /nobreak >nul
echo 正在打开浏览器...
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

echo 按任意键停止服务...
pause >nul

:: ============================================
:: 清理
:: ============================================
:cleanup
echo 正在停止服务...
taskkill /f /im node.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1

echo 应用已停止
timeout /t 2 /nobreak >nul
exit /b 0

:exit_script
echo 已取消
pause
exit /b 1
