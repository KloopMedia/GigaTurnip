from django.db import models
from api.models.base import BaseModel


class Volume(BaseModel, models.Model):
    track_fk = models.ForeignKey("Track", on_delete=models.CASCADE)
    order = models.IntegerField()
    opening_ranks = models.ManyToManyField("Rank", related_name='opening_ranks')
    closing_ranks = models.ManyToManyField("Rank", related_name='closing_ranks')
    not_yet_open_message = models.TextField(
        null=True,
        blank=True,
        help_text=(
            # "TODO"
        )
    )

    already_closed_message = models.TextField(
        null=True,
        blank=True,
        help_text=(
            # "TODO"
        )
    )

    show_tags = models.BooleanField(
        default=False,
        null=True,
        help_text= '' # "TODO"
    )

    my_tasks_text = models.TextField(
        null=True,
        blank=True,
        help_text=(
            # "TODO"
        )
    )

    active_tasks_text = models.TextField(
        null=True,
        blank=True,
        help_text=(
            # "TODO"
        )
    )

    returned_tasks_text = models.TextField(
        null=True,
        blank=True,
        help_text=(
            # "TODO"
        )
    )

    completed_tasks_text = models.TextField(
        null=True,
        blank=True,
        help_text=(
            # "TODO"
        )
    )