# Generated by Django 3.2.8 on 2022-03-29 16:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0049_responseflattener'),
    ]

    operations = [
        migrations.AddField(
            model_name='responseflattener',
            name='flatten_all',
            field=models.BooleanField(default=False, help_text='Copy all response fields even they deeper than first level.'),
        ),
    ]
