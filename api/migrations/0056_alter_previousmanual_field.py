# Generated by Django 3.2.8 on 2022-06-20 04:55

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0055_auto_20220617_1159'),
    ]

    operations = [
        migrations.AlterField(
            model_name='previousmanual',
            name='field',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=250), size=None),
        ),
    ]
