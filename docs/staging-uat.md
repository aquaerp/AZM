# Isolated staging UAT

This runbook validates AZM against real API, database, Redis, worker, and web
containers without reading or writing production data.

## Isolation requirements

- Use a dedicated Compose project name, such as `azm-staging`.
- Use a dedicated environment file with unique database and application secrets.
- Bind the web ports to loopback only, for example:
  - `AZM_HTTP_BIND=127.0.0.1:18080`
  - `AZM_HTTPS_BIND=127.0.0.1:18443`
- Never copy the production database or media volume into this environment.
- Run this journey against a fresh staging database. Trial registration deliberately
  permits one trial per source IP and device.

## Start and validate

From `deploy/hostinger`:

```powershell
$env:AZM_ENV_FILE = ".env.staging"
docker compose -p azm-staging --env-file .env.staging up -d --build
```

Validate infrastructure from the project root:

```powershell
.\scripts\staging-smoke.ps1 -EnvironmentFile ".env.staging" -ProjectName "azm-staging"
```

Run the integrated acceptance journey on the staging host:

```bash
python3 scripts/uat-smoke.py --base-url https://staging.localhost:18443 --insecure
```

The journey creates an isolated trial workshop and verifies:

1. customer, vehicle, supplier, part, service, and job-card creation;
2. supplier data update;
3. technician task progress and ready-for-delivery transition;
4. technician part request and storekeeper fulfillment;
5. invoice creation, line-value correction, and total recalculation;
6. receptionist rescheduling, manual delivery, and public tracking;
7. accountant full payment and automatic PDF generation;
8. monthly commission generation and summary.

The trial plan supports three accounts. The runner therefore rotates the second
operational account from storekeeper to receptionist to accountant through the
owner API, logging in again after every role change. This validates each real
authorization boundary while respecting the plan limit.

## Remove temporary staging data

First confirm that the resolved project is `azm-staging`, then remove only its
containers and named volumes:

```powershell
docker compose -p azm-staging --env-file .env.staging down --volumes
```

This command must never be run with the production Compose project name.
