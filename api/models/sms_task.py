from django.db import models

from api.models import BaseDatesModel


class SMSTask(BaseDatesModel):
    sms_text = models.TextField(
        blank=False,
        null=False,
        help_text="Text of the task."
    )

    phone = models.TextField(
        blank=False,
        null=False,
        help_text="Text of the task."
    )

    decreed = models.JSONField(
        null=True,
        blank=True,
        help_text="Decreed sms_text."
    )

    decompressed = models.JSONField(
        null=True,
        blank=True,
        help_text="Decompressed sms_text."
    )

    task = models.OneToOneField(
        "Task",
        on_delete=models.SET_NULL,
        related_name="sms_task",
        blank=True,
        null=True,
        help_text="Task that have been created based on task."
    )

    @staticmethod
    def text_decreed(text):
        return {"text": "decreed"}

    @staticmethod
    def text_decompress(text):
        return {"text": "decompressed"}

    def __str__(self):
        return "{}: {}".format(self.id, self.phone)