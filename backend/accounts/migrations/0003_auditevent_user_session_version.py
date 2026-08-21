import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_workshop_roles")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="session_version",
            field=models.PositiveIntegerField(default=0, editable=False),
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=80)),
                ("entity_type", models.CharField(max_length=120)),
                ("entity_id", models.CharField(blank=True, max_length=80)),
                ("before", models.JSONField(blank=True, default=dict)),
                ("after", models.JSONField(blank=True, default=dict)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="audit_events", to="accounts.user")),
                ("workshop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="audit_events", to="accounts.workshop")),
            ],
            options={"ordering": ("-created_at", "-id")},
        ),
        migrations.AddIndex(model_name="auditevent", index=models.Index(fields=["workshop", "created_at"], name="accounts_au_worksho_57713d_idx")),
        migrations.AddIndex(model_name="auditevent", index=models.Index(fields=["workshop", "entity_type", "entity_id"], name="accounts_au_worksho_36ac8d_idx")),
    ]
