from django.db import models

from api.constans import AutoNotificationConstants
from api.models import BaseDatesModel, CampaignInterface


class AutoNotification(BaseDatesModel, CampaignInterface):
    trigger_stage = models.ForeignKey(
        "TaskStage",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='auto_notification_trigger_stages',
        help_text='Stage that will be trigger notification'
    )
    recipient_stage = models.ForeignKey(
        "TaskStage",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='auto_notification_recipient_stages',
        help_text='Stage to get recipient user.'
    )
    notification = models.ForeignKey(
        "Notification",
        on_delete=models.CASCADE,
        help_text='Notification that will be using for get user'
    )

    ASSIGN_BY_CHOICES = [
        (AutoNotificationConstants.FORWARD, 'Forward'),
        (AutoNotificationConstants.BACKWARD, 'Backward'),
        (AutoNotificationConstants.LAST_ONE, 'Last-one')
    ]
    go = models.CharField(
        max_length=2,
        choices=ASSIGN_BY_CHOICES,
        default=AutoNotificationConstants.FORWARD,
        help_text=('You have to choose on what action notification would be sent.')
    )
    with_response = models.BooleanField(
        default=False,
        null=False,
        help_text="If set as true, so notification text will be sent with Response on task completion."
    )

    def create_notification(self, task, receiver_task, user):
        new_notification = self.notification
        u = user if user else receiver_task.assignee
        new_notification.pk, new_notification.target_user = None, u
        new_notification.sender_task, new_notification.receiver_task = task, receiver_task
        new_notification.trigger_go = self.go
        new_notification.save()

    def get_campaign(self):
        return self.notification.campaign
