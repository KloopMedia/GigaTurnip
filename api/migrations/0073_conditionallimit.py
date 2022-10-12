# Generated by Django 3.2.8 on 2022-10-12 08:06

import api.models
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0072_alter_adminpreference_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConditionalLimit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Time of creation')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Last update time')),
                ('order', models.PositiveIntegerField(default=0, validators=[django.core.validators.MaxValueValidator(1000000)])),
                ('conditional_stage', models.OneToOneField(help_text='Allow to compare taskstage data in ConditionalStage', on_delete=django.db.models.deletion.CASCADE, related_name='conditional_limit', to='api.conditionalstage')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, api.models.CampaignInterface),
        ),
    ]
