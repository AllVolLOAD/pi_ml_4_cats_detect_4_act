param(
    [string]$OutDir = "_export",
    [switch]$IncludeData,
    [switch]$IncludeLogs,
    [switch]$KeepStage
)

$root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$outDirFull = Join-Path $root $OutDir
if (-not (Test-Path -LiteralPath $outDirFull)) {
    New-Item -ItemType Directory -Path $outDirFull | Out-Null
}

$stage = Join-Path $outDirFull "catcam_export_$timestamp"
if (Test-Path -LiteralPath $stage) {
    Remove-Item -Recurse -Force -LiteralPath $stage
}
New-Item -ItemType Directory -Path $stage | Out-Null

$excludeDirs = @(
    (Join-Path $root ".git"),
    (Join-Path $root ".cursor"),
    (Join-Path $root "__pycache__"),
    (Join-Path $root ".pytest_cache"),
    (Join-Path $root "node_modules"),
    (Join-Path $root "dist"),
    (Join-Path $root "build"),
    (Join-Path $root $OutDir),
    (Join-Path $root "catcam\\pc\\__pycache__"),
    (Join-Path $root "catcam\\pc\\roi\\__pycache__")
)

if (-not $IncludeData) {
    $excludeDirs += (Join-Path $root "catcam\\data")
}
if (-not $IncludeLogs) {
    $excludeDirs += (Join-Path $root "catcam\\pc\\logs")
}

$excludeFiles = @(
    "Thumbs.db",
    "Desktop.ini"
)

$robocopyArgs = @(
    $root,
    $stage,
    "/MIR",
    "/R:1",
    "/W:1",
    "/NFL",
    "/NDL",
    "/NJH",
    "/NJS",
    "/XD"
) + $excludeDirs + @("/XF") + $excludeFiles

& robocopy @robocopyArgs | Out-Null

$manifest = @()
$manifest += "catcam export manifest"
$manifest += "timestamp: $timestamp"
$manifest += "include_data: $IncludeData"
$manifest += "include_logs: $IncludeLogs"
$manifest += "root: $root"
$manifest += ""
$manifest += "excluded_dirs:"
$manifest += ($excludeDirs | ForEach-Object { "  - $_" })
$manifest += ""
$manifest += "excluded_files:"
$manifest += ($excludeFiles | ForEach-Object { "  - $_" })

$manifestPath = Join-Path $stage "EXPORT_MANIFEST.txt"
$manifest | Set-Content -LiteralPath $manifestPath -Encoding ASCII

$zipPath = Join-Path $outDirFull "catcam_export_$timestamp.zip"
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -Force -LiteralPath $zipPath
}
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath

if (-not $KeepStage) {
    Remove-Item -Recurse -Force -LiteralPath $stage
}

Write-Host "Export ready: $zipPath"
