param(
    [string]$EnvironmentFile = ".env",
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$composeDirectory = Join-Path $projectRoot "deploy\hostinger"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$env:AZM_ENV_FILE = $EnvironmentFile

Push-Location $composeDirectory
try {
    docker compose --env-file $EnvironmentFile config --quiet
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose configuration is invalid." }

    $requiredServices = @("db", "redis", "api", "worker", "beat")
    do {
        $unhealthy = @()
        foreach ($service in $requiredServices) {
            $containerId = docker compose --env-file $EnvironmentFile ps -q $service
            if ($LASTEXITCODE -ne 0 -or -not $containerId) {
                $unhealthy += "$service=missing"
                continue
            }
            $health = docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" $containerId
            if ($LASTEXITCODE -ne 0 -or $health -ne "healthy") {
                $unhealthy += "$service=$health"
            }
        }
        if ($unhealthy.Count -eq 0) { break }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)

    if ($unhealthy.Count -ne 0) {
        docker compose --env-file $EnvironmentFile ps
        docker compose --env-file $EnvironmentFile logs --tail 80 api worker beat
        throw "Staging services did not become healthy within $TimeoutSeconds seconds: $($unhealthy -join ', ')."
    }

    $identity = docker compose --env-file $EnvironmentFile exec -T api python -c "import json, os, urllib.request; domain=os.environ['AZM_DOMAIN']; request=urllib.request.Request('http://127.0.0.1:8000/healthz/', headers={'Host': domain, 'X-Forwarded-Proto': 'https'}); response=json.load(urllib.request.urlopen(request)); print(json.dumps({'process_uid': os.stat('/proc/1').st_uid, 'health': response}, sort_keys=True))"
    if ($LASTEXITCODE -ne 0) { throw "The in-container health request failed." }

    $result = $identity | ConvertFrom-Json
    if ($result.process_uid -eq 0) { throw "API application is running as root." }
    if ($result.health.status -ne "ok") { throw "API health endpoint did not report ok." }

    docker compose --env-file $EnvironmentFile ps
    Write-Host "Staging smoke test passed: database, Redis, API, worker and beat are healthy; dependencies reachable; application UID $($result.process_uid)."
}
finally {
    Pop-Location
}
