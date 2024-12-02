# Generated by Django 3.2.8 on 2024-11-05 10:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0122_auto_20240725_0638'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='contact_us_link',
            field=models.CharField(blank=True, help_text="Link to 'Contact Us' button", max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='campaign',
            name='new_task_view_mode',
            field=models.BooleanField(default=False, help_text='Use new task view mode'),
        ),
    ]
