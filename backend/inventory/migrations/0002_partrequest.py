import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0009_inventory_role_and_auto_delivery"),
        ("inventory", "0001_initial"),
        ("workshop", "0003_jobcard_delivery"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PartRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name="الكمية المطلوبة")),
                ("status", models.CharField(choices=[("requested", "مطلوبة"), ("approved", "معتمدة"), ("fulfilled", "تم الصرف"), ("rejected", "مرفوضة")], default="requested", max_length=20)),
                ("notes", models.TextField(blank=True, verbose_name="ملاحظات الفني")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("fulfilled_usage", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="source_request", to="inventory.partusage")),
                ("job_card", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="part_requests", to="workshop.jobcard")),
                ("part", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requests", to="inventory.part")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="part_requests_created", to=settings.AUTH_USER_MODEL)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="part_requests_reviewed", to=settings.AUTH_USER_MODEL)),
                ("workshop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="%(class)ss", to="accounts.workshop")),
            ],
            options={"ordering": ("-created_at",), "indexes": [models.Index(fields=["workshop", "status"], name="inventory_p_worksho_req_idx"), models.Index(fields=["workshop", "requested_by"], name="inventory_p_worksho_user_idx")]},
        ),
    ]
