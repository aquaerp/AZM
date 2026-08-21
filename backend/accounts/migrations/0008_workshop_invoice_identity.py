from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0007_trialregistrationidentity")]

    operations = [
        migrations.AddField(model_name="workshop", name="email", field=models.EmailField(blank=True, max_length=254, verbose_name="البريد الإلكتروني")),
        migrations.AddField(model_name="workshop", name="website", field=models.URLField(blank=True, verbose_name="الموقع الإلكتروني")),
        migrations.AddField(model_name="workshop", name="street", field=models.CharField(blank=True, max_length=150, verbose_name="الشارع")),
        migrations.AddField(model_name="workshop", name="district", field=models.CharField(blank=True, max_length=100, verbose_name="الحي")),
        migrations.AddField(model_name="workshop", name="building_number", field=models.CharField(blank=True, max_length=20, verbose_name="رقم المبنى")),
        migrations.AddField(model_name="workshop", name="postal_code", field=models.CharField(blank=True, max_length=10, verbose_name="الرمز البريدي")),
        migrations.AddField(model_name="workshop", name="additional_number", field=models.CharField(blank=True, max_length=10, verbose_name="الرقم الإضافي")),
        migrations.AddField(model_name="workshop", name="latitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name="خط العرض")),
        migrations.AddField(model_name="workshop", name="longitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name="خط الطول")),
        migrations.AddField(model_name="workshop", name="logo", field=models.ImageField(blank=True, upload_to="workshop-logos/", verbose_name="شعار الورشة")),
    ]
