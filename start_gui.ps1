param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$GuiPath = Join-Path $PSScriptRoot "start_gui.py"
& $Python $GuiPath
exit $LASTEXITCODE
