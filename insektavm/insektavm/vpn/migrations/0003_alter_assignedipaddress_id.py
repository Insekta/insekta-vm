# Generated by Django 4.2.1 on 2023-05-03 21:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vpn', '0002_auto_20160116_0101'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assignedipaddress',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
