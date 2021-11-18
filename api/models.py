import datetime
from abc import ABCMeta, abstractmethod

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import UniqueConstraint
from polymorphic.models import PolymorphicModel


class BaseDatesModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        # default=datetime.datetime(2001, 1, 1),
        help_text="Time of creation"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        # default=datetime.datetime(2001, 1, 1),
        help_text="Last update time"
    )

    class Meta:
        abstract = True


class CustomUser(AbstractUser, BaseDatesModel):
    ranks = models.ManyToManyField(
        "Rank",
        through="RankRecord",
        related_name="users")

    def __str__(self):
        return self.email + " " + self.last_name


class BaseModel(BaseDatesModel):
    name = models.CharField(
        max_length=100,
        help_text="Instance name"
    )
    description = models.TextField(
        blank=True,
        help_text="Instance description"
    )

    class Meta:
        abstract = True


class SchemaProvider(models.Model):
    json_schema = models.TextField(
        null=True,
        blank=True,
        help_text="Defines the underlying data to be shown in the UI "
                  "(objects, properties, and their types)"
    )
    ui_schema = models.TextField(
        null=True,
        blank=True,
        help_text="Defines how JSON data is rendered as a form, "
                  "e.g. the order of controls, their visibility, "
                  "and the layout"
    )
    library = models.CharField(
        max_length=200,
        blank=True,
        help_text="Type of JSON form library"
    )

    class Meta:
        abstract = True


class BaseDates(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date of creation"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update date"
    )

    class Meta:
        abstract = True


class CampaignInterface:
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_campaign(self):
        pass


class Campaign(BaseModel, CampaignInterface):
    default_track = models.ForeignKey(
        "Track",
        on_delete=models.CASCADE,  # TODO Change deletion method
        blank=True,
        null=True,
        related_name="default_campaigns",
        help_text="Default track id"
    )
    managers = models.ManyToManyField(
        CustomUser,
        through="CampaignManagement",
        related_name="managed_campaigns"
    )

    open = models.BooleanField(default=False,
                               help_text="If True, users can join")

    def join(self, request):
        if request.user is not None:
            rank_record, created = RankRecord.objects.get_or_create(
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


class CampaignManagement(BaseDatesModel, CampaignInterface):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="campaign_managements"
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="campaign_managements"
    )

    class Meta:
        unique_together = ['user', 'campaign']

    def get_campaign(self) -> Campaign:
        return self.campaign


class Chain(BaseModel, CampaignInterface):
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="chains",
        help_text="Campaign id"
    )

    def get_campaign(self) -> Campaign:
        return self.campaign

    def __str__(self):
        return str("Chain: " +
                   self.name + " " +
                   self.campaign.__str__())


class Stage(PolymorphicModel, BaseModel, CampaignInterface):
    x_pos = models.DecimalField(
        max_digits=17,
        decimal_places=3,
        help_text="Starting position of 'x' coordinate "
                  "to draw on Giga Turnip Chain frontend interface"
    )
    y_pos = models.DecimalField(
        max_digits=17,
        decimal_places=3,
        help_text="Starting position of 'y' coordinate "
                  "to draw on Giga Turnip Chain frontend interface"
    )
    chain = models.ForeignKey(
        Chain,
        on_delete=models.CASCADE,
        related_name="stages",
        help_text="Chain id"
    )

    in_stages = models.ManyToManyField(
        "self",
        related_name="out_stages",
        symmetrical=False,
        blank=True,
        help_text="List of previous id stages"
    )

    def get_campaign(self) -> Campaign:
        return self.chain.campaign

    def __str__(self):
        return str("Stage: " +
                   self.name + " " +
                   self.chain.__str__())


