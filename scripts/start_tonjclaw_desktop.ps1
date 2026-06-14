# Start TonjClaw desktop (alias for restart with conflict check)
param([switch]$Force)
& "$PSScriptRoot\restart_tonjclaw_desktop.ps1" @PSBoundParameters
