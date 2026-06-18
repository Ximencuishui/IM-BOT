@echo off
chcp 65001 >nul
echo Sim.Bot 桌面客户端正在启动...
echo.

set "SIM_BOT_ROOT=%~dp0sim-bot-app"
set "SIM_BOT_ROOT=%SIM_BOT_ROOT:\=/%"

cd /d "%~dp0sim-bot-app"

if not exist "node_modules" (
    echo [首次部署] 正在安装依赖...
    call npm install
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请手动执行 npm install
        pause
        exit /b 1
    )
    echo [完成] 依赖安装成功
)

echo [启动] 正在启动服务...
"..\nodejs\node.exe" src/server.js

pause