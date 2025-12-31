param(
    [Parameter(Mandatory = $true)]
    [string]$Input,
    [string]$StoreCode = "001",
    [string]$CameraCode = "entrance",
    [Parameter(Mandatory = $true)]
    [string]$Date,
    [string]$BaseTime = "00:00:00",
    [int]$SegmentMinutes = 5,
    [int]$Fps = 6,
    [string]$Scale = "480:-2",
    [int]$Workers = 1,
    [string]$OutputJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path $Input)) {
    throw "Input not found: $Input"
}

$outputArg = ""
if ($OutputJson) {
    $outputArg = "--output-json `"$OutputJson`""
}

python -m apps.cli split-process `
  --input-path "$Input" `
  --store-code "$StoreCode" `
  --camera-code "$CameraCode" `
  --date "$Date" `
  --base-time "$BaseTime" `
  --segment-minutes $SegmentMinutes `
  --fps $Fps `
  --scale "$Scale" `
  --workers $Workers `
  $outputArg

Write-Output "Face captures saved under FACES_ROOT (see .env)"
