# Generated by Django 3.2.8 on 2024-01-18 12:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0117_counttasksmodifier'),
    ]

    operations = [
        migrations.RenameField(
            model_name='campaign',
            old_name='descriptor',
            new_name='short_description',
        ),
        migrations.AddField(
            model_name='campaign',
            name='featured',
            field=models.BooleanField(default=False, help_text='featured'),
        ),
        migrations.AddField(
            model_name='campaign',
            name='featured_image',
            field=models.TextField(blank=True, help_text='Text or url to the SVG'),
        ),
    ]