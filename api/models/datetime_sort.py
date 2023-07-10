from django.db import models

from api.models import BaseDatesModel


class DatetimeSort(BaseDatesModel):
    stage = models.OneToOneField(
        "Stage",
        related_name='datetime_sort',
        blank=False,
        help_text='step sorted by datetime',
        on_delete=models.CASCADE
    )
    start_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text='the time when the task should open'
    )
    end_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text='the time when the task should close'
    )
    how_much = models.FloatField(
        blank=True,
        null=True,
        help_text='The task should become available to users in (measurement in hours)'
    )
    after_how_much = models.FloatField(
        blank=True,
        null=True,
        help_text='The task will no longer be available to users in (measurement in hours)'
    )
