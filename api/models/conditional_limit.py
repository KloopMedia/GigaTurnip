from django.core.validators import MaxValueValidator
from django.db import models

from api.models import BaseDatesModel, CampaignInterface


class ConditionalLimit(BaseDatesModel, CampaignInterface):
    conditional_stage = models.OneToOneField(
        "ConditionalStage",
        related_name='conditional_limit',
        on_delete=models.CASCADE,
        help_text='Allow to compare taskstage data in ConditionalStage'
    )
    order = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(1000000)]
    )
    def get_campaign(self):
        return self.conditional_stage.get_campaign()
