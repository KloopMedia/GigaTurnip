from django.db import models

from api.models import BaseDatesModel, CampaignInterface


class ErrorGroup(BaseDatesModel, CampaignInterface):
    type_name = models.CharField(
        verbose_name='type',
        max_length=512
    )

    @staticmethod
    def get_group(exc: type):
        group = ErrorGroup.objects.get_or_create(type_name=exc.__name__)[0]
        return group

    def __str__(self):
        return self.type_name

