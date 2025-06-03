<# Сборка winloopcap.exe (single-file) и копирование в app/audio #>

$ErrorActionPreference = "Stop"

Write-Host ">>> dotnet restore"
dotnet restore capture-cli

Write-Host ">>> dotnet publish"
dotnet publish capture-cli `
    -c Release `
    -o capture-cli\publish `
    --self-contained `
    -r win-x64

$src  = "capture-cli\publish\winloopcap.exe"
$dest = "app\audio\winloopcap.exe"

Copy-Item $src $dest -Force
Write-Host " Copied $src → $dest"
