$ErrorActionPreference = 'Stop'
$taskPython = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '.venv/Scripts/python.exe')).Path
$taskPidFile = Join-Path $PSScriptRoot '.runtime/npc.pid'
New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot '.runtime') -Force | Out-Null
$taskExisting = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -like '*npc_worker.py*' -and $_.ExecutablePath -eq $taskPython }
if ($taskExisting) { Write-Output 'NPC worker already running.'; exit 0 }
$taskWorker = Start-Process -FilePath $taskPython -ArgumentList '-u','npc_worker.py' -WorkingDirectory $PSScriptRoot -RedirectStandardOutput (Join-Path $PSScriptRoot '.runtime/npc-out.log') -RedirectStandardError (Join-Path $PSScriptRoot '.runtime/npc-error.log') -WindowStyle Hidden -PassThru
$taskWorker.Id | Set-Content -LiteralPath $taskPidFile
Write-Output "NPC worker started: $($taskWorker.Id)"
