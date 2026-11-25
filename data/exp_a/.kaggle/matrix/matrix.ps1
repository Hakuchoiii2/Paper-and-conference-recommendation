param([ValidateSet('build','push','status','download')][string]$Action = 'build')
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$TaskMatrixRoot = $PSScriptRoot
$TaskMatrixCli = (Get-Command kaggle -ErrorAction Stop).Source
$TaskMatrixPython = Join-Path (Split-Path (Split-Path $TaskMatrixCli -Parent) -Parent) 'python.exe'
$TaskMatrixKernel = 'htnkhi/exp-a-qwen-facet-matrix'
$TaskMatrixDataset = 'htnkhi/exp-a-qwen-facet-matrix-inputs'
if ($Action -in @('build','push')) {
    & $TaskMatrixPython -X utf8 -B (Join-Path $TaskMatrixRoot 'build_matrix.py')
    if ($LASTEXITCODE -ne 0) { throw 'Matrix build failed' }
}
if ($Action -eq 'push') {
    $TaskMatrixAccount = & $TaskMatrixPython -B -c "from kaggle import api; print(api.get_config_value('username'))"
    if ($LASTEXITCODE -ne 0 -or $TaskMatrixAccount.Trim() -ne 'htnkhi') { throw 'Kaggle account differs from htnkhi' }
    & $TaskMatrixCli datasets status $TaskMatrixDataset *> $null
    if ($LASTEXITCODE -eq 0) {
        & $TaskMatrixCli datasets version -p (Join-Path $TaskMatrixRoot 'build_matrix/input-dataset') -m 'Paired 4B 8B original source-first method contribution; frozen AI reference' --dir-mode zip
    } else {
        & $TaskMatrixCli datasets create -p (Join-Path $TaskMatrixRoot 'build_matrix/input-dataset') --dir-mode zip
    }
    if ($LASTEXITCODE -ne 0) { throw 'Matrix input upload failed' }
    $TaskMatrixReady = $false
    for ($TaskMatrixAttempt = 0; $TaskMatrixAttempt -lt 60; $TaskMatrixAttempt++) {
        $TaskMatrixStatus = & $TaskMatrixCli datasets status $TaskMatrixDataset
        if ($LASTEXITCODE -eq 0 -and ($TaskMatrixStatus -join ' ') -match '^\s*ready\s*$') {
            $TaskMatrixReady = $true
            break
        }
        Start-Sleep -Seconds 10
    }
    if (-not $TaskMatrixReady) { throw 'Matrix input not ready; kernel was not pushed' }
    & $TaskMatrixCli kernels push -p (Join-Path $TaskMatrixRoot 'build_matrix/kernel') --accelerator NvidiaTeslaT4
    if ($LASTEXITCODE -ne 0) { throw 'Matrix kernel push failed' }
}
if ($Action -eq 'status') {
    & $TaskMatrixCli kernels status $TaskMatrixKernel
    if ($LASTEXITCODE -ne 0) { throw 'Matrix status failed' }
}
if ($Action -eq 'download') {
    $TaskMatrixRunName = 'run_' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '_' + [Guid]::NewGuid().ToString('N').Substring(0,8)
    $TaskMatrixDownload = Join-Path (Join-Path $TaskMatrixRoot 'matrix_downloads') $TaskMatrixRunName
    & $TaskMatrixCli kernels output $TaskMatrixKernel -p $TaskMatrixDownload
    if ($LASTEXITCODE -ne 0) { throw 'Matrix download failed' }
    Write-Output "Saved this attempt separately: $TaskMatrixDownload"
}
