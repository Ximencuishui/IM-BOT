@echo off
chcp 65001 >nul
title TonjClaw 桌面端
setlocal enabledelayedexpansion

echo ========================================
echo   桌面端应用（本地业务系统）
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python,请先安装Python 3.8+
    pause
    exit /b 1
)

REM 设置桌面端模式
set APP_MODE=desktop
set TONJCLAW_SKIP_SCHEDULER=1

REM 检查并安装依赖
echo [1/3] 检查Python依赖...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo [..] 正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
    echo [OK] 依赖安装完成
) else (
    echo [OK] 依赖已就绪
)

REM 检查配置文件
echo [2/3] 检查配置...
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo [OK] 已从模板创建 .env 配置文件
    ) else (
        echo [警告] 未找到 .env 配置文件
    )
) else (
    echo [OK] 配置文件就绪
)

REM 检查日志目录
if not exist logs mkdir logs

REM 启动后端服务
echo [3/3] 启动后端服务...
echo.
echo 访问地址:
echo   - 后端API: http://localhost:5000/api
echo   - 健康检查: http://localhost:5000/health
echo   - 就绪检查: http://localhost:5000/health/ready
echo.
echo 前端开发服务器请单独启动: cd tonjclaw-web ^&^& npm run dev
echo.

python main.py

if errorlevel 1 (
    echo [错误] 后端服务异常退出，请查看 logs/ 目录下的日志文件
    pause
)

endlocal