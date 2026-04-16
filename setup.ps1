$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Join-Path $BaseDir "MAAT RPG.app\Contents\Resources\maatos\setup.ps1"

if (-not (Test-Path $Target)) {
    Write-Host "❌ MAAT-RPG setup script not found:"
    Write-Host "   $Target"
    exit 1
}

& $Target @args
