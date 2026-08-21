from django.db import migrations


def create_trial_plan(apps, schema_editor):
    SubscriptionPlan = apps.get_model("accounts", "SubscriptionPlan")
    SubscriptionPlan.objects.get_or_create(
        code="trial-14-days",
        defaults={
            "name": "تجربة 14 يومًا",
            "monthly_price": 0,
            "max_users": 3,
            "is_active": True,
        },
    )


def remove_unused_trial_plan(apps, schema_editor):
    SubscriptionPlan = apps.get_model("accounts", "SubscriptionPlan")
    SubscriptionPlan.objects.filter(code="trial-14-days", subscriptions__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_subscriptionplan_workshopsubscription")]
    operations = [migrations.RunPython(create_trial_plan, remove_unused_trial_plan)]
