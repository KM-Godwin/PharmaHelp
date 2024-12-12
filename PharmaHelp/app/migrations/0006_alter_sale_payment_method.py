# Generated by Django 5.1.4 on 2024-12-07 06:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0005_alter_sale_options_sale_app_sale_date_af6fc7_idx_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sale',
            name='payment_method',
            field=models.CharField(choices=[('CASH', 'Cash'), ('MPESA', 'MPESA')], default='CASH', max_length=20),
        ),
    ]
