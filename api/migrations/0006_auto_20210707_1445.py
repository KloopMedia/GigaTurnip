# Generated by Django 3.2.5 on 2021-07-07 14:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_task_assignee'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ranklimit',
            old_name='list_permission',
            new_name='is_listing_allowed',
        ),
        migrations.RemoveField(
            model_name='ranklimit',
            name='close_selection',
        ),
        migrations.RemoveField(
            model_name='ranklimit',
            name='close_submission',
        ),
        migrations.AddField(
            model_name='ranklimit',
            name='is_creation_open',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='ranklimit',
            name='is_selection_open',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='ranklimit',
            name='is_submission_open',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='ranklimit',
            name='stage',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ranklimits', to='api.taskstage'),
        ),
    ]
