from django.db import models

from api.models import BaseDatesModel, CampaignInterface


class NotificationStatus(BaseDatesModel, CampaignInterface):
    user = models.ForeignKey(
        "CustomUser",
        on_delete=models.CASCADE,
        help_text="User id"
    )

    notification = models.ForeignKey(
        "Notification",
        on_delete=models.CASCADE,
        help_text="Notification id",
        related_name="notification_statuses",
    )

    def get_campaign(self):
        return self.notification.campaign

    def __str__(self):
        return str(
            "Notification id #" + self.notification.id.__str__() + ": " +
            self.notification.title.__str__() + " - "
            + self.notification.text.__str__()[:100]
        )
