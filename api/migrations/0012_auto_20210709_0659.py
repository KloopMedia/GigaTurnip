# Generated by Django 3.2.5 on 2021-07-09 06:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_auto_20210709_0643'),
    ]

    operations = [
        migrations.CreateModel(
            name='CampaignManagement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('campaign', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='campaign_managements', to='api.campaign')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='campaign_managements', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'campaign')},
            },
        ),
        migrations.AddField(
            model_name='campaign',
            name='managers',
            field=models.ManyToManyField(related_name='managed_campaigns', through='api.CampaignManagement', to=settings.AUTH_USER_MODEL),
        ),
    ]
