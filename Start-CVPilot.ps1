$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$cvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $cvPython)) {
    python -m venv .venv
}
& $cvPython -c "import streamlit, psycopg, fastapi, reportlab, playwright"
if ($LASTEXITCODE -ne 0) {
    & $cvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& $cvPython scripts/setup_env.py
$cvPorts = (& $cvPython -c "import cvpilot,os,json; print(json.dumps({'landing':int(os.getenv('LANDING_PORT','4317')),'workspace':int(os.getenv('STREAMLIT_PORT','8501'))}))") | ConvertFrom-Json
$cvLanding = "http://127.0.0.1:$($cvPorts.landing)"
$cvWorkspace = "http://127.0.0.1:$($cvPorts.workspace)"
function Test-CVPilotReady {
    try {
        $cvHealth = Invoke-RestMethod "$cvLanding/health" -TimeoutSec 3
        $cvStHealth = Invoke-WebRequest "$cvWorkspace/_stcore/health" -UseBasicParsing -TimeoutSec 3
        return ($cvHealth.ok -eq $true -and $cvStHealth.StatusCode -eq 200)
    } catch { return $false }
}
if (Test-CVPilotReady) {
    Write-Output "CV Pilot is already running: $cvLanding"
    exit 0
}
function Test-CVDockerReady {
    try {
        docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}
if (-not (Test-CVDockerReady)) {
    $cvDockerDesktop = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
    if (Test-Path -LiteralPath $cvDockerDesktop) {
        Start-Process -FilePath $cvDockerDesktop -WindowStyle Hidden
        for ($cvTry = 0; $cvTry -lt 60; $cvTry++) {
            Start-Sleep -Seconds 1
            if (Test-CVDockerReady) { break }
        }
    }
}
docker compose up -d --wait postgres
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL could not start. Check Docker Desktop.' }
& $cvPython scripts/migrate_sqlite.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$cvListeners = Get-NetTCPConnection -State Listen -LocalPort $cvPorts.landing,$cvPorts.workspace -ErrorAction SilentlyContinue
if ($cvListeners) { throw 'A web port is already in use, but the app is not healthy. Check the existing service before starting another copy.' }
$cvLogs = Join-Path $PSScriptRoot 'data'
New-Item -ItemType Directory -Force -Path $cvLogs | Out-Null
$cvService = Start-Process -FilePath $cvPython -ArgumentList 'run.py' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $cvLogs 'service.log') -RedirectStandardError (Join-Path $cvLogs 'service-error.log') -PassThru
Set-Content -LiteralPath (Join-Path $cvLogs 'service.pid') -Value $cvService.Id
for ($cvTry = 0; $cvTry -lt 30; $cvTry++) {
    if (Test-CVPilotReady) {
        Write-Output "CV Pilot is running in the background: $cvLanding"
        Write-Output "Workspace: $cvWorkspace"
        exit 0
    }
    $cvService.Refresh()
    if ($cvService.HasExited) { break }
    Start-Sleep -Seconds 1
}
throw 'CV Pilot did not become ready. See data/service-error.log for details.'
