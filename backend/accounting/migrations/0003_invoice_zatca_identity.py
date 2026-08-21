import uuid

import django.db.models.deletion
from django.db import migrations, models


def assign_workshop_sequences(apps, schema_editor):
    Invoice = apps.get_model("accounting", "Invoice")
    workshop_ids = Invoice.objects.order_by().values_list("workshop_id", flat=True).distinct()
    for workshop_id in workshop_ids:
        for sequence, invoice in enumerate(Invoice.objects.filter(workshop_id=workshop_id).order_by("created_at", "id"), start=1):
            Invoice.objects.filter(pk=invoice.pk).update(sequence_number=sequence, invoice_number=f"INV-{sequence:06d}")


class Migration(migrations.Migration):
    dependencies = [("accounting", "0002_accountingvoucher"), ("accounts", "0004_workshop_business_fields")]

    operations = [
        migrations.AlterField(model_name="invoice", name="invoice_number", field=models.CharField(blank=True, editable=False, max_length=32)),
        migrations.AddField(model_name="invoice", name="sequence_number", field=models.PositiveBigIntegerField(editable=False, null=True)),
        migrations.AddField(model_name="invoice", name="uuid", field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
        migrations.AlterField(model_name="invoice", name="issued_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.RunPython(assign_workshop_sequences, migrations.RunPython.noop),
        migrations.AlterField(model_name="invoice", name="sequence_number", field=models.PositiveBigIntegerField(editable=False)),
        migrations.AddConstraint(model_name="invoice", constraint=models.UniqueConstraint(fields=("workshop", "sequence_number"), name="unique_invoice_sequence_per_workshop")),
        migrations.AddConstraint(model_name="invoice", constraint=models.UniqueConstraint(fields=("workshop", "invoice_number"), name="unique_invoice_number_per_workshop")),
    ]
