from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0075_datetimesort'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dynamicjson',
            name='task_stage',
            field=models.ForeignKey(help_text='Stage where we want set answers dynamically',
                                    on_delete=django.db.models.deletion.CASCADE, related_name='dynamic_jsons_target',
                                    to='api.taskstage')
        ),
        migrations.RenameField(
            model_name='dynamicjson',
            old_name='task_stage',
            new_name='target',
        ),
        migrations.AddField(
            model_name='dynamicjson',
            name='source',
            field=models.ForeignKey(blank=True, help_text='Stage where we want get main field data', null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='dynamic_jsons_source', to='api.taskstage'),
        ),
    ]
