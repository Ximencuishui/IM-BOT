# Restart TonjClaw desktop (backend + frontend) with port conflict dialog
param(
    [switch]$Force   # skip dialog, kill occupying processes
)

$Root = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\tonjclaw_ports.ps1"

if (-not (Resolve-TonjClawPortConflicts -Force:$Force)) {
    Write-Host 'Cancelled: ports not released.'
    exit 1
}

$env:APP_MODE = 'all'
$env:TONJCLAW_SKIP_SCHEDULER = '1'
$env:WECHAT_QUIT_BEFORE_INJECT = '1'

Write-Host 'Starting backend http://127.0.0.1:5000 ...'
Start-Process -WorkingDirectory $Root -FilePath 'python' -ArgumentList 'main.py' -WindowStyle Minimized

Start-Sleep -Seconds 3

Write-Host 'Starting frontend (npm run dev) ...'
Start-Process -WorkingDirectory (Join-Path $Root 'tonjclaw-web') -FilePath 'npm' -ArgumentList 'run', 'dev' -WindowStyle Minimized

Start-Sleep -Seconds 3
$vitePort = 5173
if (-not (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue)) {
    if (Get-NetTCPConnection -LocalPort 5174 -State Listen -ErrorAction SilentlyContinue) {
        $vitePort = 5174
    }
}

Write-Host "Backend: http://127.0.0.1:5000"
Write-Host "Frontend: http://localhost:$vitePort/"

if (-not $Force) {
    Add-Type -AssemblyName System.Windows.Forms
    [void][System.Windows.Forms.MessageBox]::Show(
        "TonjClaw desktop started.`n`nBackend: http://127.0.0.1:5000`nFrontend: http://localhost:$vitePort/`n`nLogin: BOSS quick login",
        'TonjClaw',
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    )
}
