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
    visible = models.BooleanField(default=False, help_text="If true - campaigns is visible in the all endpoints. "
                                                           "Otherwise it invisible but users can join it."
    )

    sms_login_allow = models.BooleanField(
        default=False,
        help_text='User that logged in via sms can enter in the campaign'
    )

    logo = models.TextField(
        blank=True,
        help_text="Text or url to the SVG"
    )

    short_description = models.CharField(
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

    sms_phone = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Phone of the campaign to send sms."
    )

    sms_complete_task_allow = models.BooleanField(
        default=False,
        null=True,
        help_text="If the campaign allows users to send tasks via sms."
    )

    languages = models.ManyToManyField(
        "Language",
        related_name="campaigns",
        blank=True,
        null=True,
        help_text="Language of the campaign."
    )

    featured = models.BooleanField(default=False, help_text="featured")

    featured_image = models.TextField(
        blank=True,
        help_text="Text or url to the SVG"
    )

    new_task_view_mode = models.BooleanField(
        default=False,
        help_text="Use new task view mode"
    )
    contact_us_link = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Link to 'Contact Us' button"
    )

    start_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date when the course will start"
    )

    course_completetion_rank = models.ForeignKey(
        "Rank",
        blank=True,
        null=True,
        help_text="Check if user has the rank, to determine course completion",
        on_delete=models.SET_NULL,
    )

    def is_course_completed(self, request):
        """
        Check if the user has completed the course by verifying the existence
        of a rank record for the user with the specified rank.
        """
        user = request.user
        if user and not user.is_anonymous:
            RankRecord = apps.get_model("api", "RankRecord")
            return RankRecord.objects.filter(
                user=user,
                rank=self.course_completetion_rank
            ).exists()
        return False

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
