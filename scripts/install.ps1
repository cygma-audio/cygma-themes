# Arguments are forwarded unchanged, including repeated --app/--variant flags.
$ErrorActionPreference = 'Stop'
$installerPath = Join-Path $PSScriptRoot 'install.py'
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $installerPath @args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python $installerPath @args
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    & python3 $installerPath @args
} else {
    Write-Error 'Cygma requires Python 3.10 or newer.'
    exit 1
}
exit $LASTEXITCODE
