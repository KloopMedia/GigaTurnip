from django.apps import apps
from django.db import models

from api.models import BaseModel, CampaignInterface


class Rank(BaseModel, CampaignInterface):
    stages = models.ManyToManyField(
        "TaskStage",
        related_name="ranks",
        through="RankLimit",
        help_text="Stages id"
    )
    track = models.ForeignKey(
        "Track",
        related_name="ranks",
        on_delete=models.CASCADE,
        help_text="Track this rank belongs to",
        null=True,
        blank=True
    )
    prerequisite_ranks = models.ManyToManyField(
        "self",
        related_name="postrequisite_ranks",
        blank=True,
        symmetrical=False,
        help_text="Preceded tasks"
    )
    avatar = models.TextField(
        blank=True,
        help_text="Text or url to the SVG"
    )
    priority = models.PositiveIntegerField(
        default=0,
        blank=False,
        null=False,
        help_text="Priority of the rank in the system."
    )

    def get_campaign(self):
        return self.track.campaign

    def __str__(self):
        return self.name

    def connect_with_user(self, user):
        apps.get_model(app_label='api',
                       model_name='RankRecord').objects.get_or_create(
            user=user,
            rank=self,
        )
