# Elevated: start (or stop) the Flanders service and report what happened.
param([string]$Action = "start")

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$StateDir = Join-Path $Root "state"
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
$Log = Join-Path $StateDir "service-action.log"

Remove-Item (Join-Path $StateDir "service-boot.log") -ErrorAction SilentlyContinue

"=== $Action $(Get-Date -Format o) ===" | Out-File $Log -Encoding utf8

if ($Action -eq "start") {
    sc.exe start FlandersSlackWatch *>&1 | Tee-Object -FilePath $Log -Append
} elseif ($Action -eq "restart") {
    sc.exe stop FlandersSlackWatch *>&1 | Tee-Object -FilePath $Log -Append
    Start-Sleep -Seconds 4
    sc.exe start FlandersSlackWatch *>&1 | Tee-Object -FilePath $Log -Append
} else {
    sc.exe stop FlandersSlackWatch *>&1 | Tee-Object -FilePath $Log -Append
}

Start-Sleep -Seconds 8
sc.exe queryex FlandersSlackWatch *>&1 | Tee-Object -FilePath $Log -Append

"`n--- boot breadcrumbs ---" | Add-Content $Log
$boot = Join-Path $StateDir "service-boot.log"
if (Test-Path $boot) { Get-Content $boot | Add-Content $Log } else { "NONE" | Add-Content $Log }

"`n--- service log ---" | Add-Content $Log
$svc = Join-Path $StateDir "flanders-service.log"
if (Test-Path $svc) { Get-Content $svc -Tail 20 | Add-Content $Log } else { "NONE" | Add-Content $Log }
