# Generated by Django 3.2.8 on 2021-12-01 03:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0044_stagepublisher'),
    ]

    operations = [
        migrations.AddField(
            model_name='stagepublisher',
            name='is_public',
            field=models.BooleanField(default=False, help_text='Indicates tasks of this stage may be accessed by unauthenticated users.'),
        ),
    ]
