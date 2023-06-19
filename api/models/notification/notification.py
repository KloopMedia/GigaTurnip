from django.apps import apps
from django.db import models

from api.constans import AutoNotificationConstants
from api.models import BaseDatesModel, CampaignInterface


class Notification(BaseDatesModel, CampaignInterface):
    title = models.CharField(
        max_length=150,
        help_text="Instance title"
    )

    text = models.TextField(
        null=True,
        blank=True,
        help_text="Text notification"
    )

    campaign = models.ForeignKey(
        "Campaign",
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="Campaign id"
    )

    importance = models.IntegerField(
        default=3,
        help_text="The lower the more important")

    rank = models.ForeignKey(
        "Rank",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text="Rank id"
    )

    target_user = models.ForeignKey(
        "CustomUser",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="User id"
    )
    sender_task = models.ForeignKey(
        "Task",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="sender_notifications"
    )
    receiver_task = models.ForeignKey(
        "Task",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="receiver_notifications"
    )

    DIRECTIONS = [
        ('', ''),
        (AutoNotificationConstants.FORWARD, 'Forward'),
        (AutoNotificationConstants.BACKWARD, 'Backward'),
        (AutoNotificationConstants.LAST_ONE, 'Last-one')
    ]
    trigger_go = models.CharField(
        max_length=2,
        choices=DIRECTIONS,
        default='',
        blank=None,
        help_text=('Trigger gone in this direction and this notification has been created.')
    )

    def open(self, user):
        notification_status, created = apps.get_model("api.notificationstatus") \
            .objects.get_or_create(
                user=user,
                notification=self)
        return notification_status, created

    def get_campaign(self):
        return self.campaign

    def __str__(self):
        return str(
            "#" + str(self.id) + ": " + self.title.__str__() + " - "
            + self.text.__str__()[:100]
        )
