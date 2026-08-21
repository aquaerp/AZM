from datetime import timedelta

from django.db.models import Count, F, OuterRef, Subquery, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import record_audit
from .permissions import IsManager, IsOwner
from .models import AuditEvent, SubscriptionPlan, User, Workshop, WorkshopSubscription
from .serializers import AuditEventSerializer, AzmTokenObtainPairSerializer, PlatformWorkshopSerializer, RegisterSerializer, StaffMemberCreateSerializer, StaffMemberUpdateSerializer, SubscriptionPlanSerializer, UserSerializer, WorkshopProfileSerializer, WorkshopSubscriptionSerializer


class AzmTokenObtainPairView(TokenObtainPairView):
    serializer_class = AzmTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    """Create a new workshop and its initial manager account."""

    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)


class CurrentUserView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class TeamListCreateView(generics.ListCreateAPIView):
    """Lets a workshop manager create technicians required for job assignment."""

    permission_classes = (IsManager,)

    def get_queryset(self):
        return User.objects.filter(workshop=self.request.user.workshop).exclude(pk=self.request.user.pk).order_by("first_name", "username")

    def get_serializer_class(self):
        return StaffMemberCreateSerializer if self.request.method == "POST" else UserSerializer

    def perform_create(self, serializer):
        member = serializer.save()
        record_audit(
            self.request,
            "team.member_created",
            member,
            after={"username": member.username, "role": member.role, "is_active": member.is_active},
        )


class TeamMemberDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsOwner,)
    serializer_class = StaffMemberUpdateSerializer
    http_method_names = ("get", "patch", "head", "options")

    def get_queryset(self):
        return User.objects.filter(workshop=self.request.user.workshop).exclude(pk=self.request.user.pk)

    def perform_update(self, serializer):
        member = self.get_object()
        before = {"first_name": member.first_name, "last_name": member.last_name, "email": member.email, "role": member.role, "is_active": member.is_active}
        member = serializer.save()
        after = {"first_name": member.first_name, "last_name": member.last_name, "email": member.email, "role": member.role, "is_active": member.is_active}
        record_audit(self.request, "team.member_updated", member, before=before, after=after)


class AuditEventListView(generics.ListAPIView):
    permission_classes = (IsOwner,)
    serializer_class = AuditEventSerializer

    def get_queryset(self):
        return AuditEvent.objects.select_related("actor").filter(workshop=self.request.user.workshop)


class WorkshopProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsOwner,)
    serializer_class = WorkshopProfileSerializer
    http_method_names = ("get", "patch", "head", "options")

    def get_object(self):
        return self.request.user.workshop

    def perform_update(self, serializer):
        workshop = self.get_object()
        fields = ("name", "phone", "email", "website", "city", "legal_name", "tax_number", "commercial_registration", "national_address", "street", "district", "building_number", "postal_code", "additional_number", "latitude", "longitude", "auto_deliver_paid_ready_jobs", "logo")
        before = {field: str(getattr(workshop, field)) if field == "logo" else getattr(workshop, field) for field in fields}
        workshop = serializer.save()
        after = {field: str(getattr(workshop, field)) if field == "logo" else getattr(workshop, field) for field in fields}
        record_audit(self.request, "workshop.profile_updated", workshop, before=before, after=after)


class PlatformDashboardView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request):
        today = timezone.localdate()
        subscriptions = WorkshopSubscription.objects.select_related("plan")
        active = subscriptions.filter(status=WorkshopSubscription.Status.ACTIVE)
        return Response({
            "workshops": Workshop.objects.count(),
            "users": User.objects.filter(is_superuser=False).count(),
            "active_subscriptions": active.count(),
            "trial_subscriptions": subscriptions.filter(status=WorkshopSubscription.Status.TRIAL).count(),
            "past_due_subscriptions": subscriptions.filter(status=WorkshopSubscription.Status.PAST_DUE).count(),
            "suspended_subscriptions": subscriptions.filter(status__in=(WorkshopSubscription.Status.SUSPENDED, WorkshopSubscription.Status.CANCELLED)).count(),
            "unassigned_workshops": Workshop.objects.filter(subscription__isnull=True).count(),
            "expiring_soon": subscriptions.filter(current_period_end__range=(today, today + timedelta(days=30))).count(),
            "monthly_recurring_revenue": active.aggregate(total=Sum("plan__monthly_price"))["total"] or 0,
        })


class SubscriptionPlanListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = SubscriptionPlanSerializer

    def get_queryset(self):
        return SubscriptionPlan.objects.annotate(subscriptions_count=Count("subscriptions"))


class SubscriptionPlanDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = SubscriptionPlanSerializer
    http_method_names = ("get", "patch", "head", "options")

    def get_queryset(self):
        return SubscriptionPlan.objects.annotate(subscriptions_count=Count("subscriptions"))


class PlatformWorkshopListView(generics.ListAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = PlatformWorkshopSerializer

    def get_queryset(self):
        owner = User.objects.filter(workshop=OuterRef("pk"), role=User.Role.OWNER, is_active=True).order_by("id").values("username")[:1]
        return Workshop.objects.select_related("subscription__plan").annotate(users_count=Count("users"), owner_username=Subquery(owner)).order_by("-created_at")


class PlatformWorkshopSubscriptionView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def patch(self, request, pk):
        workshop = get_object_or_404(Workshop, pk=pk)
        current = getattr(workshop, "subscription", None)
        serializer = WorkshopSubscriptionSerializer(current, data=request.data, partial=current is not None)
        serializer.is_valid(raise_exception=True)
        subscription = serializer.save() if current else serializer.save(workshop=workshop)
        if subscription.status in (WorkshopSubscription.Status.SUSPENDED, WorkshopSubscription.Status.CANCELLED):
            User.objects.filter(workshop=workshop).update(session_version=F("session_version") + 1)
        return Response(WorkshopSubscriptionSerializer(subscription).data, status=status.HTTP_200_OK)
