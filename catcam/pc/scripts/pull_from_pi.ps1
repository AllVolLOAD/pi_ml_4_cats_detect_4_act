param(
    [string]$PiHost = "mlprojectcat@192.168.1.103",
    [string]$RemoteDir = "/home/pi/catcam_record",
    [string]$LocalDir = (Join-Path $PSScriptRoot "..\..\data\raw_videos")
)

if (-not (Test-Path -LiteralPath $LocalDir)) {
    New-Item -ItemType Directory -Path $LocalDir | Out-Null
}
$LocalDir = (Resolve-Path -LiteralPath $LocalDir).Path

$files = & ssh $PiHost "ls -1 $RemoteDir/*.mp4 2>/dev/null"
if (-not $files) { exit 0 }

foreach ($f in $files) {
    $fileName = [System.IO.Path]::GetFileName($f)
    $localPath = Join-Path $LocalDir $fileName
    & scp "${PiHost}:$f" "$localPath"
    if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $localPath)) {
        & ssh $PiHost "rm -f '$f'"
    }
}
