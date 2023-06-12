from django.db import models

from api.models import BaseDatesModel, CampaignInterface


class RankLimit(BaseDatesModel, CampaignInterface):
    rank = models.ForeignKey(
        "Rank",
        on_delete=models.CASCADE,
        related_name="ranklimits",
        help_text="Rank id"
    )
    stage = models.ForeignKey(
        "TaskStage",
        on_delete=models.CASCADE,
        related_name="ranklimits",
        help_text="Stage id"
    )
    open_limit = models.IntegerField(
        default=0,
        help_text="The maximum number of tasks that "
                  "can be opened at the same time for a user"
    )
    total_limit = models.IntegerField(
        default=0,
        help_text="The maximum number of tasks that user can obtain"
    )
    is_listing_allowed = models.BooleanField(
        default=False,
        help_text="Allow user to see the list of created tasks"
    )
    is_submission_open = models.BooleanField(
        default=True,
        help_text="Allow user to submit a task"
    )
    is_selection_open = models.BooleanField(
        default=True,
        help_text="Allow user to select a task"
    )
    is_creation_open = models.BooleanField(
        default=True,
        help_text="Allow user to create a task"
    )

    class Meta:
        unique_together = ['rank', 'stage']

    def get_campaign(self):
        return self.stage.get_campaign()

    def __str__(self):
        return f"{self.rank} - {self.stage}"
