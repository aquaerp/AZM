# Generated manually for accounting vouchers.
from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("accounting", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountingVoucher",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("voucher_number", models.CharField(blank=True, editable=False, max_length=24, unique=True)),
                ("voucher_type", models.CharField(choices=[("receipt", "سند قبض"), ("disbursement", "سند صرف")], max_length=16)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("party_name", models.CharField(max_length=150)),
                ("description", models.CharField(max_length=255)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("occurred_at", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expense", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="voucher", to="accounting.expense")),
                ("invoice", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="vouchers", to="accounting.invoice")),
                ("payment", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="voucher", to="accounting.payment")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_vouchers", to=settings.AUTH_USER_MODEL)),
                ("workshop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="%(class)ss", to="accounts.workshop")),
            ],
            options={"ordering": ("-occurred_at", "-created_at"), "verbose_name": "سند محاسبي", "verbose_name_plural": "سندات محاسبية"},
        ),
        migrations.AddIndex(model_name="accountingvoucher", index=models.Index(fields=["workshop", "voucher_type", "occurred_at"], name="accounting__worksho_09e8aa_idx")),
    ]
