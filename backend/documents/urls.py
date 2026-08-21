from rest_framework.routers import DefaultRouter

from .views import DocumentExpiryAlertViewSet, DocumentViewSet

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")
router.register("alerts", DocumentExpiryAlertViewSet, basename="document-alert")

urlpatterns = router.urls
