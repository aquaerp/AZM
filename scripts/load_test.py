"""HTTP load scenario for an isolated Azm database.

Each target record creates one customer, one linked vehicle, and one job card.
The default 100-record smoke run therefore exercises 300 write operations.
Use --records 100000 for the full 300,000-row scenario.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.latencies: list[float] = []
        self.successes = 0
        self.failures = Counter()

    def add(self, duration_ms: float, status: int | None) -> None:
        with self._lock:
            self.latencies.append(duration_ms)
            if status is not None and 200 <= status < 300:
                self.successes += 1
            else:
                self.failures[str(status or "network")] += 1

    def summary(self, elapsed_seconds: float) -> dict:
        values = sorted(self.latencies)
        percentile = lambda value: values[min(len(values) - 1, max(0, int(len(values) * value) - 1))] if values else 0
        return {
            "requests": len(values),
            "successful_requests": self.successes,
            "failed_requests": sum(self.failures.values()),
            "requests_per_second": round(len(values) / elapsed_seconds, 2) if elapsed_seconds else 0,
            "latency_ms": {
                "min": round(values[0], 2) if values else 0,
                "p50": round(percentile(0.50), 2),
                "p95": round(percentile(0.95), 2),
                "max": round(values[-1], 2) if values else 0,
                "mean": round(statistics.mean(values), 2) if values else 0,
            },
            "failure_counts": dict(self.failures),
            "elapsed_seconds": round(elapsed_seconds, 2),
        }


class ApiClient:
    def __init__(self, base_url: str, metrics: Metrics) -> None:
        self.base_url = base_url.rstrip("/")
        self.metrics = metrics
        self.token = ""

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[int | None, dict]:
        headers = {"Accept": "application/json", "Accept-Language": "en"}
        body = None
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        started = time.perf_counter()
        status = None
        data: dict = {}
        try:
            request = Request(f"{self.base_url}{path}", data=body, headers=headers, method=method)
            with urlopen(request, timeout=30) as response:
                status = response.status
                raw = response.read()
                data = json.loads(raw) if raw else {}
        except HTTPError as error:
            status = error.code
            raw = error.read()
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                data = {"detail": raw.decode("utf-8", errors="replace")}
        except (URLError, TimeoutError, OSError) as error:
            data = {"detail": str(error)}
        finally:
            self.metrics.add((time.perf_counter() - started) * 1000, status)
        return status, data


def require_success(client: ApiClient, method: str, path: str, payload: dict | None = None) -> dict:
    status, data = client.request(method, path, payload)
    if status is None or not 200 <= status < 300:
        raise RuntimeError(f"{method} {path} returned {status}: {data}")
    return data


def validate_target(base_url: str, allow_remote: bool) -> None:
    host = urlparse(base_url).hostname
    if not allow_remote and host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Refusing a non-local target. Pass --allow-remote only for an approved isolated environment.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Azm isolated API load test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/api")
    parser.add_argument("--records", type=int, default=100, help="customer/vehicle/job-card triplets to create")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-p95-ms", type=float, default=1500)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-remote", action="store_true")
    args = parser.parse_args()
    if args.records < 1 or args.workers < 1:
        parser.error("--records and --workers must be positive")
    validate_target(args.base_url, args.allow_remote)

    metrics = Metrics()
    client = ApiClient(args.base_url, metrics)
    run_id = uuid.uuid4().hex[:10]
    password = "LoadTestPass123!"
    require_success(client, "POST", "/auth/register/", {
        "workshop_name": f"Load test {run_id}", "first_name": "Load", "last_name": "Manager",
        "username": f"load-manager-{run_id}", "email": f"load-{run_id}@example.test", "password": password,
    })
    login = require_success(client, "POST", "/auth/login/", {"username": f"load-manager-{run_id}", "password": password})
    client.token = login["access"]
    require_success(client, "POST", "/workshop/services/", {"name": f"Load service {run_id}", "base_price": "100.00"})

    started = time.perf_counter()

    def create_triplet(index: int) -> None:
        customer = require_success(client, "POST", "/workshop/customers/", {
            "name": f"Load customer {run_id}-{index}", "phone": f"05{index:08d}"[-10:], "email": f"customer-{run_id}-{index}@example.test",
        })
        vehicle = require_success(client, "POST", "/workshop/vehicles/", {
            "customer": customer["id"], "license_plate": f"LT{index:06d}", "make": "Load", "model": "Test",
        })
        require_success(client, "POST", "/workshop/job-cards/", {
            "customer": customer["id"], "vehicle": vehicle["id"], "complaint": "Load-test job card", "estimated_cost": "100.00",
        })

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(create_triplet, index) for index in range(args.records)]
        for future in as_completed(futures):
            try:
                future.result()
            except RuntimeError:
                pass

    for endpoint in ("/workshop/customers/", "/workshop/vehicles/", "/workshop/job-cards/", "/workshop/job-cards/dashboard/"):
        client.request("GET", endpoint)
    summary = metrics.summary(time.perf_counter() - started)
    summary.update({"records_requested": args.records, "rows_targeted": args.records * 3, "workers": args.workers, "base_url": args.base_url})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    if summary["failed_requests"] or summary["latency_ms"]["p95"] > args.max_p95_ms:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
