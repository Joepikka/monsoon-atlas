# Single local CAP capture; never enables scheduling or publication.
$ErrorActionPreference = 'Stop'
$atlasRoot = Split-Path -Parent $PSScriptRoot
$env:TEMP = Join-Path $atlasRoot '.cache/tmp'
$env:TMP = $env:TEMP
$env:PYTHONUTF8 = '1'
Set-Location -LiteralPath $atlasRoot
& (Join-Path $atlasRoot '.venv/Scripts/python.exe') -m atlas.ingest.s09_collect @args
exit $LASTEXITCODE
