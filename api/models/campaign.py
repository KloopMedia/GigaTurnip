from abc import ABCMeta, abstractmethod

from django.db import models
from django.apps import apps

from api.models.base import BaseModel


class CampaignInterface:
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_campaign(self):
        pass

    def generate_error(self, exc_type: type, details: str = None, tb=None, tb_info=None, data=None):
        apps.get_model("api.erroritem").create_from_data(self.get_campaign(), exc_type, details, tb, tb_info, data)


class Campaign(BaseModel, CampaignInterface):
    default_track = models.ForeignKey(
        "Track",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="default_campaigns",
        help_text="Default track id"
    )
    managers = models.ManyToManyField(
        "CustomUser",
        through="CampaignManagement",
        related_name="managed_campaigns"
    )

    open = models.BooleanField(default=False,
                               help_text="If True, users can join")

    sms_login_allow = models.BooleanField(
        default=False,
        help_text='User that logged in via sms can enter in the campaign'
    )

    logo = models.TextField(
        blank=True,
        help_text="Text or url to the SVG"
    )

    descriptor = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text="Fast description to the campaign to attract new users."
    )

    countries = models.ManyToManyField(
        "Country",
        blank=True,
        default=None,
        help_text="Countries where campaign works."
    )

    categories = models.ManyToManyField(
        "Category",
        blank=True,
        default=None,
        help_text="Categories of the campaign."
    )

    language = models.ForeignKey(
        "Language",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="Language of the campaign."
    )

    def join(self, request):
        if request.user is not None:
            rank_record, created = apps.get_model(
                "api.rankrecord").objects.get_or_create(
                user=request.user,
                rank=self.default_track.default_rank
            )
            return rank_record, created
        else:
            return None, None

    def get_campaign(self):
        return self

    def __str__(self):
        return str("Campaign: " + self.name)
