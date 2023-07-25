import json

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

    source = models.TextField(
        blank=True,
        null=True,
        help_text="Accepted data."
    )

    decrypted = models.TextField(
        null=True,
        blank=True,
        help_text="Decreed sms_text."
    )

    decompressed = models.TextField(
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
    def text_decryption(text):
        return {"text": "decreed"}

    @staticmethod
    def text_decompression(text):
        return {"text": "decompressed"}

    @property
    def decrypted_dict(self):
        if self.decrypted:
            try:
                return json.loads(self.decrypted)
            finally:
                return None
        return None

    def __str__(self):
        return "{}: {}".format(self.id, self.phone)