from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import AuditEvent, SubscriptionPlan, User, Workshop, WorkshopSubscription


class AuthenticationApiTests(APITestCase):
    def test_register_creates_manager_and_workshop(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "manager1",
                "password": "SafePass123!",
                "first_name": "طارق",
                "last_name": "حسين",
                "email": "tariq@example.com",
                "workshop_name": "ورشة عزم",
            },
            HTTP_X_AZM_DEVICE_ID="test-device-0000000000000001",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="manager1")
        self.assertEqual(user.role, User.Role.OWNER)
        self.assertEqual(Workshop.objects.count(), 1)
        subscription = WorkshopSubscription.objects.get(workshop=user.workshop)
        self.assertEqual(subscription.status, WorkshopSubscription.Status.TRIAL)
        self.assertEqual(subscription.plan.code, "trial-14-days")
        self.assertEqual(subscription.current_period_end, timezone.localdate() + timedelta(days=13))

    def test_trial_registration_rejects_reused_device_with_new_identity(self):
        first = {"username": "first-trial", "password": "SafePass123!", "email": "first@example.com", "workshop_name": "First workshop"}
        second = {"username": "second-trial", "password": "SafePass123!", "email": "second@example.com", "workshop_name": "Second workshop"}

        first_response = self.client.post("/api/auth/register/", first, HTTP_X_AZM_DEVICE_ID="same-device-000000000000001", REMOTE_ADDR="10.0.0.1")
        second_response = self.client.post("/api/auth/register/", second, HTTP_X_AZM_DEVICE_ID="same-device-000000000000001", REMOTE_ADDR="10.0.0.2")

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Workshop.objects.count(), 1)

    def test_trial_registration_rejects_reused_ip_with_new_device(self):
        first = {"username": "ip-first", "password": "SafePass123!", "email": "ip-first@example.com", "workshop_name": "IP First"}
        second = {"username": "ip-second", "password": "SafePass123!", "email": "ip-second@example.com", "workshop_name": "IP Second"}

        first_response = self.client.post("/api/auth/register/", first, HTTP_X_AZM_DEVICE_ID="first-device-000000000000001", REMOTE_ADDR="10.0.0.3")
        second_response = self.client.post("/api/auth/register/", second, HTTP_X_AZM_DEVICE_ID="second-device-00000000000001", REMOTE_ADDR="10.0.0.3")

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Workshop.objects.count(), 1)

    def test_login_returns_jwt_tokens(self):
        user = User.objects.create_user(username="tech1", password="SafePass123!")

        response = self.client.post("/api/auth/login/", {"username": user.username, "password": "SafePass123!"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_manager_can_create_technician_for_own_workshop(self):
        workshop = Workshop.objects.create(name="ورشة عزم")
        manager = User.objects.create_user(username="manager", password="SafePass123!", workshop=workshop, role=User.Role.MANAGER)
        self.client.force_authenticate(manager)

        response = self.client.post(
            "/api/auth/team/",
            {"username": "tech2", "password": "SafePass123!", "first_name": "سجاد", "last_name": "علي", "role": "technician"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="tech2")
        self.assertEqual(user.workshop, workshop)
        self.assertEqual(user.role, User.Role.TECHNICIAN)

    def test_manager_can_list_own_team(self):
        workshop = Workshop.objects.create(name="ورشة عزم")
        manager = User.objects.create_user(username="manager-list", password="SafePass123!", workshop=workshop, role=User.Role.MANAGER)
        teammate = User.objects.create_user(username="tech-list", password="SafePass123!", workshop=workshop, role=User.Role.TECHNICIAN)
        self.client.force_authenticate(manager)

        response = self.client.get("/api/auth/team/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["username"] for item in response.data], [teammate.username])

    def test_manager_role_without_workshop_has_no_manager_permissions(self):
        orphan_manager = User.objects.create_user(username="orphan-manager", password="SafePass123!", role=User.Role.MANAGER)
        self.client.force_authenticate(orphan_manager)

        response = self.client.get("/api/auth/team/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_create_manager_and_receptionist_but_not_another_owner(self):
        workshop = Workshop.objects.create(name="Owner workshop")
        owner = User.objects.create_user(username="owner", password="SafePass123!", workshop=workshop, role=User.Role.OWNER)
        self.client.force_authenticate(owner)

        manager = self.client.post("/api/auth/team/", {"username": "new-manager", "password": "SafePass123!", "role": "manager"})
        receptionist = self.client.post("/api/auth/team/", {"username": "reception", "password": "SafePass123!", "role": "receptionist"})
        another_owner = self.client.post("/api/auth/team/", {"username": "second-owner", "password": "SafePass123!", "role": "owner"})

        self.assertEqual(manager.status_code, status.HTTP_201_CREATED)
        self.assertEqual(receptionist.status_code, status.HTTP_201_CREATED)
        self.assertEqual(another_owner.status_code, status.HTTP_400_BAD_REQUEST)

    def test_role_change_is_audited_and_revokes_existing_jwt(self):
        workshop = Workshop.objects.create(name="Secure workshop")
        plan = SubscriptionPlan.objects.create(name="Secure plan", code="secure-plan")
        WorkshopSubscription.objects.create(workshop=workshop, plan=plan, status=WorkshopSubscription.Status.ACTIVE, started_at=timezone.localdate())
        owner = User.objects.create_user(username="secure-owner", password="SafePass123!", workshop=workshop, role=User.Role.OWNER)
        member = User.objects.create_user(username="member", password="SafePass123!", workshop=workshop, role=User.Role.TECHNICIAN)
        token_client = APIClient()
        login = token_client.post("/api/auth/login/", {"username": member.username, "password": "SafePass123!"})
        old_access = login.data["access"]
        self.client.force_authenticate(owner)

        response = self.client.patch(f"/api/auth/team/{member.id}/", {"role": "accountant"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event = AuditEvent.objects.get(action="team.member_updated", entity_id=str(member.id))
        self.assertEqual(event.before["role"], User.Role.TECHNICIAN)
        self.assertEqual(event.after["role"], User.Role.ACCOUNTANT)
        token_client.credentials(HTTP_AUTHORIZATION=f"Bearer {old_access}")
        self.assertEqual(token_client.get("/api/auth/me/").status_code, status.HTTP_401_UNAUTHORIZED)

    def test_audit_event_list_is_scoped_to_owner_workshop(self):
        workshop = Workshop.objects.create(name="Audit workshop")
        other_workshop = Workshop.objects.create(name="Other audit workshop")
        owner = User.objects.create_user(username="audit-owner", password="SafePass123!", workshop=workshop, role=User.Role.OWNER)
        other_owner = User.objects.create_user(username="other-audit-owner", password="SafePass123!", workshop=other_workshop, role=User.Role.OWNER)
        own_event = AuditEvent.objects.create(workshop=workshop, actor=owner, action="own", entity_type="test", entity_id="1")
        AuditEvent.objects.create(workshop=other_workshop, actor=other_owner, action="other", entity_type="test", entity_id="2")
        self.client.force_authenticate(owner)

        response = self.client.get("/api/auth/audit-events/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [own_event.id])

    def test_only_owner_can_update_workshop_business_profile(self):
        workshop = Workshop.objects.create(name="Business workshop")
        owner = User.objects.create_user(username="business-owner", password="SafePass123!", workshop=workshop, role=User.Role.OWNER)
        manager = User.objects.create_user(username="business-manager", password="SafePass123!", workshop=workshop, role=User.Role.MANAGER)
        payload = {"legal_name": "Azm Workshop LLC", "tax_number": "310123456789003", "commercial_registration": "1010123456", "national_address": "Riyadh"}
        self.client.force_authenticate(manager)
        denied = self.client.patch("/api/auth/workshop/", payload)
        self.client.force_authenticate(owner)

        updated = self.client.patch("/api/auth/workshop/", payload)

        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        workshop.refresh_from_db()
        self.assertEqual(workshop.tax_number, payload["tax_number"])
        self.assertTrue(AuditEvent.objects.filter(workshop=workshop, action="workshop.profile_updated").exists())

    def test_workshop_profile_rejects_invalid_tax_number(self):
        workshop = Workshop.objects.create(name="Tax workshop")
        owner = User.objects.create_user(username="tax-owner", password="SafePass123!", workshop=workshop, role=User.Role.OWNER)
        self.client.force_authenticate(owner)

        response = self.client.patch("/api/auth/workshop/", {"tax_number": "123"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PlatformAdminApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="platform-admin", password="SafePass123!", email="admin@example.com")
        self.workshop = Workshop.objects.create(name="Managed workshop", city="Riyadh")
        self.owner = User.objects.create_user(username="managed-owner", password="SafePass123!", workshop=self.workshop, role=User.Role.OWNER)

    def test_only_superuser_can_access_platform_dashboard(self):
        self.client.force_authenticate(self.owner)
        denied = self.client.get("/api/auth/platform/dashboard/")
        self.client.force_authenticate(self.admin)
        allowed = self.client.get("/api/auth/platform/dashboard/")

        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertEqual(allowed.data["workshops"], 1)
        self.assertEqual(allowed.data["unassigned_workshops"], 1)

    def test_superuser_can_create_plan_and_assign_subscription(self):
        self.client.force_authenticate(self.admin)
        plan_response = self.client.post("/api/auth/platform/plans/", {"name": "Professional", "code": "professional", "monthly_price": "299.00", "max_users": 15})
        subscription_response = self.client.patch(
            f"/api/auth/platform/workshops/{self.workshop.id}/subscription/",
            {"plan": plan_response.data["id"], "status": "active", "started_at": "2026-08-11", "current_period_end": "2026-09-10", "auto_renew": True},
        )

        self.assertEqual(plan_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(subscription_response.status_code, status.HTTP_200_OK)
        self.assertEqual(WorkshopSubscription.objects.get(workshop=self.workshop).plan.code, "professional")
        workshops = self.client.get("/api/auth/platform/workshops/")
        self.assertEqual(workshops.data[0]["owner_username"], self.owner.username)
        self.assertEqual(workshops.data[0]["users_count"], 1)

    def test_suspending_subscription_revokes_tokens_and_blocks_login(self):
        plan = SubscriptionPlan.objects.create(name="Basic", code="basic", monthly_price="99.00")
        WorkshopSubscription.objects.create(workshop=self.workshop, plan=plan, status=WorkshopSubscription.Status.ACTIVE, started_at="2026-08-11")
        token_client = APIClient()
        login = token_client.post("/api/auth/login/", {"username": self.owner.username, "password": "SafePass123!"})
        token_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.client.force_authenticate(self.admin)

        response = self.client.patch(f"/api/auth/platform/workshops/{self.workshop.id}/subscription/", {"status": "suspended"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(token_client.get("/api/auth/me/").status_code, status.HTTP_401_UNAUTHORIZED)
        blocked_login = APIClient().post("/api/auth/login/", {"username": self.owner.username, "password": "SafePass123!"})
        self.assertEqual(blocked_login.status_code, status.HTTP_400_BAD_REQUEST)

    def test_plan_user_limit_is_enforced_inside_workshop(self):
        plan = SubscriptionPlan.objects.create(name="Solo", code="solo", monthly_price="49.00", max_users=1)
        WorkshopSubscription.objects.create(workshop=self.workshop, plan=plan, status=WorkshopSubscription.Status.ACTIVE, started_at="2026-08-11")
        self.client.force_authenticate(self.owner)

        response = self.client.post("/api/auth/team/", {"username": "extra-user", "password": "SafePass123!", "role": "technician"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="extra-user").exists())

    def test_workshop_without_subscription_cannot_login(self):
        response = self.client.post("/api/auth/login/", {"username": self.owner.username, "password": "SafePass123!"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_trial_blocks_login_and_existing_jwt(self):
        plan = SubscriptionPlan.objects.create(name="Trial", code="expired-trial", monthly_price="0.00")
        subscription = WorkshopSubscription.objects.create(
            workshop=self.workshop,
            plan=plan,
            status=WorkshopSubscription.Status.TRIAL,
            started_at=timezone.localdate() - timedelta(days=14),
            current_period_end=timezone.localdate(),
        )
        token_client = APIClient()
        login = token_client.post("/api/auth/login/", {"username": self.owner.username, "password": "SafePass123!"})
        token_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        subscription.current_period_end = timezone.localdate() - timedelta(days=1)
        subscription.save(update_fields=("current_period_end", "updated_at"))

        self.assertEqual(token_client.get("/api/auth/me/").status_code, status.HTTP_401_UNAUTHORIZED)
        blocked_login = APIClient().post("/api/auth/login/", {"username": self.owner.username, "password": "SafePass123!"})
        self.assertEqual(blocked_login.status_code, status.HTTP_400_BAD_REQUEST)
