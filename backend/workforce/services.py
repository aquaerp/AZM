from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from inventory.models import PartUsage
from workshop.models import JobCard
from django.db.models import Q

from .models import EmployeeCommission, JobTask


MONEY = Decimal("0.01")


def commission_base_for_job(job_card: JobCard) -> Decimal:
    service_total = sum((service.base_price for service in job_card.services.all()), Decimal("0.00"))
    parts_total = sum((usage.total_sale_value for usage in PartUsage.objects.filter(job_card=job_card)), Decimal("0.00"))
    return (service_total + parts_total).quantize(MONEY)


def generate_monthly_commissions(workshop, year: int, month: int):
    """Generate or refresh commissions for delivered jobs in a calendar month.

    Each completed task qualifies its employee. The job's service and parts value is
    shared equally between qualifying employees before applying their commission rate.
    """

    period = date(year, month, 1)
    jobs = JobCard.objects.filter(workshop=workshop, status=JobCard.Status.DELIVERED).filter(
        Q(delivered_at__year=year, delivered_at__month=month)
        | Q(delivered_at__isnull=True, status_updated_at__year=year, status_updated_at__month=month)
    ).prefetch_related("services")
    records = []
    for job in jobs:
        employees = list(
            {task.employee_id: task.employee for task in JobTask.objects.filter(job_card=job, status=JobTask.Status.COMPLETED).select_related("employee")}.values()
        )
        if not employees:
            continue
        share = (commission_base_for_job(job) / len(employees)).quantize(MONEY, rounding=ROUND_HALF_UP)
        for employee in employees:
            amount = (share * employee.commission_rate / Decimal("100")).quantize(MONEY, rounding=ROUND_HALF_UP)
            record, _ = EmployeeCommission.objects.update_or_create(
                employee=employee,
                job_card=job,
                defaults={
                    "workshop": workshop,
                    "period": period,
                    "commission_rate": employee.commission_rate,
                    "basis_amount": share,
                    "amount": amount,
                },
            )
            records.append(record)
    return records