class TaskStage(Stage, SchemaProvider):
    rich_text = models.TextField(
        null=True,
        blank=True,
        help_text="Text field with rich HTML formatting, "
                  "can be used for manuals"
    )
    copy_input = models.BooleanField(
        default=False,
        help_text=""
    )
    allow_multiple_files = models.BooleanField(
        default=False,
        help_text="Allow user to upload multiple files"
    )
    is_creatable = models.BooleanField(
        default=False,
        help_text="Allow user to create a task manually"
    )
    displayed_prev_stages = models.ManyToManyField(
        Stage,
        related_name="displayed_following_stages",
        blank=True,
        help_text="List of previous stages (tasks data) "
                  "to be shown in current stage"
    )

    RANK = 'RA'
    STAGE = 'ST'
    ASSIGN_BY_CHOICES = [
        (RANK, 'Rank'),
        (STAGE, 'Stage')
    ]
    assign_user_by = models.CharField(
        max_length=2,
        choices=ASSIGN_BY_CHOICES,
        default=RANK,
        help_text="User assignment method (by 'Stage' or by 'Rank')"
    )

    assign_user_from_stage = models.ForeignKey(
        Stage,
        on_delete=models.CASCADE,
        related_name="assign_user_to_stages",
        blank=True,
        null=True,
        help_text="Stage id. User from assign_user_from_stage "
                  "will be assigned to a task")

    webhook_address = models.URLField(
        null=True,
        blank=True,
        max_length=1000,
        help_text=(
            "Webhook URL address. If not empty, field indicates that "
            "task should be given not to a user in the system, but to a "
            "webhook. Only data from task directly preceding webhook is "
            "sent. All fields related to user assignment are ignored,"
            "if this field is not empty."
        )
    )

    webhook_payload_field = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "JSON field name to put outgoing data into. Ignored if "
            "webhook_address field is empty."
        )
    )

    webhook_params = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "Get parameters sent to webhook."
        )
    )

    webhook_response_field = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "JSON response field name to extract data from. Ignored if "
            "webhook_address field is empty."
        )
    )

    def get_integration(self):
        if hasattr(self, 'integration'):
            return self.integration
        return None


class Integration(BaseDatesModel):
    task_stage = models.OneToOneField(
        TaskStage,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="integration",
        help_text="Parent TaskStage")
    group_by = models.TextField(
        blank=True,
        help_text="Top level Task responses keys for task grouping "
                  "separated by whitespaces."
    )
    # exclusion_stage = models.ForeignKey(
    #     TaskStage,
    #     on_delete=models.SET_NULL,
    #     related_name="integration_exclusions",
    #     blank=True,
    #     null=True,
    #     help_text="Stage containing JSON form "
    #               "explaining reasons for exclusion."
    # )
    # is_exclusion_reason_required = models.BooleanField(
    #     default=False,
    #     help_text="Flag indicating that explanation "
    #               "for exclusion is mandatory."
    # )

    def get_or_create_integrator_task(self, task): # TODO Check for race condition
        integrator_group = self._get_task_fields(task.responses)
        integrator_task = Task.objects.get_or_create(
            stage=self.task_stage,
            integrator_group=integrator_group
        )
        return integrator_task

    def _get_task_fields(self, responses):
        group = {}
        groupings = self.group_by.split()
        for grouping in groupings:
            if grouping in responses:
                group[grouping] = responses[grouping]
        return group

    def __str__(self):
        return str(self.task_stage.__str__())


class ConditionalStage(Stage):
    conditions = models.JSONField(null=True,
                                  help_text="JSON logic conditions")
    pingpong = models.BooleanField(default=False,
                                   help_text="If True, makes 'in stages' "
                                             "task incomplete")

    # def __str__(self):
    #     return str("Conditional Stage Filler for " + self.stage__str__())


class Case(BaseDatesModel):

    def __str__(self):
        return str("Case #" +
                   str(self.id))


