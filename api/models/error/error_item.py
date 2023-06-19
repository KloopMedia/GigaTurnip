import os

from django.apps import apps
from django.db import models

from api.constans import ErrorConstants
from api.models import BaseDatesModel, CampaignInterface


class ErrorItem(BaseDatesModel, CampaignInterface):
    campaign = models.ForeignKey(
        "Campaign",
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        help_text='In which campaign exception is occur.'
    )
    group = models.ForeignKey(
        "ErrorGroup",
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        help_text='Group of the exception'
    )
    traceback_info = models.TextField(
        verbose_name='traceback',
        null=False,
        blank=False,
        help_text='Stack of functions calls.'
    )
    filename = models.CharField(
        null=True,
        blank=True,
        max_length=256,
        help_text='File where error raised.'
    )
    line = models.IntegerField(
        null=True,
        blank=True,
        help_text='Line number where error raised.'
    )
    details = models.TextField(
        null=True,
        blank=True,
        help_text='Details that may help understand error.'
    )
    data = models.TextField(
        null=True,
        blank=True,
        help_text='Data that used.'
    )

    def get_campaign(self):
        return self.campaign


    def _create_task(self, stage):
        responses = {
            "campaign": self.campaign.name,
            "campaign_id": self.campaign.id,
            "group": self.group.type_name,
            "traceback_info": self.traceback_info,
            "filename": self.filename,
            "line": self.line,
            "details": self.details,
            "data": self.data
        }
        apps.get_model("api.task").objects.create(
            case=apps.get_model("api.case").objects.create(),
            stage=stage,
            responses=responses,
        )

    @staticmethod
    def create_error_task(err_item):
        if apps.get_model("api.campaign").objects.filter(name=ErrorConstants.ERROR_CAMPAIGN).count() == 0:
            err_campaign = apps.get_model("api.campaign").objects.create(
                name=ErrorConstants.ERROR_CAMPAIGN,

            )
            default_track = apps.get_model("api.track").objects.create(campaign=err_campaign)
            default_rank = apps.get_model("api.rank").objects.create(name="error campaign rank", track=default_track)
            default_track.default_rank = default_rank
            err_campaign.default_track = default_track
            default_track.save(), err_campaign.save()
            err_chain = apps.get_model("api.chain").objects.create(name=ErrorConstants.ERROR_CHAIN, campaign=err_campaign)
            err_stage = apps.get_model("api.taskstage").objects.create(
                name="ERROR",
                x_pos=1,
                y_pos=1,
                chain=err_chain,
                is_creatable=True)
            err_item._create_task(err_stage)
        else:
            err_campaign = apps.get_model("api.campaign").objects.filter(name=ErrorConstants.ERROR_CAMPAIGN).order_by('-created_at')[0]
            err_chain = err_campaign.chains.get(name=ErrorConstants.ERROR_CHAIN)
            stage = apps.get_model("api.taskstage").objects.filter(chain=err_chain)[0]
            err_item._create_task(stage)

    @classmethod
    def create_from_data(cls, campaign, exc_type: type, details: str, tb, tb_info, data=None):
        """
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        """
        group = apps.get_model("api.errorgroup").get_group(exc_type)

        filename = None
        line = None
        if tb:
            filename = os.path.split(tb.tb_frame.f_code.co_filename)[1]
            line = tb.tb_lineno

        err_item = ErrorItem.objects.create(
            campaign=campaign,
            group=group,
            traceback_info=tb_info,
            filename=filename,
            line=line,
            details=details,
            data=data
        )
        cls.create_error_task(err_item)
