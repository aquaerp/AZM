from rest_framework.routers import DefaultRouter

from .views import CustomerViewSet, JobCardViewSet, ServiceViewSet, VehicleViewSet

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customer")
router.register("vehicles", VehicleViewSet, basename="vehicle")
router.register("services", ServiceViewSet, basename="service")
router.register("job-cards", JobCardViewSet, basename="job-card")

urlpatterns = router.urls