class Task(BaseDatesModel, CampaignInterface):
    assignee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,  # TODO Change deletion
        related_name="tasks",
        blank=True,
        null=True,
        help_text="User id who is responsible for the task"
    )
    stage = models.ForeignKey(
        TaskStage,
        on_delete=models.CASCADE,
        related_name="tasks",
        help_text="Stage id"
    )
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="tasks",
        blank=True,
        null=True,
        help_text="Case id"
    )
    responses = models.JSONField(
        null=True,
        blank=True,
        help_text="User generated responses "
                  "(answers)"
    )
    in_tasks = models.ManyToManyField(
        "self",
        related_name="out_tasks",
        blank=True,
        symmetrical=False,
        help_text="Preceded tasks"
    )
    integrator_group = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text="Response fields that must be shared "
                  "by all tasks being integrated."
    )
    complete = models.BooleanField(default=False)
    force_complete = models.BooleanField(default=False)

    class Meta:
        UniqueConstraint(
            fields=['integrator_group', 'stage'],
            name='unique_integrator_group')

    def get_campaign(self) -> Campaign:
        return self.stage.get_campaign()

    def get_displayed_prev_tasks(self):
        return Task.objects.filter(case=self.case) \
            .filter(stage__in=self.stage.displayed_prev_stages.all()) \
            .exclude(id=self.id)

    def __str__(self):
        return str("Task #:" + str(self.id) + self.case.__str__())

    # class Integrator(BaseDatesModel):
    #     integrator_task = models.OneToOneField(
    #         Task,
    #         primary_key=True,
    #         on_delete=models.CASCADE,
    #         related_name="integrator",
    #         help_text="Settings for integrator task, when created "
    #                   "will always create corresponding task as well.")
    #     stage = models.ForeignKey(
    #         TaskStage,
    #         on_delete=models.CASCADE,
    #         related_name="integrator_tasks",
    #         help_text="Stage id"
    #     )
    #     response_group = models.JSONField(
    #         null=True,
    #         blank=True,
    #         help_text="Response fields that must be shared "
    #                   "by all tasks being integrated."
    #     )
    #
    # class Meta:
    #     unique_together = ['integrator_task', 'response_group']


# class IntegrationStatus(BaseDatesModel):
#     integrated_task = models.ForeignKey(
#         Task,
#         on_delete=models.CASCADE,
#         related_name="integration_statuses",
#         help_text="Task being integrated")
#     integrator = models.ForeignKey(
#         Task,
#         on_delete=models.CASCADE,
#         related_name="integrated_task_statuses",
#         help_text="Integrator task"
#     )
#     is_excluded = models.BooleanField(
#         default=False,
#         help_text="Indicates that integrated task "
#                   "was excluded from integration."
#     )
#     exclusion_reason = models.TextField(
#         blank=True,
#         help_text="Explanation, why integrated task was excluded."
#     )


class Rank(BaseModel, CampaignInterface):
    stages = models.ManyToManyField(
        TaskStage,
        related_name="ranks",
        through="RankLimit",
        help_text="Stages id"
    )
    track = models.ForeignKey(
        "Track",
        related_name="ranks",
        on_delete=models.CASCADE,
        help_text="Track this rank belongs to",
        null=True,
        blank=True
    )

    def get_campaign(self):
        return self.track.campaign

    def __str__(self):
        return self.name


class Track(BaseModel, CampaignInterface):
    campaign = models.ForeignKey(
        Campaign,
        related_name="tracks",
        on_delete=models.CASCADE,
        help_text="Campaign id"
    )
    default_rank = models.ForeignKey(
        Rank,
        related_name="default_track",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Rank id"
    )

    def get_campaign(self) -> Campaign:
        return self.campaign

    def __str__(self):
        return self.name


class RankRecord(BaseDatesModel, CampaignInterface):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        help_text="User id"
    )
    rank = models.ForeignKey(
        Rank,
        on_delete=models.CASCADE,
        help_text="Rank id"
    )

    class Meta:
        unique_together = ['user', 'rank']

    def get_campaign(self):
        return self.rank.track.campaign

    def __str__(self):
        return str(self.rank.__str__() + " " + self.user.__str__())


