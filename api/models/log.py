from django.db import models

from api.models import BaseDatesModel, CampaignInterface


class Log(BaseDatesModel, CampaignInterface):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    json = models.JSONField(blank=True)
    campaign = models.ForeignKey(
        "Campaign",
        related_name="logs",
        on_delete=models.CASCADE,
        help_text="Campaign related to the issue in the log"
    )
    chain = models.ForeignKey(
        "Chain",
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Chain related to the issue in the log"
    )
    stage = models.ForeignKey(
        "Stage",
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Stage related to the issue in the log"
    )
    case = models.ForeignKey(
        "Case",
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Case related to the issue in the log"
    )
    task = models.ForeignKey(
        "Task",
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Task related to the issue in the log"
    )
    user = models.ForeignKey(
        "CustomUser",
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="User related to the issue in the log"
    )
    track = models.ForeignKey(
        "Track",
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Track related to the issue in the log"
    )
    rank = models.ForeignKey(
        "Rank",
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Rank related to the issue in the log"
    )
    rank_limit = models.ForeignKey(
        "RankLimit",
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="RankLimit related to the issue in the log"
    )
    rank_record = models.ForeignKey(
        "RankLimit",
        on_delete=models.CASCADE,
        related_name="rr_logs",
        blank=True,
        null=True,
        help_text="RankRecord related to the issue in the log"
    )

    def get_campaign(self):
        return self.campaign
