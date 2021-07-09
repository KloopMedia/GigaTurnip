# Generated by Django 3.2.5 on 2021-07-09 11:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_alter_task_responses'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskstage',
            name='json_schema',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='taskstage',
            name='ui_schema',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='webhookstage',
            name='json_schema',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='webhookstage',
            name='ui_schema',
            field=models.TextField(blank=True, null=True),
        ),
    ]
