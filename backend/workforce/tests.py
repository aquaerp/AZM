from datetime import date
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User, Workshop
from inventory.models import Part, PartUsage
from workshop.models import Customer, JobCard, Service, Vehicle

from .models import Employee, EmployeeCommission, JobTask


class WorkforceApiTests(APITestCase):
    def setUp(self):
        self.workshop = Workshop.objects.create(name="ورشة عزم")
        self.other_workshop = Workshop.objects.create(name="ورشة أخرى")
        self.manager = User.objects.create_user(username="manager", password="SafePass123!", workshop=self.workshop, role=User.Role.MANAGER)
        self.technician = User.objects.create_user(username="tech", password="SafePass123!", workshop=self.workshop, role=User.Role.TECHNICIAN, first_name="سجاد")
        self.employee = Employee.objects.create(workshop=self.workshop, user=self.technician, job_title="فني ميكانيكا", hired_at=date.today(), commission_rate="10.00")
        customer = Customer.objects.create(workshop=self.workshop, name="خالد", phone="0500000000")
        vehicle = Vehicle.objects.create(workshop=self.workshop, customer=customer, license_plate="أ ب ج 123", make="Toyota", model="Camry")
        self.job = JobCard.objects.create(workshop=self.workshop, customer=customer, vehicle=vehicle, complaint="فحص", status=JobCard.Status.DELIVERED, created_by=self.manager)
        service = Service.objects.create(workshop=self.workshop, name="صيانة", base_price="100.00")
        self.job.services.add(service)
        part = Part.objects.create(workshop=self.workshop, name="فلتر", sku="F-1", quantity=5, reorder_level=1, sale_price="20.00")
        PartUsage.objects.create(workshop=self.workshop, job_card=self.job, part=part, quantity=1, unit_purchase_price="10.00", unit_sale_price="20.00", added_by=self.manager)
        self.task = JobTask.objects.create(workshop=self.workshop, job_card=self.job, employee=self.employee, title="تغيير الفلتر", status=JobTask.Status.COMPLETED)
        self.client.force_authenticate(self.manager)

    def test_manager_creates_employee_from_technician_account(self):
        another = User.objects.create_user(username="tech2", password="SafePass123!", workshop=self.workshop, role=User.Role.TECHNICIAN)
        response = self.client.post("/api/workforce/employees/", {"user": another.id, "job_title": "فني كهرباء", "hired_at": str(date.today()), "commission_rate": "12.50"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Employee.objects.filter(user=another).exists())

    def test_creating_task_assigns_technician_to_job_card(self):
        response = self.client.post(
            "/api/workforce/tasks/",
            {"job_card": self.job.id, "employee": self.employee.id, "title": "فحص نهائي", "estimated_hours": "1.00"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.job.assigned_technicians.filter(pk=self.technician.pk).exists())

    def test_technician_can_start_and_complete_own_task(self):
        self.task.status = JobTask.Status.NOT_STARTED
        self.task.save()
        self.client.force_authenticate(self.technician)

        start = self.client.post(f"/api/workforce/tasks/{self.task.id}/start/")
        complete = self.client.post(f"/api/workforce/tasks/{self.task.id}/complete/")

        self.assertEqual(start.status_code, status.HTTP_200_OK)
        self.assertEqual(complete.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, JobTask.Status.COMPLETED)

    def test_generate_monthly_commission_from_services_and_parts(self):
        response = self.client.post("/api/workforce/commissions/generate/", {"year": date.today().year, "month": date.today().month})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        commission = EmployeeCommission.objects.get(employee=self.employee, job_card=self.job)
        self.assertEqual(commission.basis_amount, Decimal("120.00"))
        self.assertEqual(commission.amount, Decimal("12.00"))

    def test_manager_cannot_create_task_for_other_workshop_employee(self):
        other_technician = User.objects.create_user(username="other-tech", password="SafePass123!", workshop=self.other_workshop, role=User.Role.TECHNICIAN)
        other_employee = Employee.objects.create(workshop=self.other_workshop, user=other_technician, job_title="Technician", hired_at=date.today())

        response = self.client.post(
            "/api/workforce/tasks/",
            {"job_card": self.job.id, "employee": other_employee.id, "title": "Cross-tenant task"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_commission_summary_excludes_other_workshop_records(self):
        own_commission = EmployeeCommission.objects.create(
            workshop=self.workshop,
            employee=self.employee,
            job_card=self.job,
            period=date.today().replace(day=1),
            commission_rate="10.00",
            basis_amount="120.00",
            amount="12.00",
        )
        other_manager = User.objects.create_user(username="other-commission-manager", password="SafePass123!", workshop=self.other_workshop, role=User.Role.MANAGER)
        other_technician = User.objects.create_user(username="other-commission-tech", password="SafePass123!", workshop=self.other_workshop, role=User.Role.TECHNICIAN)
        other_employee = Employee.objects.create(workshop=self.other_workshop, user=other_technician, job_title="Technician", hired_at=date.today())
        other_customer = Customer.objects.create(workshop=self.other_workshop, name="Other customer", phone="0599999999")
        other_vehicle = Vehicle.objects.create(workshop=self.other_workshop, customer=other_customer, license_plate="OTHER-COMM", make="Kia", model="K5")
        other_job = JobCard.objects.create(workshop=self.other_workshop, customer=other_customer, vehicle=other_vehicle, complaint="Other", status=JobCard.Status.DELIVERED, created_by=other_manager)
        EmployeeCommission.objects.create(workshop=self.other_workshop, employee=other_employee, job_card=other_job, period=date.today().replace(day=1), commission_rate="50.00", basis_amount="9999.00", amount="4999.50")

        response = self.client.get("/api/workforce/commissions/summary/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(Decimal(response.data["total"]), Decimal("12.00"))
