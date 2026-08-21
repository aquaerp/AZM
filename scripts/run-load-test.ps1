[CmdletBinding()]
param(
    [ValidateRange(1, 1000000)][int]$Records = 100,
    [ValidateRange(1, 128)][int]$Workers = 8,
    [ValidateRange(1024, 65535)][int]$Port = 8001,
    [ValidatePattern('^[a-zA-Z0-9_]+$')][string]$LoadDatabase = 'azm_loadtest',
    [switch]$FullScale
)

$ErrorActionPreference = 'Stop'
if ($Records -gt 1000 -and -not $FullScale) {
    throw 'Runs over 1,000 triplets require -FullScale. The 100,000-triplet scenario creates 300,000 rows.'
}
if (-not $LoadDatabase.StartsWith('azm_loadtest')) {
    throw 'The isolated database name must begin with azm_loadtest.'
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$backend = Join-Path $projectRoot 'backend'
$summary = Join-Path $projectRoot ("tmp\load-test-{0}.json" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (-not (Test-Path $python)) { throw "Python virtual environment was not found at $python" }

function Invoke-Checked { param([scriptblock]$Command); & $Command; if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE." } }

$postgresUser = (& docker compose exec -T postgres printenv POSTGRES_USER).Trim()
if (-not $postgresUser) { throw 'Could not determine the PostgreSQL user from the Docker service.' }
$databaseExists = (& docker compose exec -T postgres psql -U $postgresUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$LoadDatabase'").Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect PostgreSQL databases.' }
if ($databaseExists -ne '1') {
    Invoke-Checked { & docker compose exec -T postgres createdb -U $postgresUser $LoadDatabase }
}

$previousDatabase = $env:POSTGRES_DB
$previousDebug = $env:DJANGO_DEBUG
$env:POSTGRES_DB = $LoadDatabase
$env:DJANGO_DEBUG = 'true'
Push-Location $backend
try {
    Invoke-Checked { & $python manage.py migrate --noinput }
    New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot 'tmp') | Out-Null
    $server = Start-Process -FilePath $python -ArgumentList @('manage.py', 'runserver', "127.0.0.1:$Port", '--noreload') -WorkingDirectory $backend -WindowStyle Hidden -PassThru
    try {
        $ready = $false
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            if (Test-NetConnection -ComputerName '127.0.0.1' -Port $Port -InformationLevel Quiet) { $ready = $true; break }
            Start-Sleep -Seconds 1
        }
        if (-not $ready) { throw "Load-test server did not listen on port $Port." }
        Invoke-Checked { & $python (Join-Path $projectRoot 'scripts\load_test.py') --base-url "http://127.0.0.1:$Port/api" --records $Records --workers $Workers --output $summary }
    }
    finally {
        if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force }
    }
}
finally {
    Pop-Location
    $env:POSTGRES_DB = $previousDatabase
    $env:DJANGO_DEBUG = $previousDebug
}

Write-Host "Load-test summary: $summary"
