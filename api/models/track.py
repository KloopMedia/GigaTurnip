from django.db import models

from api.models import BaseModel, CampaignInterface
from api.models.stage import TaskStage


class Track(BaseModel, CampaignInterface):
    campaign = models.ForeignKey(
        "Campaign",
        related_name="tracks",
        on_delete=models.CASCADE,
        help_text="Campaign id"
    )
    default_rank = models.ForeignKey(
        "Rank",
        related_name="default_track",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Rank id"
    )
    registration_stage = models.ForeignKey(
        TaskStage,
        on_delete=models.CASCADE,
        related_name="tracks",
        blank=True,
        null=True,
        help_text="Registration stage"
    )

    def get_campaign(self):
        return self.campaign

    def __str__(self):
        return self.name
