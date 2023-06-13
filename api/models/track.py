from django.db import models

from api.models import BaseModel, CampaignInterface


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

    def get_campaign(self):
        return self.campaign

    def __str__(self):
        return self.name
