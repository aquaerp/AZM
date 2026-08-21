from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_workshop_business_fields")]

    operations = [
        migrations.CreateModel(
            name="SubscriptionPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("code", models.SlugField(max_length=50, unique=True)),
                ("monthly_price", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("max_users", models.PositiveIntegerField(default=5)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("monthly_price", "name")},
        ),
        migrations.CreateModel(
            name="WorkshopSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("trial", "فترة تجريبية"), ("active", "نشط"), ("past_due", "متأخر"), ("suspended", "معلق"), ("cancelled", "ملغي")], default="trial", max_length=20)),
                ("started_at", models.DateField()),
                ("current_period_end", models.DateField(blank=True, null=True)),
                ("auto_renew", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="subscriptions", to="accounts.subscriptionplan")),
                ("workshop", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="subscription", to="accounts.workshop")),
            ],
            options={"ordering": ("current_period_end", "workshop__name")},
        ),
    ]
