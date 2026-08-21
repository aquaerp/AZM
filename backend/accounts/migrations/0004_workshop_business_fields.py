from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_auditevent_user_session_version")]

    operations = [
        migrations.AddField(model_name="workshop", name="legal_name", field=models.CharField(blank=True, max_length=200, verbose_name="الاسم القانوني")),
        migrations.AddField(model_name="workshop", name="tax_number", field=models.CharField(blank=True, max_length=15, verbose_name="الرقم الضريبي")),
        migrations.AddField(model_name="workshop", name="commercial_registration", field=models.CharField(blank=True, max_length=30, verbose_name="رقم السجل التجاري")),
        migrations.AddField(model_name="workshop", name="national_address", field=models.TextField(blank=True, verbose_name="العنوان الوطني")),
    ]
