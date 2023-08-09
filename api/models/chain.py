from django.db import models

from api.constans import ChainConstants
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

    ORDER_TYPE_CHOICES = [
        (ChainConstants.CHRONOLOGICALLY, 'Chronologically'),
        (ChainConstants.GRAPH_FLOW, 'By Graph order'),
        (ChainConstants.ORDER, 'By manually order'),
    ]
    order_in_individuals = models.CharField(
        max_length=2,
        choices=ORDER_TYPE_CHOICES,
        default=ChainConstants.CHRONOLOGICALLY,
        help_text="What ordering will be used on tasks return in chain individuals."
    )
    def get_campaign(self):
        return self.campaign

    def __str__(self):
        return self.name
