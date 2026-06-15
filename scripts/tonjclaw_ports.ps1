# TonjClaw port helpers (5000 backend, 5173/5174 vite)
$ErrorActionPreference = 'SilentlyContinue'

$script:TonjClawPorts = @(
    @{ Port = 5000; Label = 'Flask backend' }
    @{ Port = 5173; Label = 'Vite frontend (preferred)' }
    @{ Port = 5174; Label = 'Vite frontend (alternate)' }
)

function Get-TonjClawPortConflicts {
    $rows = @()
    foreach ($def in $script:TonjClawPorts) {
        $port = [int]$def.Port
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if (-not $conns) { continue }
        $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($pid in $pids) {
            if (-not $pid) { continue }
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            $rows += [PSCustomObject]@{
                Port  = $port
                Label = $def.Label
                PID   = $pid
                Name  = if ($proc) { $proc.ProcessName } else { 'unknown' }
            }
        }
    }
    return $rows
}

function Stop-TonjClawPortListeners {
    foreach ($def in $script:TonjClawPorts) {
        Get-NetTCPConnection -LocalPort $def.Port -State Listen -ErrorAction SilentlyContinue |
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    }
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match 'main\.py' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
        Where-Object { $_.CommandLine -match 'tonjclaw-web' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

function Show-TonjClawPortConflictDialog {
    param([array]$Conflicts)
    $lines = ($Conflicts | ForEach-Object {
        "  Port $($_.Port) ($($_.Label)): $($_.Name) PID $($_.PID)"
    }) -join "`n"
    $msg = @"
检测到以下端口已被占用，可能导致 TonjClaw 桌面端无法启动：

$lines

是否关闭上述进程并释放端口？
（选择「否」将取消本次启动）
"@
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $result = [System.Windows.Forms.MessageBox]::Show(
        $msg,
        'TonjClaw - Port conflict',
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Warning
    )
    return ($result -eq [System.Windows.Forms.DialogResult]::Yes)
}

function Resolve-TonjClawPortConflicts {
    param([switch]$Force)
    $conflicts = @(Get-TonjClawPortConflicts)
    if ($conflicts.Count -eq 0) { return $true }
    if ($Force) {
        Stop-TonjClawPortListeners
        return $true
    }
    $ok = Show-TonjClawPortConflictDialog -Conflicts $conflicts
    if (-not $ok) { return $false }
    Stop-TonjClawPortListeners
    return $true
}
