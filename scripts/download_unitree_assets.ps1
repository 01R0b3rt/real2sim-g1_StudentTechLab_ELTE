$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$assetsDir = Join-Path $projectRoot "assets"
$targetDir = Join-Path $assetsDir "unitree_mujoco"
$sceneXml = Join-Path $targetDir "unitree_robots\g1\scene.xml"
$zipPath = Join-Path $assetsDir "unitree_mujoco.zip"
$extractDir = Join-Path $assetsDir "_unitree_extract"
$url = "https://github.com/unitreerobotics/unitree_mujoco/archive/refs/heads/main.zip"

if (Test-Path -LiteralPath $sceneXml) {
    Write-Host "Unitree G1 MuJoCo XML already exists: $sceneXml"
    exit 0
}

New-Item -ItemType Directory -Force -Path $assetsDir | Out-Null

if (Test-Path -LiteralPath $extractDir) {
    Remove-Item -LiteralPath $extractDir -Recurse -Force
}

Write-Host "Downloading:"
Write-Host "  $url"
Write-Host "to:"
Write-Host "  $zipPath"
Invoke-WebRequest -Uri $url -OutFile $zipPath

Write-Host "Extracting archive..."
Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir -Force

$repoDir = Get-ChildItem -LiteralPath $extractDir -Directory | Select-Object -First 1
if ($null -eq $repoDir) {
    throw "Downloaded archive did not contain a repository directory."
}

if (Test-Path -LiteralPath $targetDir) {
    Remove-Item -LiteralPath $targetDir -Recurse -Force
}
Move-Item -LiteralPath $repoDir.FullName -Destination $targetDir

Remove-Item -LiteralPath $extractDir -Recurse -Force
Remove-Item -LiteralPath $zipPath -Force

if (-not (Test-Path -LiteralPath $sceneXml)) {
    throw "Unitree G1 scene.xml was not found after extraction: $sceneXml"
}

Write-Host "Unitree assets ready:"
Write-Host "  $sceneXml"
