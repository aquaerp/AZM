import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_delivered_at(apps, schema_editor):
    JobCard = apps.get_model("workshop", "JobCard")
    JobCard.objects.filter(status="delivered", delivered_at__isnull=True).update(delivered_at=models.F("status_updated_at"), delivery_method="manual")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0009_inventory_role_and_auto_delivery"),
        ("workshop", "0002_jobcard_portal_token"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(model_name="jobcard", name="delivered_at", field=models.DateTimeField(blank=True, null=True, verbose_name="تاريخ التسليم الفعلي")),
        migrations.AddField(model_name="jobcard", name="delivery_method", field=models.CharField(blank=True, choices=[("manual", "يدوي"), ("automatic", "آلي")], max_length=20, verbose_name="طريقة التسليم")),
        migrations.AddField(model_name="jobcard", name="delivered_by", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="delivered_job_cards", to=settings.AUTH_USER_MODEL)),
        migrations.RunPython(backfill_delivered_at, migrations.RunPython.noop),
    ]
