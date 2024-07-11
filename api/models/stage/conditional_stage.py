from django.db import models

from . import Stage


class ConditionalStage(Stage):
    conditions = models.JSONField(
        null=True,
        help_text='JSON logic conditions'
    )
    pingpong = models.BooleanField(
        default=False,
        help_text='If True, makes \'in stages\' task incomplete'
    )
    prevent_duplicate = models.BooleanField(
        default=False,
        help_text='If true prevents duplicate task creation'
    )

