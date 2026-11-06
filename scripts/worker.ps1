$ErrorActionPreference = 'Stop'
$atlasRoot = Split-Path $PSScriptRoot -Parent
$atlasNode = Join-Path $atlasRoot '.tools/node/node-v22.16.0-win-x64'
$env:TEMP = Join-Path $atlasRoot '.cache/tmp'
$env:TMP = $env:TEMP
$env:npm_config_cache = Join-Path $atlasRoot '.cache/npm'
$env:XDG_CACHE_HOME = Join-Path $atlasRoot '.cache'
$env:WRANGLER_SEND_METRICS = 'false'
$env:PATH = $atlasNode + ';' + $env:PATH
Set-Location (Join-Path $atlasRoot 'worker')
& (Join-Path $atlasNode 'node.exe') (Join-Path $atlasNode 'node_modules/npm/bin/npm-cli.js') @args
exit $LASTEXITCODE
