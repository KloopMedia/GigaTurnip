from django.db import models
from polymorphic.models import PolymorphicModel

from api.models import BaseModel, CampaignInterface


class Stage(PolymorphicModel, BaseModel, CampaignInterface):
    x_pos = models.DecimalField(
        max_digits=17,
        decimal_places=3,
        help_text="Starting position of 'x' coordinate "
                  "to draw on Giga Turnip Chain frontend interface"
    )
    y_pos = models.DecimalField(
        max_digits=17,
        decimal_places=3,
        help_text="Starting position of 'y' coordinate "
                  "to draw on Giga Turnip Chain frontend interface"
    )
    chain = models.ForeignKey(
        "Chain",
        on_delete=models.CASCADE,
        related_name="stages",
        help_text="Chain id"
    )

    in_stages = models.ManyToManyField(
        "self",
        related_name="out_stages",
        symmetrical=False,
        blank=True,
        help_text="List of previous id stages"
    )

    def get_campaign(self):
        return self.chain.campaign

    def add_stage(self, stage):
        stage.chain = self.chain
        if not hasattr(stage, "name"):
            stage.name = "NoName"
        if not hasattr(stage, "x_pos") or stage.x_pos is None:
            stage.x_pos = 1
        if not hasattr(stage, "y_pos") or stage.y_pos is None:
            stage.y_pos = 1
        stage.save()
        stage.in_stages.add(self)
        return stage

    def __str__(self):
        return f"ID: {self.id}; {self.name}"
