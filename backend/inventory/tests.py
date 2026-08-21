from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import AuditEvent, User, Workshop
from workshop.models import Customer, JobCard, Vehicle

from .models import InventoryAlert, Part, PartRequest, PartUsage, Supplier
from .tasks import check_low_stock_levels


class InventoryApiTests(APITestCase):
    def setUp(self):
        self.workshop = Workshop.objects.create(name="ورشة عزم")
        self.other_workshop = Workshop.objects.create(name="ورشة أخرى")
        self.manager = User.objects.create_user(username="manager", password="SafePass123!", workshop=self.workshop, role=User.Role.MANAGER)
        customer = Customer.objects.create(workshop=self.workshop, name="خالد", phone="0500000000")
        vehicle = Vehicle.objects.create(workshop=self.workshop, customer=customer, license_plate="أ ب ج 123", make="Toyota", model="Camry")
        self.job = JobCard.objects.create(workshop=self.workshop, customer=customer, vehicle=vehicle, complaint="فحص", created_by=self.manager)
        self.part = Part.objects.create(workshop=self.workshop, name="فلتر زيت", sku="OF-001", quantity=5, reorder_level=3, purchase_price="12.00", sale_price="20.00")
        self.other_part = Part.objects.create(workshop=self.other_workshop, name="قطعة أخرى", sku="X-001", quantity=10, reorder_level=2)
        self.client.force_authenticate(self.manager)

    def test_part_usage_decreases_stock_and_creates_alert(self):
        response = self.client.post("/api/inventory/part-usages/", {"job_card": self.job.id, "part": self.part.id, "quantity": 2})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.part.refresh_from_db()
        self.assertEqual(self.part.quantity, 3)
        self.assertTrue(InventoryAlert.objects.filter(part=self.part, is_active=True).exists())
        event = AuditEvent.objects.get(action="inventory.part_issued")
        self.assertEqual(event.workshop, self.workshop)
        self.assertEqual(event.after["part_id"], self.part.id)

    def test_part_usage_cannot_exceed_stock(self):
        response = self.client.post("/api/inventory/part-usages/", {"job_card": self.job.id, "part": self.part.id, "quantity": 6})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.part.refresh_from_db()
        self.assertEqual(self.part.quantity, 5)

    def test_deleting_part_usage_restores_stock(self):
        usage = PartUsage.objects.create(workshop=self.workshop, job_card=self.job, part=self.part, quantity=2, unit_purchase_price="12.00", unit_sale_price="20.00", added_by=self.manager)
        self.part.quantity = 3
        self.part.save()

        response = self.client.delete(f"/api/inventory/part-usages/{usage.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.part.refresh_from_db()
        self.assertEqual(self.part.quantity, 5)

    def test_part_usage_rejects_part_from_another_workshop(self):
        response = self.client.post("/api/inventory/part-usages/", {"job_card": self.job.id, "part": self.other_part.id, "quantity": 1})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_daily_task_creates_low_stock_alert(self):
        self.part.quantity = 2
        self.part.save()

        count = check_low_stock_levels()

        self.assertEqual(count, 1)
        self.assertTrue(InventoryAlert.objects.filter(part=self.part, is_active=True).exists())

    def test_manager_cannot_retrieve_or_delete_other_workshop_part(self):
        url = f"/api/inventory/parts/{self.other_part.id}/"

        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Part.objects.filter(pk=self.other_part.id).exists())

    def test_inventory_alert_list_and_acknowledge_are_workshop_scoped(self):
        own_alert = InventoryAlert.objects.create(workshop=self.workshop, part=self.part, quantity_at_alert=2, reorder_level_at_alert=3)
        other_alert = InventoryAlert.objects.create(workshop=self.other_workshop, part=self.other_part, quantity_at_alert=1, reorder_level_at_alert=2)

        response = self.client.get("/api/inventory/alerts/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [own_alert.id])
        self.assertEqual(self.client.post(f"/api/inventory/alerts/{other_alert.id}/acknowledge/").status_code, status.HTTP_404_NOT_FOUND)
        other_alert.refresh_from_db()
        self.assertIsNone(other_alert.acknowledged_at)
        self.client.post(f"/api/inventory/alerts/{own_alert.id}/acknowledge/")
        self.assertTrue(AuditEvent.objects.filter(action="inventory.alert_acknowledged", workshop=self.workshop, entity_id=str(own_alert.id)).exists())

    def test_technician_requests_part_and_storekeeper_fulfills_it(self):
        technician = User.objects.create_user(username="parts-tech", password="SafePass123!", workshop=self.workshop, role=User.Role.TECHNICIAN)
        storekeeper = User.objects.create_user(username="storekeeper", password="SafePass123!", workshop=self.workshop, role=User.Role.STOREKEEPER)
        self.job.assigned_technicians.add(technician)
        self.client.force_authenticate(technician)
        created = self.client.post("/api/inventory/part-requests/", {"job_card": self.job.id, "part": self.part.id, "quantity": 2, "notes": "مطلوبة للإصلاح"})

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        request_record = PartRequest.objects.get(requested_by=technician)
        self.client.force_authenticate(storekeeper)
        fulfilled = self.client.post(f"/api/inventory/part-requests/{request_record.id}/fulfill/")

        self.assertEqual(fulfilled.status_code, status.HTTP_200_OK)
        request_record.refresh_from_db()
        self.part.refresh_from_db()
        self.assertEqual(request_record.status, PartRequest.Status.FULFILLED)
        self.assertEqual(request_record.reviewed_by, storekeeper)
        self.assertEqual(self.part.quantity, 3)
        self.assertIsNotNone(request_record.fulfilled_usage_id)

    def test_receptionist_can_issue_part_directly(self):
        receptionist = User.objects.create_user(username="parts-reception", password="SafePass123!", workshop=self.workshop, role=User.Role.RECEPTIONIST)
        self.client.force_authenticate(receptionist)

        response = self.client.post("/api/inventory/part-usages/", {"job_card": self.job.id, "part": self.part.id, "quantity": 1})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PartUsage.objects.filter(added_by=receptionist, job_card=self.job).exists())

    def test_storekeeper_can_update_supplier_details(self):
        storekeeper = User.objects.create_user(username="supplier-storekeeper", password="SafePass123!", workshop=self.workshop, role=User.Role.STOREKEEPER)
        supplier = Supplier.objects.create(workshop=self.workshop, name="المورد القديم")
        self.client.force_authenticate(storekeeper)

        response = self.client.patch(f"/api/inventory/suppliers/{supplier.id}/", {"name": "المورد المحدث", "phone": "0501234567"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        supplier.refresh_from_db()
        self.assertEqual(supplier.name, "المورد المحدث")
