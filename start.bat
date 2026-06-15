@echo off
chcp 65001 >nul
echo ========================================
echo   本地化配送服务商智能订货统计工具
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python,请先安装Python 3.8+
    pause
    exit /b 1
)

echo [1/4] 检查依赖...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo [2/4] 检查MySQL连接配置...
if not exist .env (
    echo [警告] 未找到.env配置文件,请复制.env.example并修改
    echo [提示] copy .env.example .env
    pause
)

echo [3/4] 初始化数据库...
echo [提示] 请手动执行 database/schema.sql 到MySQL

echo [4/4] 启动服务...
echo.
echo 可用服务:
echo   1. HTTP消息接收服务 (core/app.py) - 端口5000
echo   2. TCP消息接收服务 (core/tcp_server.py) - 端口61108
echo   3. 完整业务服务 (main.py) - 端口5000
echo.
set /p choice=请选择要启动的服务 (1/2/3):

if "%choice%"=="1" (
    echo 启动HTTP消息接收服务...
    python core\app.py
) else if "%choice%"=="2" (
    echo 启动TCP消息接收服务...
    python core\tcp_server.py
) else if "%choice%"=="3" (
    echo 启动完整业务服务...
    python main.py
) else (
    echo [错误] 无效选择
    pause
    exit /b 1
)
