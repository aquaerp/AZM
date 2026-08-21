from django.urls import path

from .views import PublicJobStatusView

urlpatterns = [path("jobs/<uuid:token>/", PublicJobStatusView.as_view(), name="public-job-status")]
