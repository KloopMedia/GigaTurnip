# Generated by Django 3.2.8 on 2022-06-01 05:00

import api.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0052_auto_20220518_1215'),
    ]

    operations = [
        migrations.CreateModel(
            name='DynamicJson',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Time of creation')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Last update time')),
                ('dynamic_fields', models.JSONField(default=None, help_text='Get top level fields with dynamic answers')),
                ('webhook_address', models.URLField(blank=True, help_text='Webhook URL address. If not empty, field indicates that task should be given not to a user in the system, but to a webhook. Only data from task directly preceding webhook is sent. All fields related to user assignment are ignored,if this field is not empty.', max_length=1000, null=True)),
                ('task_stage', models.ForeignKey(help_text='Stage where we want set answers dynamicly', on_delete=django.db.models.deletion.CASCADE, related_name='dynamic_jsons', to='api.taskstage')),
            ],
            options={
                'ordering': ['created_at', 'updated_at'],
            },
            bases=(models.Model, api.models.CampaignInterface),
        ),
    ]
