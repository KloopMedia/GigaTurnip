# Generated by Django 3.2.8 on 2022-08-16 07:29

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0067_alter_rankrecord_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='trigger_go',
            field=models.CharField(blank=None, choices=[('', ''), ('FW', 'Forward'), ('BW', 'Backward'), ('LO', 'Last-one')], default='', help_text='Trigger gone in this direction and this notification has been created.', max_length=2),
        ),
        migrations.AddField(
            model_name='notification',
            name='trigger_task',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='api.task'),
        ),
        migrations.AddField(
            model_name='task',
            name='internal_metadata',
            field=models.JSONField(blank=True, default=None, help_text="The field for internal data that wouldn't be shown to the user.", null=True),
        ),
        migrations.AlterField(
            model_name='notification',
            name='target_user',
            field=models.ForeignKey(blank=True, help_text='User id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL),
        ),
    ]