class RankLimit(BaseDatesModel, CampaignInterface):
    rank = models.ForeignKey(
        Rank,
        on_delete=models.CASCADE,
        help_text="Rank id"
    )
    stage = models.ForeignKey(
        TaskStage,
        on_delete=models.CASCADE,
        related_name="ranklimits",
        help_text="Stage id"
    )
    open_limit = models.IntegerField(
        default=0,
        help_text="The maximum number of tasks that "
                  "can be opened at the same time for a user"
    )
    total_limit = models.IntegerField(
        default=0,
        help_text="The maximum number of tasks that user can obtain"
    )
    is_listing_allowed = models.BooleanField(
        default=False,
        help_text="Allow user to see the list of created tasks"
    )
    is_submission_open = models.BooleanField(
        default=True,
        help_text="Allow user to submit a task"
    )
    is_selection_open = models.BooleanField(
        default=True,
        help_text="Allow user to select a task"
    )
    is_creation_open = models.BooleanField(
        default=True,
        help_text="Allow user to create a task"
    )

    class Meta:
        unique_together = ['rank', 'stage']

    def get_campaign(self) -> Campaign:
        return self.stage.get_campaign()

    def __str__(self):
        return str("Rank limit: " +
                   self.rank.__str__() +
                   " " +
                   self.stage.__str__())


class Log(BaseDatesModel, CampaignInterface):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    json = models.JSONField(blank=True)
    campaign = models.ForeignKey(
        Campaign,
        related_name="logs",
        on_delete=models.CASCADE,
        help_text="Campaign related to the issue in the log"
    )
    chain = models.ForeignKey(
        Chain,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Chain related to the issue in the log"
    )
    stage = models.ForeignKey(
        Stage,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Stage related to the issue in the log"
    )
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Case related to the issue in the log"
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Task related to the issue in the log"
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="User related to the issue in the log"
    )
    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Track related to the issue in the log"
    )
    rank = models.ForeignKey(
        Rank,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Rank related to the issue in the log"
    )
    rank_limit = models.ForeignKey(
        RankLimit,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="RankLimit related to the issue in the log"
    )
    rank_record = models.ForeignKey(
        RankLimit,
        on_delete=models.CASCADE,
        related_name="rr_logs",
        blank=True,
        null=True,
        help_text="RankRecord related to the issue in the log"
    )

    def get_campaign(self) -> Campaign:
        return self.campaign


class Notification(BaseDates, CampaignInterface):
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
        Campaign,
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="Campaign id"
    )

    importance = models.IntegerField(
        default=3,
        help_text="The lower the more important")

    rank = models.ForeignKey(
        Rank,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text="Rank id"
    )

    target_user = models.ForeignKey(
        CustomUser,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text="User id"
    )

    def open(self, request):
        if request.user is not None:
            notification_status, created = NotificationStatus \
                .objects.get_or_create(
                user=request.user,
                notification=self
            )

            return notification_status, created
        else:
            return None, None

    def get_campaign(self) -> Campaign:
        return self.campaign

    def __str__(self):
        return str(
            "#" + str(self.id) + ": " + self.title.__str__() + " - "
            + self.text.__str__()[:100]
        )


class NotificationStatus(BaseDates, CampaignInterface):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        help_text="User id"
    )

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        help_text="Notification id",
        related_name="notification_statuses",
    )

    def get_campaign(self) -> Campaign:
        return self.notification.campaign

    def __str__(self):
        return str(
            "Notification id #" + self.notification.id.__str__() + ": " +
            self.notification.title.__str__() + " - "
            + self.notification.text.__str__()[:100]
        )


class AdminPreference(BaseDates):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    campaign = models.ForeignKey(
        Campaign,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    def __str__(self):
        return self.id.__str__()
