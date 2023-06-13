from django.db import models

from api.models import BaseDatesModel, CampaignInterface


class CampaignManagement(BaseDatesModel, CampaignInterface):
    user = models.ForeignKey(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name="campaign_managements"
    )
    campaign = models.ForeignKey(
        "Campaign",
        on_delete=models.CASCADE,
        related_name="campaign_managements"
    )

    class Meta:
        unique_together = ['user', 'campaign']

    def get_campaign(self):
        return self.campaign

    def __str__(self):
        return f"{self.campaign.name} - {self.user}"
