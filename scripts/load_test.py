"""HTTP load scenario for an isolated Azm database.

Each target record creates one customer, one linked vehicle, and one job card.
The default 100-record smoke run therefore exercises 300 write operations.
Use --records 100000 for the full 300,000-row scenario.
"""

from __future__ import annotations

import argparse
import base64
import json
import statistics
import sys
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import urllib3


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.latencies: list[float] = []
        self.endpoint_latencies: dict[str, list[float]] = {}
        self.successes = 0
        self.failures = Counter()

    @staticmethod
    def latency_summary(values: list[float]) -> dict:
        ordered = sorted(values)
        percentile = lambda value: ordered[min(len(ordered) - 1, max(0, int(len(ordered) * value) - 1))] if ordered else 0
        return {
            "requests": len(ordered),
            "min": round(ordered[0], 2) if ordered else 0,
            "p50": round(percentile(0.50), 2),
            "p95": round(percentile(0.95), 2),
            "max": round(ordered[-1], 2) if ordered else 0,
            "mean": round(statistics.mean(ordered), 2) if ordered else 0,
        }

    def add(self, duration_ms: float, status: int | None, endpoint: str) -> None:
        with self._lock:
            self.latencies.append(duration_ms)
            self.endpoint_latencies.setdefault(endpoint, []).append(duration_ms)
            if status is not None and 200 <= status < 300:
                self.successes += 1
            else:
                self.failures[str(status or "network")] += 1

    def summary(self, elapsed_seconds: float) -> dict:
        latency = self.latency_summary(self.latencies)
        return {
            "requests": len(self.latencies),
            "successful_requests": self.successes,
            "failed_requests": sum(self.failures.values()),
            "requests_per_second": round(len(self.latencies) / elapsed_seconds, 2) if elapsed_seconds else 0,
            "latency_ms": {key: value for key, value in latency.items() if key != "requests"},
            "endpoint_latency_ms": {endpoint: self.latency_summary(values) for endpoint, values in sorted(self.endpoint_latencies.items())},
            "failure_counts": dict(self.failures),
            "elapsed_seconds": round(elapsed_seconds, 2),
        }


class ApiClient:
    def __init__(self, base_url: str, metrics: Metrics, max_connections: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.metrics = metrics
        self.http = urllib3.PoolManager(num_pools=1, maxsize=max_connections, block=True)
        self.token = ""
        self.refresh_token = ""
        self.token_expires_at = 0
        self._refresh_lock = threading.Lock()
        self.device_id = f"load-test-device-{uuid.uuid4().hex}"

    @staticmethod
    def _token_expiry(token: str) -> int:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return int(json.loads(base64.urlsafe_b64decode(payload))["exp"])

    def set_tokens(self, data: dict) -> None:
        self.token = data["access"]
        self.refresh_token = data.get("refresh", self.refresh_token)
        self.token_expires_at = self._token_expiry(self.token)

    def _ensure_access_token(self) -> None:
        if not self.token or time.time() < self.token_expires_at - 30:
            return
        with self._refresh_lock:
            if time.time() < self.token_expires_at - 30:
                return
            response = self.http.request(
                "POST",
                f"{self.base_url}/auth/token/refresh/",
                body=json.dumps({"refresh": self.refresh_token}).encode("utf-8"),
                headers={"Content-Type": "application/json", "X-Azm-Device-Id": self.device_id},
                timeout=urllib3.Timeout(total=30),
            )
            if not 200 <= response.status < 300:
                raise RuntimeError(f"Token refresh returned {response.status}: {response.data.decode('utf-8', errors='replace')}")
            self.set_tokens(json.loads(response.data))

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[int | None, dict]:
        self._ensure_access_token()
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en",
            "X-Azm-Device-Id": self.device_id,
        }
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
            response = self.http.request(
                method,
                f"{self.base_url}{path}",
                body=body,
                headers=headers,
                timeout=urllib3.Timeout(total=30),
            )
            status = response.status
            raw = response.data
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                data = {"detail": raw.decode("utf-8", errors="replace")}
        except (urllib3.exceptions.HTTPError, TimeoutError, OSError) as error:
            data = {"detail": str(error)}
        finally:
            self.metrics.add((time.perf_counter() - started) * 1000, status, f"{method} {path}")
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
    client = ApiClient(args.base_url, metrics, args.workers)
    run_id = uuid.uuid4().hex[:10]
    password = "LoadTestPass123!"
    require_success(client, "POST", "/auth/register/", {
        "workshop_name": f"Load test {run_id}", "first_name": "Load", "last_name": "Manager",
        "username": f"load-manager-{run_id}", "email": f"load-{run_id}@example.test", "password": password,
    })
    login = require_success(client, "POST", "/auth/login/", {"username": f"load-manager-{run_id}", "password": password})
    client.set_tokens(login)
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
        for completed, future in enumerate(as_completed(futures), start=1):
            try:
                future.result()
            except RuntimeError:
                pass
            if args.records >= 1000 and (completed % 1000 == 0 or completed == args.records):
                elapsed = time.perf_counter() - started
                rate = completed / elapsed if elapsed else 0
                print(f"Progress: {completed}/{args.records} triplets ({rate:.2f}/s)", flush=True)

    observed_counts = {}
    validation_errors = []
    for name, endpoint in (
        ("customers", "/workshop/customers/?page=1&page_size=100"),
        ("vehicles", "/workshop/vehicles/?page=1&page_size=100"),
        ("job_cards", "/workshop/job-cards/?page=1&page_size=100"),
    ):
        data = require_success(client, "GET", endpoint)
        observed = data.get("count") if isinstance(data, dict) and "count" in data else len(data)
        observed_counts[name] = observed
        if observed != args.records:
            validation_errors.append(f"{name}: expected {args.records}, observed {observed}")
    dashboard = require_success(client, "GET", "/workshop/job-cards/dashboard/")
    observed_counts["dashboard_total"] = dashboard.get("total")
    if dashboard.get("total") != args.records:
        validation_errors.append(f"dashboard_total: expected {args.records}, observed {dashboard.get('total')}")
    summary = metrics.summary(time.perf_counter() - started)
    summary.update({
        "records_requested": args.records,
        "rows_targeted": args.records * 3,
        "observed_counts": observed_counts,
        "validation_errors": validation_errors,
        "workers": args.workers,
        "base_url": args.base_url,
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    slow_endpoints = [endpoint for endpoint, latency in summary["endpoint_latency_ms"].items() if latency["p95"] > args.max_p95_ms]
    if summary["failed_requests"] or validation_errors or slow_endpoints:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
