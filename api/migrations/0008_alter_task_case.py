# Generated by Django 3.2.5 on 2021-07-08 14:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_auto_20210708_0553'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='case',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='api.case'),
        ),
    ]
