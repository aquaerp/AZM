from django.db import migrations, models


def promote_first_manager_to_owner(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Workshop = apps.get_model("accounts", "Workshop")
    for workshop_id in Workshop.objects.values_list("id", flat=True).iterator():
        manager = User.objects.filter(workshop_id=workshop_id, role="manager", is_active=True).order_by("date_joined", "id").first()
        if manager:
            User.objects.filter(pk=manager.pk).update(role="owner")


def restore_owners_as_managers(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="owner").update(role="manager")


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("owner", "مالك الورشة"),
                    ("manager", "مدير الورشة"),
                    ("technician", "فني"),
                    ("accountant", "محاسب"),
                    ("receptionist", "موظف استقبال"),
                ],
                default="technician",
                max_length=20,
            ),
        ),
        migrations.RunPython(promote_first_manager_to_owner, restore_owners_as_managers),
    ]
