# Generated by Django 3.2.1 on 2021-06-29 10:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_taskstage_node_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskstage',
            name='copy_input',
            field=models.BooleanField(default=False),
        ),
    ]
