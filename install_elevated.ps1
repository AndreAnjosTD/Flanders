# Runs elevated (UAC) to install the Flanders Slack Watch service.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$StateDir = Join-Path $Root "state"
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
$Log = Join-Path $StateDir "install.log"

"=== install started $(Get-Date -Format o) ===" | Out-File $Log -Encoding utf8

& (Join-Path $Root ".venv\Scripts\python.exe") (Join-Path $Root "flanders_service.py") install *>&1 |
    Tee-Object -FilePath $Log -Append

"exit=$LASTEXITCODE" | Add-Content -Path $Log -Encoding utf8
Start-Sleep -Seconds 3
