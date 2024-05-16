from django.db import models
from api.models.base import BaseModel


class Volume(BaseModel, models.Model):
    track_fk = models.ForeignKey(
        "Track",
        on_delete=models.CASCADE,
        help_text=(
            "Track this volume belongs to."
        )
     )

    order = models.IntegerField(help_text=(
            "Order inside track"
        )
    )

    opening_ranks = models.ManyToManyField(
        "Rank",
        related_name='opening_ranks',
        help_text=(
            "Ranks needed to open this volume"
        )
    )

    closing_ranks = models.ManyToManyField(
        "Rank",
        related_name='closing_ranks',
        help_text=(
            "Ranks needed to close this volume"
        )
   )

    not_yet_open_message = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "Message for users when volume isn't yet opened"
        )
    )

    already_closed_message = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "Message for users when volume is already closed"
        )
    )

    show_tags = models.BooleanField(
        default=False,
        null=True,
        help_text= 'Flag to determine if tags should be shown for the volume'
    )

    my_tasks_text = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "Text to display for 'My Tasks' section related to the volume"
        )
    )

    active_tasks_text = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "Text to display for 'Active Tasks' section related to the volume"
        )
    )

    returned_tasks_text = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "Text to display for 'Returned Tasks' section related to the volume"
        )
    )

    completed_tasks_text = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "Text to display for 'Completed Tasks' section related to the volume"
        )
    )