from rest_framework.routers import DefaultRouter

from .views import EmployeeCommissionViewSet, EmployeeViewSet, JobTaskViewSet

router = DefaultRouter()
router.register("employees", EmployeeViewSet, basename="employee")
router.register("tasks", JobTaskViewSet, basename="task")
router.register("commissions", EmployeeCommissionViewSet, basename="commission")

urlpatterns = router.urls
