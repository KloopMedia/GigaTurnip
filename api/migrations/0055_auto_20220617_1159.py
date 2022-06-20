# Generated by Django 3.2.8 on 2022-06-17 11:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0054_taskstage_external_metadata'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskstage',
            name='assign_user_by',
            field=models.CharField(choices=[('RA', 'Rank'), ('ST', 'Stage'), ('AU', 'Auto-complete'), ('PA', 'Previous manual')], default='RA', help_text="User assignment method (by 'Stage' or by 'Rank')", max_length=2),
        ),
        migrations.CreateModel(
            name='PreviousManual',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Time of creation')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Last update time')),
                ('field', models.CharField(help_text='Field from previous Task Stage where placed email or id of user to assign', max_length=200)),
                ('is_id', models.BooleanField(default=False, help_text='If True, user have to pass id. Otherwise, use have to pass email')),
                ('task_stage', models.OneToOneField(help_text='Point to find previous task stage', on_delete=django.db.models.deletion.CASCADE, related_name='previous_manual', to='api.taskstage')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
