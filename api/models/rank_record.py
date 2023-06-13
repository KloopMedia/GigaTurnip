from django.db import models

from api.models import BaseDatesModel, CampaignInterface


class RankRecord(BaseDatesModel, CampaignInterface):
    user = models.ForeignKey(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name='user_ranks',
        help_text="User id"
    )
    rank = models.ForeignKey(
        "Rank",
        on_delete=models.CASCADE,
        help_text="Rank id"
    )

    class Meta:
        unique_together = ['user', 'rank']

    def get_campaign(self):
        return self.rank.track.campaign

    def __str__(self):
        return str(self.rank.__str__() + " " + self.user.__str__())
