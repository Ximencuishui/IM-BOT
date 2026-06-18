$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appDir = Join-Path $rootDir "sim-bot-app"
$nodeExe = Join-Path $rootDir "nodejs" "node.exe"

Write-Host "Sim.Bot 桌面客户端正在启动..." -ForegroundColor Green
Write-Host ""

# 设置环境变量
$env:SIM_BOT_ROOT = $appDir.Replace("\", "/")

# 切换到应用目录
Set-Location $appDir

# 检查 node_modules
if (-not (Test-Path "node_modules")) {
    Write-Host "[首次部署] 正在安装依赖..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] 依赖安装失败，请手动执行 npm install" -ForegroundColor Red
        pause
        exit 1
    }
    Write-Host "[完成] 依赖安装成功" -ForegroundColor Green
}

Write-Host "[启动] 正在启动服务..." -ForegroundColor Cyan
& $nodeExe src/server.js

pause