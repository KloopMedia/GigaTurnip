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
        help_text="If true, this chain is an individual chain."
    )

    is_text_book = models.BooleanField(
        default=False,
        help_text=("If true, this chain is a text book, which means its stages "
                    "containing rich text will accessible at once to any logged in user "
                    "but without any tasks, tests, or progress tracking.")
    )

    new_task_view_mode = models.BooleanField(
        default=False,
        help_text="Use new task view mode"
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
