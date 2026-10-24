# Flanders local voice setup.
#
# Idempotent: re-running skips steps that are already done.
# Run from the Flanders project root:
#     powershell -ExecutionPolicy Bypass -File scripts\setup_local.ps1
#
# Steps:
#   1. create the Python virtual environment
#   2. install the core runtime requirements
#   3. install PyTorch with CUDA
#   4. install the Fish Speech inference dependencies
#   5. download the Fish Speech 1.5 weights from ModelScope
#   6. convert the reference sample to 44.1 kHz mono WAV
#   7. print a readiness check

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root

$Venv = Join-Path $Root ".venv"
$Py = Join-Path $Venv "Scripts\python.exe"
$Ckpt = Join-Path $Root "fish-speech\checkpoints\fish-speech-1.5"

function Step($name) { Write-Host ""; Write-Host "== $name" -ForegroundColor Cyan }

Step "1/7 virtual environment"
if (-not (Test-Path $Venv)) {
    py -m venv $Venv
} else {
    Write-Host "already present"
}

Step "2/7 core requirements"
& $Py -m pip install -r (Join-Path $Root "requirements.txt")

Step "3/7 PyTorch"
& $Py -c "import torch" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $Py -m pip install torch==2.4.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu124
} else {
    Write-Host "already installed"
}

Step "4/7 inference dependencies"
& $Py -m pip install -r (Join-Path $Root "requirements-local.txt")

Step "5/7 model weights"
New-Item -ItemType Directory -Force -Path $Ckpt | Out-Null
$files = @(
    "config.json",
    "model.pth",
    "firefly-gan-vq-fsq-8x1024-21hz-generator.pth",
    "tokenizer.tiktoken",
    "special_tokens.json"
)
foreach ($file in $files) {
    $dest = Join-Path $Ckpt $file
    if ((Test-Path $dest) -and ((Get-Item $dest).Length -gt 0)) {
        Write-Host "have $file"
        continue
    }
    $url = "https://modelscope.cn/api/v1/models/fishaudio/fish-speech-1.5/repo?Revision=master&FilePath=$file"
    Write-Host "fetch $file"
    curl.exe -L --fail --retry 3 -o $dest $url
}

Step "6/7 reference clip"
if (-not (Test-Path (Join-Path $Root "references\flanders_sample.txt"))) {
    & $Py (Join-Path $Root "scripts\fetch_reference.py")
}
& $Py (Join-Path $Root "scripts\prepare_reference.py")

Step "7/7 readiness"
& $Py (Join-Path $Root "flanders\flanders_local_tts.py") --check
