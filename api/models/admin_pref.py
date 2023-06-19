from django.db import models

from api.models.base import BaseDatesModel


class AdminPreference(BaseDatesModel):
    user = models.OneToOneField(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name='admin_preference',
        blank=True,
        null=True
    )
    campaign = models.ForeignKey(
        "Campaign",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    def __str__(self):
        return self.id.__str__()
