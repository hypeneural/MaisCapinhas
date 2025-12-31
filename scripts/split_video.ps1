param(
    [Parameter(Mandatory = $true)]
    [string]$Input,
    [Parameter(Mandatory = $true)]
    [string]$OutputDir,
    [Parameter(Mandatory = $true)]
    [string]$BaseTime,
    [int]$SegmentMinutes = 5,
    [int]$Fps = 8,
    [string]$Scale = "640:-2"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path $Input)) {
    throw "Input not found: $Input"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$segmentSeconds = $SegmentMinutes * 60
$segmentPattern = Join-Path $OutputDir "seg_%03d.mp4"

& ffmpeg -hide_banner -y `
    -i $Input `
    -vf "scale=$Scale,fps=$Fps" `
    -c:v libx264 -preset veryfast -crf 28 -pix_fmt yuv420p `
    -an `
    -f segment -segment_time $segmentSeconds -reset_timestamps 1 `
    $segmentPattern | Out-Null

$files = Get-ChildItem -Path $OutputDir -Filter "seg_*.mp4" | Sort-Object Name
$start = [TimeSpan]::Parse($BaseTime)
$i = 0

foreach ($file in $files) {
    $segStart = $start + [TimeSpan]::FromSeconds($i * $segmentSeconds)
    $segEnd = $segStart + [TimeSpan]::FromSeconds($segmentSeconds)
    $name = "{0:hh\\-mm\\-ss}__{1:hh\\-mm\\-ss}.mp4" -f $segStart, $segEnd
    Rename-Item -Path $file.FullName -NewName $name
    $i += 1
}

Write-Output "Segments saved to: $OutputDir"
