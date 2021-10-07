from django.contrib.auth.models import AbstractUser
from django.db import models
from polymorphic.models import PolymorphicModel


class CustomUser(AbstractUser):
    ranks = models.ManyToManyField("Rank",
                                   through="RankRecord",
                                   related_name="users")
    def __str__(self):
        return self.email + " " + self.last_name


class BaseModel(models.Model):
    name = models.CharField(max_length=100,
                            help_text="Instance name")
    description = models.TextField(blank=True,
                                   help_text="Instance description")

    class Meta:
        abstract = True


class SchemaProvider(models.Model):
    json_schema = models.TextField(null=True,
                                   blank=True,
                                   help_text="Defines the underlying data "
                                             "to be shown in the UI (objects, "
                                             "properties, and their types)")
    ui_schema = models.TextField(null=True,
                                 blank=True,
                                 help_text="Defines how JSON data is rendered "
                                           "as a form, e.g. the order of "
                                           "controls, their visibility, "
                                           "and the layout")
    library = models.CharField(max_length=200,
                               blank=True,
                               help_text="Type of JSON form library")

    class Meta:
        abstract = True


class Campaign(BaseModel):
    default_track = models.ForeignKey("Track",
                                      on_delete=models.CASCADE,  # TODO Change deletion metgod
                                      blank=True,
                                      null=True,
                                      related_name="default_campaigns",
                                      help_text="Default track id"
                                      )
    managers = models.ManyToManyField(CustomUser,
                                      through="CampaignManagement",
                                      related_name="managed_campaigns")

    def __str__(self):
        return str("Campaign: " + self.name)


class CampaignManagement(models.Model):
    user = models.ForeignKey(CustomUser,
                             on_delete=models.CASCADE,
                             related_name="campaign_managements")
    campaign = models.ForeignKey(Campaign,
                                 on_delete=models.CASCADE,
                                 related_name="campaign_managements")

    class Meta:
        unique_together = ['user', 'campaign']



class Chain(BaseModel):
    campaign = models.ForeignKey(Campaign,
                                 on_delete=models.CASCADE,
                                 related_name="chains",
                                 help_text="Campaign id")

    def __str__(self):
        return str("Chain: " +
                   self.name + " " +
                   self.campaign.__str__())


class Stage(PolymorphicModel, BaseModel):
    x_pos = models.DecimalField(max_digits=17,
                                decimal_places=14,
                                help_text="Starting position of 'x' "
                                          "coordinate to draw on Giga Turnip "
                                          "Chain frontend interface")
    y_pos = models.DecimalField(max_digits=17,
                                decimal_places=14,
                                help_text="Starting position of 'y' "
                                          "coordinate to draw on Giga Turnip "
                                          "Chain frontend interface")
    chain = models.ForeignKey(Chain,
                              on_delete=models.CASCADE,
                              related_name="stages",
                              help_text="Chain id")

    in_stages = models.ManyToManyField("self",
                                       related_name="out_stages",
                                       symmetrical=False,
                                       blank=True,
                                       help_text="List of previous id stages")

    def __str__(self):
        return str("Stage: " +
                   self.name + " " +
                   self.chain.__str__())


class TaskStage(Stage, SchemaProvider):
    rich_text = models.TextField(null=True,
                                 blank=True,
                                 help_text="Text field with rich HTML "
                                           "formatting, can be used "
                                           "for manuals")
    copy_input = models.BooleanField(default=False, help_text="")
    allow_multiple_files = models.BooleanField(default=False,
                                               help_text="Allow user to upload"
                                                         " multiple files")
    is_creatable = models.BooleanField(default=False,
                                       help_text="Allow user to create a task"
                                                 " manually")
    displayed_prev_stages = models.ManyToManyField(Stage,
                                                   related_name="displayed_following_stages",
                                                   blank=True,
                                                   help_text="List of previous"
                                                             " stages (tasks "
                                                             "data) to be shown"
                                                             " in current stage")

    RANK = 'RA'
    STAGE = 'ST'
    ASSIGN_BY_CHOICES = [
        (RANK, 'Rank'),
        (STAGE, 'Stage')
    ]
    assign_user_by = models.CharField(max_length=2,
                                      choices=ASSIGN_BY_CHOICES,
                                      default=RANK,
                                      help_text="User assignment method "
                                                "(by 'Stage' or by 'Rank')")

    assign_user_from_stage = models.ForeignKey(Stage,
                                               on_delete=models.CASCADE,
                                               related_name="assign_user_to_stages",
                                               blank=True,
                                               null=True,
                                               help_text="Stage id. User from"
                                                         " assign_user_from_stage "
                                                         "will be assigned "
                                                         "to a task")

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


