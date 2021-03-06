# Generated by Django 3.2.8 on 2021-11-19 11:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0034_alter_taskstage_assign_user_by'),
    ]

    operations = [
        migrations.CreateModel(
            name='Webhook',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Time of creation')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Last update time')),
                ('task_stage', models.OneToOneField(help_text='Parent TaskStage', on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='webhook', serialize=False, to='api.taskstage')),
                ('url', models.URLField(blank=True, help_text='Webhook URL address. If not empty, field indicates that task should be given not to a user in the system, but to a webhook. Only data from task directly preceding webhook is sent. All fields related to user assignment are ignored,if this field is not empty.', max_length=1000, null=True)),
                ('headers', models.JSONField(blank=True, help_text='Headers sent to webhook.')),
                ('response_field', models.TextField(blank=True, help_text='JSON response field name to extract data from. Ignored if webhook_address field is empty.', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
