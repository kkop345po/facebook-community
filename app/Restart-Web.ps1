$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskPython = (Resolve-Path -LiteralPath (Join-Path $taskRoot '.venv/Scripts/python.exe')).Path
$taskRuntime = Join-Path $taskRoot '.runtime'
New-Item -ItemType Directory -Path $taskRuntime -Force | Out-Null
$taskPidPath = Join-Path $taskRuntime 'web.pid'
$taskCommandPattern = '^"?' + [regex]::Escape($taskPython) + '"?\s+server\.py\s*$'
# Windows venv Python can launch a base-interpreter child with the same command.
$taskOldProcesses = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match $taskCommandPattern })
foreach ($taskOld in ($taskOldProcesses | Sort-Object ExecutablePath -Descending)) {
    try { [System.Diagnostics.Process]::GetProcessById([int]$taskOld.ProcessId).Kill() } catch [System.ArgumentException] { } catch [System.InvalidOperationException] { }
}
foreach ($taskOld in $taskOldProcesses) { Wait-Process -Id $taskOld.ProcessId -Timeout 5 -ErrorAction SilentlyContinue }
$taskExpectedBuild = (Get-FileHash -LiteralPath (Join-Path $taskRoot 'server.py') -Algorithm SHA256).Hash.Substring(0,12).ToLowerInvariant()
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList 'server.py' -WorkingDirectory $taskRoot -RedirectStandardOutput (Join-Path $taskRuntime 'web-out.log') -RedirectStandardError (Join-Path $taskRuntime 'web-error.log') -WindowStyle Hidden -PassThru
$taskProcess.Id | Set-Content -LiteralPath $taskPidPath
$taskReady = $false
for ($taskProbe = 0; $taskProbe -lt 20; $taskProbe++) {
    $taskProcess.Refresh()
    if ($taskProcess.HasExited) {
        throw 'Website process exited during startup. Check .runtime/web-error.log.'
    }
    try {
        $taskHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:5080/api/health' -TimeoutSec 2
        if ($taskHealth.status -eq 'ok' -and $taskHealth.database -eq 'postgresql' -and $taskHealth.build -eq $taskExpectedBuild) {
            $taskReady = $true
            break
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}
if (-not $taskReady) {
    throw 'Website did not become healthy. Check .runtime/web-error.log before sharing the URL.'
}
Write-Output "Website and PostgreSQL healthy. Web process: $($taskProcess.Id)"
