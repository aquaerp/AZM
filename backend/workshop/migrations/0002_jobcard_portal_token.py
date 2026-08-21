import uuid

from django.db import migrations, models


def populate_portal_tokens(apps, schema_editor):
    JobCard = apps.get_model("workshop", "JobCard")
    for job_card in JobCard.objects.filter(portal_token__isnull=True).iterator():
        job_card.portal_token = uuid.uuid4()
        job_card.save(update_fields=("portal_token",))


class Migration(migrations.Migration):
    dependencies = [("workshop", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="jobcard",
            name="portal_token",
            field=models.UUIDField(null=True, unique=True),
        ),
        migrations.RunPython(populate_portal_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="jobcard",
            name="portal_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
