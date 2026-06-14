@echo off
chcp 65001 >nul
echo ========================================
echo   桌面端应用（本地业务系统）
echo ========================================
echo.
echo 功能:
echo   - 订单管理（CRUD、批量圈选）
echo   - 商品管理（快捷码、价格）
echo   - 客户管理（线路、销售员）
echo   - 机器人配置（Hook、回复规则）
echo   - 数据看板与报表导出
echo   - 规则配置与导入
echo.
echo 访问地址:
echo   - Vue桌面端: http://localhost:5173/desktop (开发模式)
echo   - 后端API: http://localhost:5000/api
echo.
echo 注意:
echo   - 前端开发服务器需单独启动: cd tonjclaw-web ^&^& npm run dev
echo   - 或使用构建后的静态文件
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python,请先安装Python 3.8+
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖包...
    pip install -r requirements.txt
)

echo [2/3] 检查配置文件...
if not exist .env (
    echo [警告] 未找到.env配置文件
    echo [提示] 请复制 .env.example 为 .env 并修改配置
    echo [提示] 桌面端建议使用 SQLite (DB_TYPE=sqlite)
    pause
)

echo [3/3] 启动后端服务...
echo.
set APP_MODE=desktop
python main.py

echo.
echo 后端API已启动: http://localhost:5000
echo 请单独启动前端开发服务器: cd tonjclaw-web ^&^& npm run dev
pause
