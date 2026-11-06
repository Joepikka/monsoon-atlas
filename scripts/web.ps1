# Use the plan's portable Node; all caches and browser downloads stay on D.
$ErrorActionPreference = 'Stop'
$atlasRoot = Split-Path -Parent $PSScriptRoot
$atlasNode = Join-Path $atlasRoot '.tools/node/node-v22.16.0-win-x64'
$env:TEMP = Join-Path $atlasRoot '.cache/tmp'
$env:TMP = $env:TEMP
$env:npm_config_cache = Join-Path $atlasRoot '.cache/npm'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $atlasRoot '.cache/ms-playwright'
$env:PATH = $atlasNode + [IO.Path]::PathSeparator + $env:PATH
Set-Location -LiteralPath (Join-Path $atlasRoot 'web')
& (Join-Path $atlasNode 'node.exe') (Join-Path $atlasNode 'node_modules/npm/bin/npm-cli.js') @args
exit $LASTEXITCODE
