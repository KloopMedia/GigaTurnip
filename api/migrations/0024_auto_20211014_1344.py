# Generated by Django 3.2.8 on 2021-10-14 13:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0023_remove_track_ranks'),
    ]

    operations = [
        migrations.AddField(
            model_name='rank',
            name='track',
            field=models.ForeignKey(blank=True, help_text='Track this rank belongs to', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ranks', to='api.track'),
        ),
        migrations.AlterField(
            model_name='track',
            name='default_rank',
            field=models.ForeignKey(blank=True, help_text='Rank id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='default_track', to='api.rank'),
        ),
    ]
