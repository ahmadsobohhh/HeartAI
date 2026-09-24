param(
    [Parameter(Mandatory = $true)][string]$SlicerPath,
    [string]$CaseId = '788812d5bc03'
)
$ErrorActionPreference = 'Stop'
if ($CaseId -notmatch '^[a-f0-9]{8,32}$') { throw 'Invalid case ID' }
$resolvedSlicer = (Resolve-Path -LiteralPath $SlicerPath).Path
if ([IO.Path]::GetFileName($resolvedSlicer) -ne 'Slicer.exe') { throw 'Select the installed Slicer.exe' }
$projectRoot = Split-Path $PSScriptRoot -Parent
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$caseDir = Join-Path $projectRoot "results\cases\$CaseId"
$packageDir = Join-Path $projectRoot ('results\slicer\' + $CaseId + '-' + [guid]::NewGuid().ToString('N').Substring(0,8))
& $python (Join-Path $PSScriptRoot 'prepare_slicer_case.py') $caseDir $packageDir
if ($LASTEXITCODE -ne 0) { throw 'Review package preparation failed' }
$previousPackage = $env:HEARTAI_SLICER_PACKAGE
try {
    $env:HEARTAI_SLICER_PACKAGE = Join-Path $packageDir 'review_package.json'
    & $resolvedSlicer --python-script (Join-Path $PSScriptRoot 'open_slicer_case.py')
} finally {
    $env:HEARTAI_SLICER_PACKAGE = $previousPackage
}
