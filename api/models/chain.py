from django.db import models

from api.models import BaseModel, CampaignInterface


class Chain(BaseModel, CampaignInterface):
    campaign = models.ForeignKey(
        "Campaign",
        on_delete=models.CASCADE,
        related_name="chains",
        help_text="Campaign id"
    )
    is_individual = models.BooleanField(
        default=False,
    )
    def get_campaign(self):
        return self.campaign

    def __str__(self):
        return self.name