# class WebHookStage(Stage, SchemaProvider):
#
#     web_hook_address = models.TextField()
#
#     def __str__(self):
#         return str("Web Hook Stage Filler for " + self.stage.__str__())


class ConditionalStage(Stage):
    conditions = models.JSONField(null=True,
                                  help_text="JSON logic conditions")
    pingpong = models.BooleanField(default=False,
                                   help_text="If True, makes 'in stages' "
                                             "task incomplete")

    # def __str__(self):
    #     return str("Conditional Stage Filler for " + self.stage__str__())


class Case(models.Model):

    def __str__(self):
        return str("Case #" +
                   str(self.id))


class Task(models.Model):
    assignee = models.ForeignKey(CustomUser,
                                 on_delete=models.CASCADE, # TODO Change deletion
                                 related_name="tasks",
                                 blank=True,
                                 null=True,
                                 help_text="User id who is responsible "
                                           "for the task")
    stage = models.ForeignKey(TaskStage,
                              on_delete=models.CASCADE,
                              related_name="tasks",
                              help_text="Stage id")
    case = models.ForeignKey(Case,
                             on_delete=models.CASCADE,
                             related_name="tasks",
                             blank=True,
                             null=True,
                             help_text="Case id")
    responses = models.JSONField(null=True,
                                 blank=True,
                                 help_text="User generated responses "
                                           "(answers)")
    in_tasks = models.ManyToManyField("self",
                                      related_name="out_tasks",
                                      blank=True,
                                      symmetrical=False,
                                      help_text="Preceded tasks")
    complete = models.BooleanField(default=False)

    def __str__(self):
        return str("Task #:" + str(self.id) + self.case.__str__())


class Rank(BaseModel):
    stages = models.ManyToManyField(TaskStage,
                                    related_name="ranks",
                                    through="RankLimit",
                                    help_text="Stages id")
    def __str__(self):
        return self.name


class Track(BaseModel):
    campaign = models.ForeignKey(Campaign,
                                 related_name="tracks",
                                 on_delete=models.CASCADE,
                                 help_text="Campaign id")
    ranks = models.ManyToManyField(Rank,
                                   related_name="ranks",
                                   help_text="Ranks id")
    default_rank = models.ForeignKey(Rank,
                                     on_delete=models.CASCADE,
                                     blank=True,
                                     null=True,
                                     help_text="Rank id")


class RankRecord(models.Model):
    user = models.ForeignKey(CustomUser,
                             on_delete=models.CASCADE,
                             help_text="User id")
    rank = models.ForeignKey(Rank,
                             on_delete=models.CASCADE,
                             help_text="Rank id")

    class Meta:
        unique_together = ['user', 'rank']

    def __str__(self):
        return str(self.rank.__str__() + " " + self.user.__str__())


class RankLimit(models.Model):
    rank = models.ForeignKey(Rank,
                             on_delete=models.CASCADE,
                             help_text="Rank id")
    stage = models.ForeignKey(TaskStage,
                              on_delete=models.CASCADE,
                              related_name="ranklimits",
                              help_text="Stage id")
    open_limit = models.IntegerField(default=0,
                                     help_text="The maximum number of tasks "
                                               "that can be opened at the same"
                                               " time for a user")
    total_limit = models.IntegerField(default=0,
                                      help_text="The maximum number of tasks "
                                                "that user can obtain")
    is_listing_allowed = models.BooleanField(default=False,
                                             help_text="Allow user to see "
                                                       "the list of created "
                                                       "tasks")
    is_submission_open = models.BooleanField(default=True,
                                             help_text="Allow user to submit "
                                                       "a task")
    is_selection_open = models.BooleanField(default=True,
                                            help_text="Allow user to select"
                                                      " a task")
    is_creation_open = models.BooleanField(default=True,
                                           help_text="Allow user to create"
                                                     " a task")

    class Meta:
        unique_together = ['rank', 'stage']

    def __str__(self):
        return str("Rank limit: " +
                   self.rank.__str__() +
                   " " +
                   self.stage.__str__())
