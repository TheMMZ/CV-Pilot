Set-Location -LiteralPath $PSScriptRoot
$cvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $cvPython)) {
    python -m venv .venv
    & $cvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& $cvPython scripts/setup_env.py
docker compose up -d --wait postgres
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $cvPython scripts/migrate_sqlite.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $cvPython run.py
