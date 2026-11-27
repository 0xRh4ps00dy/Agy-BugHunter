param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string[]]$Target,
    [string]$ScopeFile = "scope.md"
)

$pythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = @("py", "-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = @("python")
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = @("python3")
} else {
    Write-Error "Python 3.9+ not found in PATH."
    exit 1
}

$scriptPath = Join-Path $PSScriptRoot "validate_scope.py"
$argList = @($scriptPath, "--scope", $ScopeFile)
foreach ($t in $Target) {
    $argList += @("--target", $t)
}

if ($pythonCmd.Count -eq 2) {
    & $pythonCmd[0] $pythonCmd[1] @argList
} else {
    & $pythonCmd[0] @argList
}
exit $LASTEXITCODE
