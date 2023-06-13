from django.db import models

from api.models import BaseDatesModel, CampaignInterface


class DynamicJson(BaseDatesModel, CampaignInterface):
    source = models.ForeignKey(
        "TaskStage",
        on_delete=models.SET_NULL,
        related_name='dynamic_jsons_source',
        blank=True,
        null=True,
        help_text="Stage where we want get main field data"
    )
    target = models.ForeignKey(
        "TaskStage",
        on_delete=models.CASCADE,
        related_name='dynamic_jsons_target',
        blank=False,
        null=False,
        help_text="Stage where we want set answers dynamically"
    )
    dynamic_fields = models.JSONField(
        default=None,
        null=False,
        help_text=(
            "Get top level fields with dynamic answers"
        )
    )
    webhook = models.ForeignKey(
        "Webhook",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text='Webhook using for updating schema answers'
    )
    obtain_options_from_stage = models.BooleanField(
        default=False,
        help_text='Get options from another stages.'
    )

    class Meta:
        ordering = ['created_at', 'updated_at', ]

    def get_campaign(self):
        return self.target.get_campaign()

    def __str__(self):
        return self.target.name
