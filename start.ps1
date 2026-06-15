param(
    [switch]$SkipMilvus,
    [switch]$MilvusLogs,
    [switch]$Check
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

function Test-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Start-LoggedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string]$Arguments,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][ConsoleColor]$Color
    )

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $FilePath
    $psi.Arguments = $Arguments
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $psi
    $process.EnableRaisingEvents = $true

    $metadata = @{ Name = $Name; Color = $Color }
    $outputEvent = Register-ObjectEvent `
        -InputObject $process `
        -EventName OutputDataReceived `
        -MessageData $metadata `
        -Action {
            if ($EventArgs.Data) {
                Write-Host "[$($Event.MessageData.Name)] $($EventArgs.Data)" `
                    -ForegroundColor $Event.MessageData.Color
            }
        }
    $errorEvent = Register-ObjectEvent `
        -InputObject $process `
        -EventName ErrorDataReceived `
        -MessageData $metadata `
        -Action {
            if ($EventArgs.Data) {
                Write-Host "[$($Event.MessageData.Name)] $($EventArgs.Data)" `
                    -ForegroundColor $Event.MessageData.Color
            }
        }

    [void]$process.Start()
    $process.BeginOutputReadLine()
    $process.BeginErrorReadLine()

    [pscustomobject]@{
        Name = $Name
        Process = $process
        Events = @($outputEvent, $errorEvent)
    }
}

if ($Check) {
    Write-Host "[check] start.ps1 loaded successfully" -ForegroundColor Green
    exit 0
}

Write-Host "[start] Travel Assistant dev services" -ForegroundColor Green

if (-not $env:DASHSCOPE_API_KEY) {
    Write-Host "[warn] DASHSCOPE_API_KEY is not set. Knowledge base calls will fail." `
        -ForegroundColor Yellow
}

if (-not $SkipMilvus) {
    if (-not (Test-Command docker)) {
        Write-Host "[warn] Docker was not found. Skip Milvus startup." `
            -ForegroundColor Yellow
    } else {
        Write-Host "[milvus] docker compose up -d --pull never" `
            -ForegroundColor DarkCyan
        docker compose -f docker-compose.milvus.yml up -d --pull never
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[warn] Milvus startup failed. Check local image tags with: docker images" `
                -ForegroundColor Yellow
            Write-Host "[warn] Set MILVUS_IMAGE/MINIO_IMAGE/ETCD_IMAGE if your local tags differ from docker-compose.milvus.yml." `
                -ForegroundColor Yellow
            Write-Host "[warn] Backend and frontend will still start, but knowledge-base queries may fail until Milvus is ready." `
                -ForegroundColor Yellow
        }
    }
}

if (-not (Test-Command uv)) {
    throw "uv was not found in PATH. Install uv first: https://docs.astral.sh/uv/"
}
if (-not (Test-Command npm)) {
    throw "npm was not found in PATH. Install Node.js first: https://nodejs.org/"
}
if (-not (Test-Command node)) {
    throw "node was not found in PATH. Install Node.js first: https://nodejs.org/"
}

$services = @()
$frontendDir = Join-Path $Root "frontend"

Write-Host "[backend] uv sync --locked" -ForegroundColor Cyan
uv sync --locked
if ($LASTEXITCODE -ne 0) {
    throw "uv sync --locked failed"
}

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "[frontend] npm install" -ForegroundColor Magenta
    Push-Location $frontendDir
    try {
        npm install
        if ($LASTEXITCODE -ne 0) {
            throw "npm install failed"
        }
    } finally {
        Pop-Location
    }
}

try {
    $services += Start-LoggedProcess `
        -Name "backend" `
        -FilePath "uv" `
        -Arguments "run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000" `
        -WorkingDirectory $Root `
        -Color Cyan

    $services += Start-LoggedProcess `
        -Name "frontend" `
        -FilePath "node" `
        -Arguments "node_modules\vite\bin\vite.js --host 0.0.0.0" `
        -WorkingDirectory $frontendDir `
        -Color Magenta

    if ($MilvusLogs -and (Test-Command docker)) {
        $services += Start-LoggedProcess `
            -Name "milvus" `
            -FilePath "cmd.exe" `
            -Arguments '/d /s /c "docker compose -f docker-compose.milvus.yml logs -f milvus"' `
            -WorkingDirectory $Root `
            -Color DarkGray
    }

    Write-Host ""
    Write-Host "[ready] Logs are streaming in this terminal. Press Ctrl+C to stop app logs." `
        -ForegroundColor Green
    Write-Host "[url] Frontend: http://localhost:5173"
    Write-Host "[url] Backend:  http://localhost:8000"
    Write-Host "[url] Milvus:   http://localhost:19530"
    Write-Host ""

    while ($true) {
        Start-Sleep -Milliseconds 500
        foreach ($service in $services) {
            if ($service.Process.HasExited) {
                $code = $service.Process.ExitCode
                throw "$($service.Name) exited with code $code"
            }
        }
    }
} finally {
    Write-Host ""
    Write-Host "[stop] Stopping child processes..." -ForegroundColor Yellow
    foreach ($service in $services) {
        if (-not $service.Process.HasExited) {
            taskkill /PID $service.Process.Id /T /F > $null 2>&1
        }
        foreach ($eventSub in $service.Events) {
            Unregister-Event -SubscriptionId $eventSub.Id -ErrorAction SilentlyContinue
        }
        $service.Process.Dispose()
    }
}
