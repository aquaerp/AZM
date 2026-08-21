from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0008_workshop_invoice_identity")]

    operations = [
        migrations.AddField(
            model_name="workshop",
            name="auto_deliver_paid_ready_jobs",
            field=models.BooleanField(default=False, verbose_name="تسليم البطاقة الجاهزة آليًا بعد اكتمال السداد"),
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(choices=[("owner", "مالك الورشة"), ("manager", "مدير الورشة"), ("technician", "فني"), ("accountant", "محاسب"), ("receptionist", "موظف استقبال"), ("storekeeper", "أمين مخزن")], default="technician", max_length=20),
        ),
    ]
