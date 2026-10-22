$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv/Scripts/python.exe'
$taskRuntime = Join-Path $taskRoot '.runtime'
New-Item -ItemType Directory -Path $taskRuntime -Force | Out-Null
$taskPgBin = 'C:/Program Files/PostgreSQL/18/bin'
& (Join-Path $taskPgBin 'pg_ctl.exe') -D (Join-Path $taskRoot '.pgdata') status
if ($LASTEXITCODE -ne 0) {
    & (Join-Path $taskPgBin 'pg_ctl.exe') -D (Join-Path $taskRoot '.pgdata') -l (Join-Path $taskRuntime 'postgres.log') start
    if ($LASTEXITCODE -ne 0) { throw 'Could not start project PostgreSQL.' }
}
$taskTunnelPid = Join-Path $taskRuntime 'tunnel.pid'
$taskTunnelLog = Join-Path $taskRuntime 'tunnel-error.log'
$taskTunnel = $null
if (Test-Path -LiteralPath $taskTunnelPid) {
    $taskTunnelId = [int](Get-Content -LiteralPath $taskTunnelPid)
    $taskCandidate = Get-CimInstance Win32_Process -Filter "ProcessId = $taskTunnelId" -ErrorAction SilentlyContinue
    if ($taskCandidate -and $taskCandidate.CommandLine -match 'tunnel.+127\.0\.0\.1:5080') { $taskTunnel = $taskCandidate }
}
if (-not $taskTunnel) {
    $taskNewTunnel = Start-Process -FilePath 'cloudflared.exe' -ArgumentList @('tunnel','--url','http://127.0.0.1:5080','--no-autoupdate','--protocol','http2') -WorkingDirectory $taskRoot -RedirectStandardOutput (Join-Path $taskRuntime 'tunnel-out.log') -RedirectStandardError $taskTunnelLog -WindowStyle Hidden -PassThru
    $taskNewTunnel.Id | Set-Content -LiteralPath $taskTunnelPid
}
$taskUrl = $null
for ($taskAttempt=0; $taskAttempt -lt 30; $taskAttempt++) {
    if (Test-Path -LiteralPath $taskTunnelLog) {
        $taskText = Get-Content -LiteralPath $taskTunnelLog -Raw
        $taskMatch = [regex]::Match($taskText,'https://[a-z0-9-]+\.trycloudflare\.com')
        if ($taskMatch.Success) { $taskUrl = $taskMatch.Value; break }
    }
    Start-Sleep -Seconds 1
}
if (-not $taskUrl) { throw 'Tunnel URL unavailable. Check .runtime/tunnel-error.log.' }
Push-Location $taskRoot
try {
    & $taskPython 'manage.py' 'set-url' $taskUrl
    if ($LASTEXITCODE -ne 0) { throw 'Could not save public URL.' }
    & (Join-Path $taskRoot 'Restart-Web.ps1')
} finally { Pop-Location }
Write-Output "Public test URL: $taskUrl"
& (Join-Path $taskRoot 'Start-Npc.ps1')
Write-Output 'Keep this computer online. Tester credentials are in TEST-ACCESS.md.'
