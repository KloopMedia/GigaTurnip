# Generated by Django 3.2.8 on 2023-08-18 04:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0113_auto_20230815_0832'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskstage',
            name='filter_fields_schema',
            field=models.JSONField(blank=True, help_text='This filed will store schema for filters.', null=True),
        ),
    ]
