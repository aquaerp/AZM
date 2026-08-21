<#
Runs the local release checks for Azm from any current directory.
Requires Docker services, the Python virtual environment, and npm dependencies.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    throw "Python virtual environment was not found at $python"
}

function Invoke-Checked {
    param([scriptblock]$Command)

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Verification command failed with exit code $LASTEXITCODE."
    }
}

Invoke-Checked { & $python (Join-Path $PSScriptRoot 'check_release_metadata.py') }
Invoke-Checked { & $python -m pip check }

Push-Location (Join-Path $projectRoot 'backend')
try {
    Invoke-Checked { & $python manage.py check }
    Invoke-Checked { & $python manage.py makemigrations --check --dry-run }
    Invoke-Checked { & $python -m coverage erase }
    Invoke-Checked { & $python -m coverage run manage.py test }
    Invoke-Checked { & $python -m coverage report --fail-under=90 }
}
finally {
    Pop-Location
}

Push-Location (Join-Path $projectRoot 'frontend')
try {
    Invoke-Checked { & npm.cmd run lint }
    Invoke-Checked { & npm.cmd audit --omit=dev --audit-level=high }
    Invoke-Checked { & npm.cmd run test }
    Invoke-Checked { & npm.cmd run build }
    Invoke-Checked { & npx.cmd playwright install chromium }
    Invoke-Checked { & npm.cmd run test:e2e }
}
finally {
    Pop-Location
}

Push-Location (Join-Path $projectRoot 'mobile')
try {
    Invoke-Checked { & npm.cmd audit --omit=dev --audit-level=high }
    Invoke-Checked { & npx.cmd expo-doctor }
    Invoke-Checked { & npx.cmd expo export --platform web }
}
finally {
    Pop-Location
}

Push-Location (Join-Path $projectRoot 'desktop')
try {
    Invoke-Checked { & npm.cmd audit --omit=dev --audit-level=high }
    Invoke-Checked { & npm.cmd run verify }
}
finally {
    Pop-Location
}
