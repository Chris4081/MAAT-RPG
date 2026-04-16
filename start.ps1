$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Join-Path $BaseDir "MAAT RPG.app\Contents\Resources\maatos\start.ps1"

if (-not (Test-Path $Target)) {
    Write-Host "❌ MAAT-RPG start script not found:"
    Write-Host "   $Target"
    exit 1
}

& $Target @args
