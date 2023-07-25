import random
import string

from django.apps import apps
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.db.models import Subquery, OuterRef

from api.models.base import BaseDatesModel


class CustomUser(AbstractUser, BaseDatesModel):
    ranks = models.ManyToManyField(
        "Rank",
        through="RankRecord",
        related_name="users")
    login_via_sms = models.BooleanField(
        default=False,
        help_text="User is login via sms"
    )
    phone_number = models.CharField(
        max_length=250,
        blank=True,
        help_text='Users phone number'
    )
    sms_relay = models.BooleanField(
        default=False,
        help_text="Is user sms relay."
    )
    deleted = models.BooleanField(
        default=False,
        help_text="Is user deleted."
    )

    def __str__(self):
        if self.login_via_sms:
            return self.phone_number
        return self.email + " " + self.last_name

    # actually it took all privileges from user like deletion
    def rename(self):
        with transaction.atomic():
            first_part = ''.join(
                random.choice(string.ascii_letters + string.digits)
                for _ in range(140))

            self.username = first_part
            self.email = first_part + 'email.com'
            self.deleted = False
            self.save()
            return True
        return False

    def get_admin_preference(self):
        if hasattr(self, 'admin_preference'):
            return self.admin_preference
        return None

    def get_highest_ranks_by_track(self):
        highest_ranks = self.ranks.values("track").annotate(
            max_rank_id=Subquery(
                apps.get_model("api.rank").objects.filter(track=OuterRef("track")).order_by(
                    "-priority").values("id")[:1])
        ).distinct().values("max_rank_id")

        return highest_ranks

class UserDelete(BaseDatesModel):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        help_text='Reference to the user.'
    )

    class Meta:
        ordering = ['-created_at']

