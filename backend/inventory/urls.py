from rest_framework.routers import DefaultRouter

from .views import InventoryAlertViewSet, PartRequestViewSet, PartUsageViewSet, PartViewSet, SupplierViewSet

router = DefaultRouter()
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("parts", PartViewSet, basename="part")
router.register("part-usages", PartUsageViewSet, basename="part-usage")
router.register("part-requests", PartRequestViewSet, basename="part-request")
router.register("alerts", InventoryAlertViewSet, basename="inventory-alert")

urlpatterns = router.urls
