from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import AuditEventListView, AzmTokenObtainPairView, CurrentUserView, PlatformDashboardView, PlatformWorkshopListView, PlatformWorkshopSubscriptionView, RegisterView, SubscriptionPlanDetailView, SubscriptionPlanListCreateView, TeamListCreateView, TeamMemberDetailView, WorkshopProfileView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", AzmTokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("team/", TeamListCreateView.as_view(), name="team"),
    path("team/<int:pk>/", TeamMemberDetailView.as_view(), name="team-member"),
    path("audit-events/", AuditEventListView.as_view(), name="audit-events"),
    path("workshop/", WorkshopProfileView.as_view(), name="workshop-profile"),
    path("platform/dashboard/", PlatformDashboardView.as_view(), name="platform-dashboard"),
    path("platform/plans/", SubscriptionPlanListCreateView.as_view(), name="platform-plans"),
    path("platform/plans/<int:pk>/", SubscriptionPlanDetailView.as_view(), name="platform-plan-detail"),
    path("platform/workshops/", PlatformWorkshopListView.as_view(), name="platform-workshops"),
    path("platform/workshops/<int:pk>/subscription/", PlatformWorkshopSubscriptionView.as_view(), name="platform-workshop-subscription"),
]
