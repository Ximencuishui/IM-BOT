# Stop TonjClaw dev processes
. "$PSScriptRoot\tonjclaw_ports.ps1"
Write-Host 'Stopping TonjClaw...'
Stop-TonjClawPortListeners
Write-Host 'Ports 5000 / 5173 / 5174 released.'
