#!/usr/bin/env python3
"""Run an integrated AZM acceptance journey against a fresh isolated environment."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from secrets import token_hex


class UatFailure(RuntimeError):
    pass


class Api:
    def __init__(self, base_url: str, insecure: bool = False):
        self.base_url = base_url.rstrip("/")
        self.context = ssl._create_unverified_context() if insecure else None

    def request(self, method: str, path: str, payload=None, token: str | None = None, expected=(200,), extra_headers=None):
        headers = {"Accept": "application/json"}
        headers.update(extra_headers or {})
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(f"{self.base_url}{path}", data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, context=self.context, timeout=30) as response:
                raw = response.read()
                status = response.status
        except urllib.error.HTTPError as error:
            raw = error.read()
            status = error.code
        try:
            result = json.loads(raw.decode()) if raw else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            result = raw.decode(errors="replace")
        if status not in expected:
            raise UatFailure(f"{method} {path}: expected {expected}, got {status}: {result}")
        return result

    def download(self, path: str, token: str):
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            headers={"Accept": "application/pdf", "Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(request, context=self.context, timeout=30) as response:
            return response.headers.get_content_type(), response.read()


def require(condition: bool, message: str):
    if not condition:
        raise UatFailure(message)


def run(base_url: str, insecure: bool):
    api = Api(base_url, insecure=insecure)
    suffix = token_hex(4)
    password = f"Azm-Uat-{token_hex(8)}!9a"
    owner_name = f"uat_owner_{suffix}"
    technician_name = f"uat_tech_{suffix}"
    operator_name = f"uat_ops_{suffix}"
    steps = []

    def passed(name: str, **evidence):
        steps.append({"step": name, "status": "passed", **evidence})

    health = api.request("GET", "/healthz/")
    require(health.get("status") == "ok", "Health endpoint did not report ok")
    passed("health")

    api.request(
        "POST",
        "/api/auth/register/",
        {
            "username": owner_name,
            "password": password,
            "first_name": "UAT",
            "last_name": "Owner",
            "email": f"{owner_name}@example.test",
            "workshop_name": f"AZM UAT {suffix}",
        },
        expected=(201,),
        extra_headers={"X-Azm-Device-Id": f"azm-uat-device-{suffix}-{token_hex(16)}"},
    )
    passed("trial_registration")

    def login(username: str):
        return api.request("POST", "/api/auth/login/", {"username": username, "password": password})["access"]

    owner = login(owner_name)
    technician = api.request(
        "POST",
        "/api/auth/team/",
        {"username": technician_name, "password": password, "first_name": "UAT", "last_name": "Technician", "email": "", "role": "technician"},
        owner,
        expected=(201,),
    )
    operator = api.request(
        "POST",
        "/api/auth/team/",
        {"username": operator_name, "password": password, "first_name": "UAT", "last_name": "Operator", "email": "", "role": "storekeeper"},
        owner,
        expected=(201,),
    )
    passed("team_roles", technician_id=technician["id"], operator_id=operator["id"])

    employee = api.request(
        "POST",
        "/api/workforce/employees/",
        {"user": technician["id"], "job_title": "فني UAT", "hired_at": date.today().isoformat(), "commission_rate": "10.00", "is_active": True, "notes": ""},
        owner,
        expected=(201,),
    )
    customer = api.request("POST", "/api/workshop/customers/", {"name": "عميل UAT", "phone": f"05{suffix[:8]}", "email": "", "notes": ""}, owner, (201,))
    vehicle = api.request(
        "POST",
        "/api/workshop/vehicles/",
        {"customer": customer["id"], "license_plate": f"UAT-{suffix}", "make": "Toyota", "model": "Camry", "model_year": 2024, "vin": "", "color": "White", "mileage": 1000, "notes": ""},
        owner,
        (201,),
    )
    service = api.request("POST", "/api/workshop/services/", {"name": f"خدمة UAT {suffix}", "description": "", "base_price": "100.00", "is_active": True}, owner, (201,))
    supplier = api.request("POST", "/api/inventory/suppliers/", {"name": f"مورد UAT {suffix}", "contact_name": "", "phone": "", "email": "", "notes": "", "is_active": True}, owner, (201,))
    supplier = api.request("PATCH", f"/api/inventory/suppliers/{supplier['id']}/", {"contact_name": "Updated UAT"}, owner)
    require(supplier["contact_name"] == "Updated UAT", "Supplier update was not persisted")
    part = api.request(
        "POST",
        "/api/inventory/parts/",
        {"name": f"قطعة UAT {suffix}", "sku": f"UAT-{suffix}", "description": "", "supplier": supplier["id"], "quantity": 5, "reorder_level": 1, "purchase_price": "20.00", "sale_price": "50.00", "is_active": True},
        owner,
        (201,),
    )
    promised = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    job = api.request(
        "POST",
        "/api/workshop/job-cards/",
        {"customer": customer["id"], "vehicle": vehicle["id"], "service_ids": [service["id"]], "technician_ids": [technician["id"]], "status": "pending", "complaint": "UAT workflow", "estimated_cost": "150.00", "actual_cost": "0.00", "promised_at": promised},
        owner,
        (201,),
    )
    job = api.request("GET", f"/api/workshop/job-cards/{job['id']}/", token=owner)
    task = api.request("POST", "/api/workforce/tasks/", {"job_card": job["id"], "employee": employee["id"], "title": "مهمة UAT", "description": "", "estimated_hours": "1.00"}, owner, (201,))
    passed("master_data_and_job", job_number=job.get("job_number"))

    tech_token = login(technician_name)
    api.request("PATCH", f"/api/workshop/job-cards/{job['id']}/status/", {"status": "in_progress", "diagnosis": "UAT diagnosis"}, tech_token)
    api.request("POST", f"/api/workforce/tasks/{task['id']}/start/", {}, tech_token)
    part_request = api.request("POST", "/api/inventory/part-requests/", {"job_card": job["id"], "part": part["id"], "quantity": 2, "notes": "UAT request"}, tech_token, (201,))
    api.request("POST", f"/api/workforce/tasks/{task['id']}/complete/", {}, tech_token)
    api.request("PATCH", f"/api/workshop/job-cards/{job['id']}/status/", {"status": "ready", "diagnosis": "UAT complete"}, tech_token)
    api.request("POST", f"/api/workshop/job-cards/{job['id']}/deliver/", {}, tech_token, (403,))
    passed("technician_workflow_and_delivery_boundary")

    storekeeper = login(operator_name)
    fulfilled = api.request("POST", f"/api/inventory/part-requests/{part_request['id']}/fulfill/", {}, storekeeper)
    require(fulfilled["status"] == "fulfilled", "Part request was not fulfilled")
    remaining_part = api.request("GET", f"/api/inventory/parts/{part['id']}/", token=storekeeper)
    require(Decimal(str(remaining_part["quantity"])) == Decimal("3"), "Inventory quantity was not decremented")
    passed("storekeeper_fulfillment")

    invoice = api.request("POST", "/api/accounting/invoices/create-from-job/", {"job_card": job["id"]}, owner, (201,))
    require(len(invoice["lines"]) >= 2, "Invoice did not include service and part lines")
    line = invoice["lines"][0]
    corrected = api.request("PATCH", f"/api/accounting/invoice-lines/{line['id']}/", {"unit_price": "125.00"}, owner)
    require(Decimal(corrected["unit_price"]) == Decimal("125.00"), "Invoice line correction was not persisted")
    invoice = api.request("GET", f"/api/accounting/invoices/{invoice['id']}/", token=owner)
    expected_subtotal = sum(Decimal(item["line_total"]) for item in invoice["lines"])
    require(Decimal(invoice["subtotal"]) == expected_subtotal, "Invoice total was not recalculated after correction")
    passed("invoice_value_correction", subtotal=invoice["subtotal"])

    api.request("PATCH", f"/api/auth/team/{operator['id']}/", {"role": "receptionist"}, owner)
    receptionist = login(operator_name)
    rescheduled = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    api.request("PATCH", f"/api/workshop/job-cards/{job['id']}/reschedule/", {"promised_at": rescheduled}, receptionist)
    delivered = api.request("POST", f"/api/workshop/job-cards/{job['id']}/deliver/", {}, receptionist)
    require(delivered["status"] == "delivered" and delivered["delivery_method"] == "manual", "Workshop delivery did not complete")
    portal = api.request("GET", f"/api/portal/jobs/{delivered['portal_token']}/")
    require(portal["status"] == "delivered" and portal["promised_at"], "Public tracking did not reflect schedule/status")
    passed("reception_delivery_and_public_tracking")

    api.request("PATCH", f"/api/auth/team/{operator['id']}/", {"role": "accountant"}, owner)
    accountant = login(operator_name)
    invoice = api.request("GET", f"/api/accounting/invoices/{invoice['id']}/", token=accountant)
    payment = api.request("POST", f"/api/accounting/invoices/{invoice['id']}/record-payment/", {"amount": invoice["total"], "method": "card", "reference": f"UAT-{suffix}"}, accountant, (201,))
    require(Decimal(payment["amount"]) == Decimal(invoice["total"]), "Full payment amount differs from invoice total")
    paid_invoice = api.request("GET", f"/api/accounting/invoices/{invoice['id']}/", token=accountant)
    require(paid_invoice["status"] == "paid" and paid_invoice["pdf_url"], "Full payment did not mark paid and generate a PDF")
    pdf_type, pdf_body = api.download(f"/api/accounting/invoices/{invoice['id']}/download-pdf/", accountant)
    require(pdf_type == "application/pdf" and pdf_body.startswith(b"%PDF"), "Authenticated PDF download did not return a PDF file")
    passed("accountant_full_payment_and_pdf", invoice_number=paid_invoice["invoice_number"])

    today = date.today()
    commissions = api.request("POST", "/api/workforce/commissions/generate/", {"year": today.year, "month": today.month}, owner)
    matching = [record for record in commissions if record["employee"] == employee["id"] and record["job_card"] == job["id"]]
    require(len(matching) == 1 and Decimal(matching[0]["amount"]) > 0, "Monthly commission was not generated")
    summary = api.request("GET", f"/api/workforce/commissions/summary/?year={today.year}&month={today.month}", token=owner)
    require(summary["count"] >= 1 and Decimal(str(summary["total"])) > 0, "Commission summary is empty")
    passed("monthly_commission", amount=matching[0]["amount"])

    return {"status": "passed", "base_url": base_url, "run_id": suffix, "steps": steps}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--insecure", action="store_true", help="Allow a staging-only self-signed TLS certificate")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.base_url, args.insecure), ensure_ascii=False, indent=2))
    except Exception as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
