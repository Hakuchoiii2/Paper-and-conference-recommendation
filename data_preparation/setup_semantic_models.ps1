$ErrorActionPreference = "Stop"

$pythonCommand = Get-Command py -ErrorAction SilentlyContinue
if ($pythonCommand) {
    $script:PythonExecutable = $pythonCommand.Source
    $script:PythonPrefix = @("-3.11")
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python 3.11 was not found. Install Python 3.11, then rerun this script."
    }
    $script:PythonExecutable = $pythonCommand.Source
    $script:PythonPrefix = @()
}

function Invoke-ProjectPython {
    param([string[]]$Arguments)
    $invokeArguments = $script:PythonPrefix + $Arguments
    & $script:PythonExecutable @invokeArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE."
    }
}

$testArguments = $script:PythonPrefix + @("-c", "import sentence_transformers")
& $script:PythonExecutable @testArguments
if ($LASTEXITCODE -ne 0) {
    $install = Read-Host "sentence-transformers is missing. Install it into this Python 3.11 environment? [y/N]"
    if ($install -notmatch "^(y|yes)$") {
        throw "Setup cancelled. Install sentence-transformers before running the pipeline."
    }
    Invoke-ProjectPython -Arguments @("-m", "pip", "install", "sentence-transformers")
}

Write-Host "Downloading/checking all-MiniLM-L6-v2 for local use..."
Invoke-ProjectPython -Arguments @(
    "-c",
    "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('all-MiniLM-L6-v2'); print('Embedding dimension:', model.get_sentence_embedding_dimension())"
)

$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaCommand) {
    throw "Ollama is not installed or not on PATH. Install Ollama from https://ollama.com/download, reopen PowerShell, then rerun this script."
}

$ollamaExecutable = $ollamaCommand.Source
$ollamaReady = $false
try {
    $null = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2
    $ollamaReady = $true
} catch {
    Start-Process -FilePath $ollamaExecutable -ArgumentList @("serve") -WindowStyle Hidden
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 1
        try {
            $null = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2
            $ollamaReady = $true
            break
        } catch {
            continue
        }
    }
}

if (-not $ollamaReady) {
    throw "Ollama did not become available at http://localhost:11434. Start Ollama and rerun this script."
}

Write-Host "Downloading/checking Qwen3 4B through Ollama..."
& $ollamaExecutable pull qwen3:4b
if ($LASTEXITCODE -ne 0) {
    throw "ollama pull qwen3:4b failed with exit code $LASTEXITCODE."
}

Write-Host "Model setup complete. This script did not run the data-preparation pipeline."
