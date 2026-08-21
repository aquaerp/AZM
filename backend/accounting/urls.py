from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AccountingVoucherViewSet, ExpenseViewSet, InvoiceLineViewSet, InvoiceViewSet, ProfitLossView

router = DefaultRouter()
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("invoice-lines", InvoiceLineViewSet, basename="invoice-line")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("vouchers", AccountingVoucherViewSet, basename="voucher")

urlpatterns = router.urls + [path("reports/profit-loss/", ProfitLossView.as_view(), name="profit-loss")]
