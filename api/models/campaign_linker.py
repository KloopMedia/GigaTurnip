from django.apps import apps
from django.db import models

from api.models import BaseModel, CampaignInterface


class CampaignLinker(BaseModel, CampaignInterface):
    out_stage = models.ForeignKey(
        "TaskStage",
        on_delete=models.SET_NULL,
        related_name='stage_campaign_linkers_set',
        blank=True,
        null=True,
        help_text="Stage that triggers assign new rank to user."
    )

    stage_with_user = models.ForeignKey(
        "TaskStage",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        help_text="Stage with user to assignee new rank."

    )

    target = models.ForeignKey(
        "Campaign",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        help_text="Target campaign that will see campaign link."
    )

    def get_campaign(self):
        return self.out_stage.get_campaign()

    def get_user(self, case):
        return case.tasks.filter(
            stage=self.stage_with_user).first().assignee

    def __str__(self):
        return self.get_campaign().name + " " + self.name
