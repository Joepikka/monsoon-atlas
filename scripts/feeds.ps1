# Local CAP/weather capture, preparation or checkpoint commands.
$ErrorActionPreference = 'Stop'
$atlasRoot = Split-Path -Parent $PSScriptRoot
$env:TEMP = Join-Path $atlasRoot '.cache/tmp'
$env:TMP = $env:TEMP
$env:PYTHONUTF8 = '1'
Set-Location -LiteralPath $atlasRoot
$atlasModule = 'atlas.ingest.s09_collect'
$atlasArguments = $args
if ($args.Count -gt 0 -and $args[0] -eq 'prepare') {
    $atlasModule = 'atlas.ingest.s09_prepare'
    $atlasArguments = @($args | Select-Object -Skip 1)
}
elseif ($args.Count -gt 0 -and $args[0] -eq 'refresh') {
    $atlasModule = 'atlas.ingest.refresh'
    $atlasArguments = @($args | Select-Object -Skip 1)
}
elseif ($args.Count -gt 0 -and $args[0] -eq 'weather') {
    $atlasModule = 'atlas.ingest.s01_collect'
    $atlasArguments = @($args | Select-Object -Skip 1)
}
elseif ($args.Count -gt 0 -and $args[0] -eq 'weather-prepare') {
    $atlasModule = 'atlas.ingest.s01_prepare'
    $atlasArguments = @($args | Select-Object -Skip 1)
}
elseif ($args.Count -gt 0 -and $args[0] -eq 'upload-local') {
    $atlasModule = 'atlas.ingest.upload'
    $atlasArguments = @($args | Select-Object -Skip 1)
}
elseif ($args.Count -gt 0 -and $args[0] -in @('checkpoint-save', 'checkpoint-restore')) {
    $atlasModule = 'atlas.ingest.checkpoint_bundle'
}
& (Join-Path $atlasRoot '.venv/Scripts/python.exe') -m $atlasModule @atlasArguments
exit $LASTEXITCODE
