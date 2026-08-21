from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import AuditEvent, User, Workshop
from config.asgi import application

from .models import Customer, JobCard, Vehicle
from .realtime import workshop_group_name


class WorkshopApiTests(APITestCase):
    def setUp(self):
        self.workshop = Workshop.objects.create(name="ورشة عزم")
        self.other_workshop = Workshop.objects.create(name="ورشة أخرى")
        self.manager = User.objects.create_user(username="manager", password="SafePass123!", workshop=self.workshop, role=User.Role.MANAGER)
        self.technician = User.objects.create_user(username="tech", password="SafePass123!", workshop=self.workshop, role=User.Role.TECHNICIAN)
        self.other_manager = User.objects.create_user(username="other", password="SafePass123!", workshop=self.other_workshop, role=User.Role.MANAGER)
        self.customer = Customer.objects.create(workshop=self.workshop, name="خالد", phone="0500000000")
        self.vehicle = Vehicle.objects.create(workshop=self.workshop, customer=self.customer, license_plate="أ ب ج 123", make="Toyota", model="Camry")
        self.other_customer = Customer.objects.create(workshop=self.other_workshop, name="عميل آخر", phone="0599999999")
        self.other_vehicle = Vehicle.objects.create(workshop=self.other_workshop, customer=self.other_customer, license_plate="د هـ و 987", make="Kia", model="K5")
        self.client.force_authenticate(self.manager)

    def test_manager_creates_customer_in_own_workshop(self):
        response = self.client.post("/api/workshop/customers/", {"name": "سارة", "phone": "0511111111"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Customer.objects.get(name="سارة").workshop, self.workshop)
        event = AuditEvent.objects.get(action="workshop.record_created")
        self.assertEqual(event.workshop, self.workshop)
        self.assertEqual(event.actor, self.manager)
        self.assertEqual(event.after["name"], "سارة")

    def test_job_card_rejects_vehicle_from_another_workshop(self):
        response = self.client.post(
            "/api/workshop/job-cards/",
            {"customer": self.customer.id, "vehicle": self.other_vehicle.id, "complaint": "فحص المحرك"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_technician_can_update_assigned_job_status_only(self):
        job = JobCard.objects.create(workshop=self.workshop, customer=self.customer, vehicle=self.vehicle, complaint="صوت في المحرك", created_by=self.manager)
        job.assigned_technicians.add(self.technician)
        self.client.force_authenticate(self.technician)

        response = self.client.patch(f"/api/workshop/job-cards/{job.id}/status/", {"status": "in_progress"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        job.refresh_from_db()
        self.assertEqual(job.status, JobCard.Status.IN_PROGRESS)
        event = AuditEvent.objects.get(action="workshop.job_card_status_changed")
        self.assertEqual(event.actor, self.technician)
        self.assertEqual(event.before["status"], JobCard.Status.PENDING)
        self.assertEqual(event.after["status"], JobCard.Status.IN_PROGRESS)

    def test_dashboard_excludes_other_workshop_job_cards(self):
        JobCard.objects.create(workshop=self.workshop, customer=self.customer, vehicle=self.vehicle, complaint="فحص", created_by=self.manager)
        JobCard.objects.create(workshop=self.other_workshop, customer=self.other_customer, vehicle=self.other_vehicle, complaint="فحص", created_by=self.other_manager)

        response = self.client.get("/api/workshop/job-cards/dashboard/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 1)

    def test_public_portal_only_exposes_status_for_valid_token(self):
        job = JobCard.objects.create(workshop=self.workshop, customer=self.customer, vehicle=self.vehicle, complaint="فحص", created_by=self.manager)

        response = self.client.get(f"/api/portal/jobs/{job.portal_token}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["job_number"], job.job_number)
        self.assertNotIn("diagnosis", response.data)

    def test_manager_cannot_retrieve_update_or_delete_other_workshop_customer(self):
        url = f"/api/workshop/customers/{self.other_customer.id}/"

        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.patch(url, {"name": "Intrusion"}).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)
        self.other_customer.refresh_from_db()
        self.assertNotEqual(self.other_customer.name, "Intrusion")

    def test_manager_cannot_assign_technician_from_another_workshop(self):
        other_technician = User.objects.create_user(
            username="other-tech", password="SafePass123!", workshop=self.other_workshop, role=User.Role.TECHNICIAN
        )

        response = self.client.post(
            "/api/workshop/job-cards/",
            {
                "customer": self.customer.id,
                "vehicle": self.vehicle.id,
                "technician_ids": [other_technician.id],
                "complaint": "Cross-tenant assignment",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_receptionist_can_manage_customers_but_cannot_rotate_portal_token(self):
        receptionist = User.objects.create_user(username="reception", password="SafePass123!", workshop=self.workshop, role=User.Role.RECEPTIONIST)
        self.client.force_authenticate(receptionist)

        customer_response = self.client.post("/api/workshop/customers/", {"name": "Reception customer", "phone": "0555555555"})
        job = JobCard.objects.create(workshop=self.workshop, customer=self.customer, vehicle=self.vehicle, complaint="Check", created_by=self.manager)
        rotate_response = self.client.post(f"/api/workshop/job-cards/{job.id}/rotate-portal-token/")

        self.assertEqual(customer_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(rotate_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_rotate_portal_token(self):
        job = JobCard.objects.create(workshop=self.workshop, customer=self.customer, vehicle=self.vehicle, complaint="فحص", created_by=self.manager)
        old_token = job.portal_token

        response = self.client.post(f"/api/workshop/job-cards/{job.id}/rotate-portal-token/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        job.refresh_from_db()
        self.assertNotEqual(job.portal_token, old_token)
        self.assertEqual(self.client.get(f"/api/portal/jobs/{old_token}/").status_code, status.HTTP_404_NOT_FOUND)

    def test_technician_cannot_change_job_cost(self):
        job = JobCard.objects.create(workshop=self.workshop, customer=self.customer, vehicle=self.vehicle, complaint="فحص", created_by=self.manager)
        job.assigned_technicians.add(self.technician)
        self.client.force_authenticate(self.technician)

        response = self.client.patch(f"/api/workshop/job-cards/{job.id}/status/", {"status": "in_progress", "actual_cost": "500.00"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_receptionist_delivers_only_ready_job_and_can_reschedule(self):
        receptionist = User.objects.create_user(username="delivery-reception", password="SafePass123!", workshop=self.workshop, role=User.Role.RECEPTIONIST)
        job = JobCard.objects.create(workshop=self.workshop, customer=self.customer, vehicle=self.vehicle, complaint="فحص", created_by=self.manager)
        self.client.force_authenticate(receptionist)

        blocked = self.client.post(f"/api/workshop/job-cards/{job.id}/deliver/")
        schedule = self.client.patch(f"/api/workshop/job-cards/{job.id}/reschedule/", {"promised_at": "2026-09-01T15:00:00+03:00"})
        job.status = JobCard.Status.READY
        job.save(update_fields=("status", "status_updated_at"))
        delivered = self.client.post(f"/api/workshop/job-cards/{job.id}/deliver/")

        self.assertEqual(blocked.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(schedule.status_code, status.HTTP_200_OK)
        self.assertEqual(delivered.status_code, status.HTTP_200_OK)
        job.refresh_from_db()
        self.assertEqual(job.status, JobCard.Status.DELIVERED)
        self.assertEqual(job.delivered_by, receptionist)
        self.assertEqual(job.delivery_method, "manual")
        self.assertIsNotNone(job.delivered_at)

    def test_technician_cannot_deliver_ready_job(self):
        job = JobCard.objects.create(workshop=self.workshop, customer=self.customer, vehicle=self.vehicle, complaint="فحص", status=JobCard.Status.READY, created_by=self.manager)
        job.assigned_technicians.add(self.technician)
        self.client.force_authenticate(self.technician)

        response = self.client.post(f"/api/workshop/job-cards/{job.id}/deliver/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class WorkshopRealtimeTests(TransactionTestCase):
    def setUp(self):
        self.workshop = Workshop.objects.create(name="ورشة التزامن")
        self.other_workshop = Workshop.objects.create(name="ورشة أخرى للتزامن")
        self.technician = User.objects.create_user(username="realtime-tech", password="SafePass123!", workshop=self.workshop, role=User.Role.TECHNICIAN)

    def test_authenticated_websocket_receives_only_workshop_update_hints(self):
        async def receive_update():
            communicator = WebsocketCommunicator(
                application,
                "/ws/workshop/updates/",
                headers=[(b"origin", b"http://localhost")],
                subprotocols=["azm", f"jwt.{AccessToken.for_user(self.technician)}"],
            )
            connected, protocol = await communicator.connect()
            self.assertTrue(connected)
            self.assertEqual(protocol, "azm")
            await get_channel_layer().group_send(
                workshop_group_name(self.workshop.id),
                {"type": "workshop.update", "entity": "job_card", "record_id": 12, "job_card_id": 12},
            )
            event = await communicator.receive_json_from(timeout=1)
            await communicator.disconnect()
            return event

        event = async_to_sync(receive_update)()
        self.assertEqual(event, {"type": "workshop.update", "entity": "job_card", "record_id": 12, "job_card_id": 12})

    def test_websocket_does_not_receive_other_workshop_updates(self):
        async def assert_isolated():
            communicator = WebsocketCommunicator(
                application,
                "/ws/workshop/updates/",
                headers=[(b"origin", b"http://localhost")],
                subprotocols=["azm", f"jwt.{AccessToken.for_user(self.technician)}"],
            )
            connected, _protocol = await communicator.connect()
            self.assertTrue(connected)
            await get_channel_layer().group_send(
                workshop_group_name(self.other_workshop.id),
                {"type": "workshop.update", "entity": "job_card", "record_id": 99, "job_card_id": 99},
            )
            self.assertTrue(await communicator.receive_nothing(timeout=0.2))
            await communicator.disconnect()

        async_to_sync(assert_isolated)()
