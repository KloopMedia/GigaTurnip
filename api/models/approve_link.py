from django.db import models

from api.models import BaseDatesModel, CampaignInterface


class ApproveLink(BaseDatesModel, CampaignInterface):
    campaign = models.ForeignKey(
        "Campaign",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        help_text="Campaign that own the campaign linker."
    )

    linker = models.ForeignKey(
        "CampaignLinker",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        help_text="Fk linker."
    )

    rank = models.ForeignKey(
        "Rank",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="Rank that will be assigned to user."
    )

    task_stage = models.ForeignKey(
        "TaskStage",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="Task will created on this stage and assign to the "
                  "income user."
    )

    notification = models.ForeignKey(
        "AutoNotification",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="Auto Notification will create notification to the user."
    )

    approved = models.BooleanField(
        default=False,
        help_text="Status about approved link. "
                  "False - rank would not be assigned."
    )

    def get_campaign(self):
        return self.campaign

    def connect_rank_with_user(self, user):
        if self.rank:
            self.rank.connect_with_user(user)
        if self.notification:
            self.notification.create_notification(
                None, None, user
            )

    def __str__(self):
        return "Camp: {}, Camp link: {}, Rank: {}".format(
            self.get_campaign().name, self.linker.id, self.rank
        )
