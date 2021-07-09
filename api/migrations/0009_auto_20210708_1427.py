# Generated by Django 3.2.5 on 2021-07-08 14:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_alter_task_case'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskstage',
            name='json_schema',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='taskstage',
            name='ui_schema',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='webhookstage',
            name='json_schema',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='webhookstage',
            name='ui_schema',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
