from django.db import models

from api.models import BaseDatesModel


class TestWebhook(BaseDatesModel):
    expected_task = models.OneToOneField(
        'Task',
        related_name='expected_task',
        blank=False,
        help_text='task, with the answers you expect to answer',
        on_delete=models.CASCADE
    )
    sent_task = models.OneToOneField(
        'Task',
        related_name='sent_task',
        blank=False,
        help_text='task to be sent',
        on_delete=models.CASCADE
    )
