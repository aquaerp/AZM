from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_default_trial_plan")]
    operations = [
        migrations.CreateModel(
            name="TrialRegistrationIdentity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("device_hash", models.CharField(max_length=64, unique=True)),
                ("ip_hash", models.CharField(max_length=64, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="trial_identity", to="accounts.user")),
                ("workshop", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="trial_identity", to="accounts.workshop")),
            ],
        )
    ]
