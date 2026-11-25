param([ValidateSet('build','push','status','download')][string]$Action = 'build')
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONWARNINGS = 'ignore'
$env:PYTHONDONTWRITEBYTECODE = '1'
$TaskKaggleRoot = $PSScriptRoot
$TaskSettings = Get-Content -LiteralPath (Join-Path $TaskKaggleRoot 'settings.json') -Raw | ConvertFrom-Json
$TaskCli = (Get-Command kaggle -ErrorAction Stop).Source
$TaskPython = Join-Path (Split-Path (Split-Path $TaskCli -Parent) -Parent) 'python.exe'
$TaskKernel = "$($TaskSettings.username)/$($TaskSettings.kernel_slug)"
if ($Action -in @('build','push')) {
    & $TaskPython -B (Join-Path $TaskKaggleRoot 'build.py')
    if ($LASTEXITCODE -ne 0) { throw 'Kaggle build failed' }
}
if ($Action -eq 'push') {
    $TaskAccount = & $TaskPython -B -c "from kaggle import api; print(api.get_config_value('username'))"
    if ($LASTEXITCODE -ne 0 -or $TaskAccount.Trim() -ne $TaskSettings.username) { throw 'Authenticated Kaggle account differs from settings.username' }
    Write-Output "Authenticated Kaggle account: $TaskAccount"
    $TaskDataset = "$($TaskSettings.username)/$($TaskSettings.dataset_slug)"
    & $TaskCli datasets status $TaskDataset *> $null
    if ($LASTEXITCODE -eq 0) {
        & $TaskCli datasets version -p (Join-Path $TaskKaggleRoot 'build/input-dataset') -m 'Pilot50 prompt3.7: preserve reviewed coverage, inventory methods and introduced artifacts on dual T4' --dir-mode zip
    } else {
        & $TaskCli datasets create -p (Join-Path $TaskKaggleRoot 'build/input-dataset') --dir-mode zip
    }
    if ($LASTEXITCODE -ne 0) { throw 'Kaggle input upload failed' }
    $TaskDatasetReady = $false
    for ($TaskAttempt = 0; $TaskAttempt -lt 60; $TaskAttempt++) {
        $TaskDatasetStatus = & $TaskCli datasets status $TaskDataset
        if ($LASTEXITCODE -eq 0 -and ($TaskDatasetStatus -join ' ') -match '^\s*ready\s*$') {
            $TaskDatasetReady = $true
            break
        }
        Start-Sleep -Seconds 10
    }
    if (-not $TaskDatasetReady) { throw 'Kaggle dataset not ready; kernel was not pushed' }
    & $TaskCli kernels push -p (Join-Path $TaskKaggleRoot 'build/kernel') --accelerator $TaskSettings.accelerator
    if ($LASTEXITCODE -ne 0) { throw 'Kaggle kernel push failed' }
}
if ($Action -eq 'status') {
    & $TaskCli kernels status $TaskKernel
    if ($LASTEXITCODE -ne 0) { throw 'Kaggle status failed' }
}
if ($Action -eq 'download') {
    & $TaskCli kernels output $TaskKernel -p (Join-Path (Split-Path $TaskKaggleRoot -Parent) 'downloads') -o
    if ($LASTEXITCODE -ne 0) { throw 'Kaggle download failed' }
}
