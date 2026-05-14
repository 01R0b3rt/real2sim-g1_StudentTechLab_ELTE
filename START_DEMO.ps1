$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

Write-Host ""
Write-Host "Real2Sim G1 demo launcher"
Write-Host ""
Write-Host "  1  Stable two-arm demo for submission"
Write-Host "  2  Experimental full-body demo"
Write-Host ""
$choice = Read-Host "Choose demo [1/2]"

if ($choice -eq "2") {
    & (Join-Path $PSScriptRoot "START_FULL_BODY.bat")
} else {
    & (Join-Path $PSScriptRoot "START_ARMS_ONLY.bat")
}
