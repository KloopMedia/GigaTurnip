import datetime
import json
from abc import ABCMeta, abstractmethod
from json import JSONDecodeError

import requests
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction, OperationalError
from django.db.models import UniqueConstraint
from django.http import HttpResponse
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
        help_text="Ranks user has",
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
        """
        The ethod returns the campaign referenced by the stage.
        :return:
        """
        pass


class Campaign(BaseModel, CampaignInterface):

    """
    join:
    get a user from request and connect him with the default rank got from default_track
    """
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
        related_name="managed_campaigns",
        help_text="All managers that can manage campaign"
    )

    open = models.BooleanField(default=False,
                               help_text="If True, users can join")

    def join(self, request):
        """
        The join method creates RankRecord with the requesting user and default rank taken from the default track.
        :param request:
        :return:
        """
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
        related_name="campaign_managements",
        help_text="The User(id) who will manage the campaign"
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="campaign_managements",
        help_text="The Campaign(id) which will be managed"
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
        return self.name


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

    def add_stage(self, stage):
        """
        The method adds a stage in the in_stages field to the self-object. Note: the argument stage must be typed
        ConditionalStage or TaskStage.
         :param stage: :return:
        """
        stage.chain = self.chain
        if not hasattr(stage, "name"):
            stage.name = "NoName"
        if not hasattr(stage, "x_pos") or stage.x_pos is None:
            stage.x_pos = 1
        if not hasattr(stage, "y_pos") or stage.y_pos is None:
            stage.y_pos = 1
        stage.save()
        stage.in_stages.add(self)
        return stage

    def __str__(self):
        return self.name


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
        help_text="Allow user to upload multiple files. Boolean type."
    )
    is_creatable = models.BooleanField(
        default=False,
        help_text="Allow user to create a task manually. Boolean type."
    )
    displayed_prev_stages = models.ManyToManyField(
        Stage,
        related_name="displayed_following_stages",
        blank=True,
        help_text="List of previous stages (tasks data) "
                  "to be shown in current stage. Array of integers."
    )

    RANK = 'RA'
    STAGE = 'ST'
    INTEGRATOR = 'IN'
    ASSIGN_BY_CHOICES = [
        (RANK, 'Rank'),
        (STAGE, 'Stage'),
        (INTEGRATOR, 'Integrator')
    ]
    assign_user_by = models.CharField(
        max_length=2,
        choices=ASSIGN_BY_CHOICES,
        default=RANK,
        help_text="User assignment method (by 'Stage' or by 'Rank')"
    )

    assign_user_from_stage = models.ForeignKey(
        Stage,
        on_delete=models.SET_NULL,
        related_name="assign_user_to_stages",
        blank=True,
        null=True,
        help_text="Stage id. User from assign_user_from_stage "
                  "will be assigned to a task")

    allow_go_back = models.BooleanField(
        default=False,
        help_text="Indicates that previous task can be opened. Boolean type."
    )

    allow_release = models.BooleanField(
        default=False,
        help_text="Indicates task can be released. Boolean type."
    )

    is_public = models.BooleanField(
        default=False,
        help_text="Indicates tasks of this stage "
                  "may be accessed by unauthenticated users. Boolean type."
    )

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
            "Get parameters sent to webhook. JSON type."
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
        """
        The method returns the integration object if the self has the integration attribute. Otherwise, it returns None
        :return:
        """
        if hasattr(self, 'integration'):
            return self.integration
        return None

    def get_webhook(self):
        """
        The method returns the webhook object if the self has the webhook attribute. Otherwise, it returns None
        :return:
        """
        if hasattr(self, 'webhook'):
            return self.webhook
        return None

    def get_quiz(self):
        """
        The method returns the quiz object if the self has the quiz attribute. Otherwise, it returns None
        :return:
        """
        if hasattr(self, 'quiz'):
            return self.quiz
        return None


class Integration(BaseDatesModel):
    task_stage = models.OneToOneField(
        TaskStage,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="integration",
        help_text="Parent TaskStage(id)")
    group_by = models.TextField(
        blank=True,
        help_text="Top level Task responses keys for task grouping "
                  "separated by whitespaces. Array of str."
    ) #Todo: The group_by field have to be ArrayOfStr field than TextField because we can face up issues so if we got not the array of str

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
        """
        Create new integration task based on dictionary of top level fields returned by _get_task_fields
        :param task:
        :return:
        """
        integrator_group = self._get_task_fields(task.responses)
        integrator_task = Task.objects.get_or_create(
            stage=self.task_stage,
            integrator_group=integrator_group
        )
        return integrator_task

    def _get_task_fields(self, responses):
        """
        Returns dictionary of fields specified in group_by field from responses. Note that the method doesn't go into
        fields, it can return only top-level fields
        :param responses:
        :return:
        """
        group = {}
        groupings = self.group_by.split()
        for grouping in groupings:
            if responses:
                if grouping in responses:
                    group[grouping] = responses[grouping]
        return group

    def __str__(self):
        return str(self.task_stage.__str__())


class Webhook(BaseDatesModel):
    task_stage = models.OneToOneField(
        TaskStage,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="webhook",
        help_text="Parent TaskStage(id)")

    url = models.URLField(
        blank=True,
        null=True,
        max_length=1000,
        help_text=(
            "Webhook URL address. If not empty, field indicates that "
            "task should be given not to a user in the system, but to a "
            "webhook. Only data from task directly preceding webhook is "
            "sent. All fields related to user assignment are ignored,"
            "if this field is not empty."
        )
    )

    headers = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Headers sent to webhook. JSON type."
        )
    )

    response_field = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "JSON response field name to extract data from. Ignored if "
            "webhook_address field is empty."
        )
    )

    def trigger(self, task):
        """
        The trigger method get all in_tasks of the task you passed and extract their responses then all in_tasks
        responses will be sent to the webhook you input in the url field.
        Note the method can return exception, based on response from webhook.
        If there wasn't any exception task will accept new responses got from webhook and update current task.
        :param task:
        :return:
        """
        data = []
        for in_task in task.in_tasks.all():
            data.append(in_task.responses)
        response = requests.post(self.url, json=data, headers=self.headers)
        if response:
            try:
                if self.response_field:
                    data = response.json()[self.response_field]
                else:
                    data = response.json()
                task.responses = data
                task.save()
                return True, task, response, ""
            except JSONDecodeError:
                return False, task, response, "JSONDecodeError"

        return False, task, response, "See response status code"


class CopyField(BaseDatesModel):
    USER = 'US'
    CASE = 'CA'
    COPY_BY_CHOICES = [
        (USER, 'User'),
        (CASE, 'Case')
    ]
    copy_by = models.CharField(
        max_length=2,
        choices=COPY_BY_CHOICES,
        default=USER,
        help_text="Where to copy fields from"
    )
    task_stage = models.ForeignKey(
        TaskStage,
        on_delete=models.CASCADE,
        related_name="copy_fields",
        help_text="Stage of the task that accepts data being copied")
    copy_from_stage = models.ForeignKey(
        TaskStage,
        on_delete=models.CASCADE,
        related_name="copycat_fields",
        help_text="Stage of the task that provides data being copied")
    fields_to_copy = models.TextField(
        help_text="List of responses field pairs to copy. \n"
                  "Format: original_field1->copy_field1  \n"
                  "Pairs are joined by arrow and separated"
                  "by whitespaces. \n"
                  "Example: phone->observer_phone uik->uik ")
    copy_all = models.BooleanField(
        default=False,
        help_text="Copy all fields and ignore fields_to_copy."
    )

    def copy_response(self, task):
        if task.reopened or \
                self.task_stage.get_campaign() != self.copy_from_stage.get_campaign():
            return task
        if self.copy_by == self.USER:
            if task.assignee is None:
                return task
            original_task = Task.objects.filter(
                assignee=task.assignee,
                stage=self.copy_from_stage,
                complete=True)
        else:
            original_task = Task.objects.filter(
                case=task.case,
                stage=self.copy_from_stage,
                complete=True)
        if original_task:
            original_task = original_task.latest("updated_at")
        else:
            return task
        if self.copy_all:
            responses = original_task.responses
        else:
            responses = task.responses
            if not isinstance(responses, dict):
                responses = {}
            for pair in self.fields_to_copy.split():
                pair = pair.split("->")
                if len(pair) == 2:
                    response = original_task.responses.get(pair[0], None)
                    if response is not None:
                        responses[pair[1]] = response
        if responses:
            task.responses = responses
        return task


class StagePublisher(BaseDatesModel, SchemaProvider):
    task_stage = models.OneToOneField(
        TaskStage,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="publisher",
        help_text="Stage(id) of the task that will be published")

    exclude_fields = models.TextField(
        blank=True,
        help_text="List of all first level fields to exclude "
                  "from publication separated by whitespaces. Array of str."
    )

    is_public = models.BooleanField(
        default=False,
        help_text="Indicates tasks of this stage "
                  "may be accessed by unauthenticated users."
    )

    def prepare_responses(self, task):
        responses = task.responses
        if isinstance(responses, dict):
            for exclude_field in self.exclude_fields.split():
                responses.pop(exclude_field, None)
        return responses


# class ResponseFlattener(BaseDatesModel):
#     task_stage = models.ForeignKey(
#         TaskStage,
#         on_delete=models.CASCADE,
#         related_name="response_flatteners",
#         help_text="Stage of the task will be flattened.")
#     copy_first_level = models.BooleanField(
#         default=True,
#         help_text="Copy all first level fields in responses "
#                   "that are not dictionaries or arrays."
#     )
#     exclude_list = models.TextField(
#         blank=True,
#         help_text="List of all first level fields to exclude "
#                   "separated by whitespaces. Dictionary and array "
#                   "fields are excluded automatically."
#     )
#     columns = models.JSONField(
#         default=list,
#         blank=True,
#         help_text="List of columns with with paths to values inside."
#     )
#
#     def flatten_response(self, task):
#         result = {}
#         if task.responses:
#             if self.copy_first_level:
#                 for key, value in task.responses.items():
#                     if key not in self.exclude_list.split() and \
#                             not isinstance(value, dict) and \
#                             not isinstance(value, list):
#                         result[key] = value
#             for column in self.columns:
#                 for path in column.path_patterns:
#                     value = self.follow_path(task.responses, path)
#                     if value:
#                         result[column.name] = value
#                         break
#         return result
#
#     def follow_path(self, responses, path):
#         if "__" not in path:
#             if not path.startswith("("):
#                 result = responses.get(path, None)
#                 if isinstance(result, dict) or isinstance(result, list):
#                     return None
#                 return result
#             elif path.startswith("("):
#                 return self.find_partial_key(responses, path)
#         paths = path.split("__", 1)[0]
#         result = responses.get(paths[0], None)
#         if isinstance(result, dict):
#             return self.follow_path(result, paths[1])
#         return None
#
#     def find_partial_key(self, responses, path):
#         for key, value in responses.items():
#             p = path.split(")", 1)[1]
#             if p in key:
#                 if not isinstance(value, dict) and not isinstance(value, list):
#                     return value
#         return None


class Quiz(BaseDatesModel):
    task_stage = models.OneToOneField(
        TaskStage,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="quiz",
        help_text="Stage(id) of the task that will be published.")
    correct_responses_task = models.OneToOneField(
        "Task",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="quiz",
        help_text="Task(id) containing correct responses to the quiz."
    )
    threshold = models.FloatField(
        blank=True,
        null=True,
        help_text="If set, task will not be closed with "
                  "quiz scores lower than this threshold."
    )

    def is_ready(self):
        """
        Returns true if correct responses are set, false - if correct responses don't set.
        :return:
        """
        return bool(self.correct_responses_task)

    def check_score(self, task):
        """
        Returns result of counting correct responses with users' answers for the current task.
        :param task:
        :return:
        """
        return self._determine_correctness_ratio(task.responses)

    def _determine_correctness_ratio(self, responses):
        """
        The _determine_correctness_ratio determines percent of correct answers of user.
        The _determine_correctness_ratio method gets as argument users' responses to compare with correct responses.
        The method returns percent of correct answers.
        :param responses:
        :return:
        """
        correct_answers = self.correct_responses_task.responses
        correct = 0
        for key, answer in correct_answers.items():
            if str(responses.get(key)) == str(answer):
                correct += 1
        len_correct_answers = len(correct_answers)
        if correct_answers.get("meta_quiz_score"):
            len_correct_answers -= 1
        correct_ratio = int(correct * 100 / len_correct_answers)
        return correct_ratio


class ConditionalStage(Stage):
    conditions = models.JSONField(null=True,
                                  help_text="JSON logic conditions. JSON type.")
    pingpong = models.BooleanField(default=False,
                                   help_text="If True, makes 'in stages' "
                                             "task incomplete. Boolean type.")

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
        help_text="User id who is responsible for the task."
    )
    stage = models.ForeignKey(
        TaskStage,
        on_delete=models.CASCADE,
        related_name="tasks",
        help_text="Stage id."
    )
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="tasks",
        blank=True,
        null=True,
        help_text="Case id."
    )
    responses = models.JSONField(
        null=True,
        blank=True,
        help_text="User generated responses "
                  "(answers). JSON type."
    )
    in_tasks = models.ManyToManyField(
        "self",
        related_name="out_tasks",
        blank=True,
        symmetrical=False,
        help_text="Preceded tasks."
    )
    integrator_group = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text="Response fields that must be shared "
                  "by all tasks being integrated. JSON type."
    )
    complete = models.BooleanField(default=False,
                                   help_text="Task sent on the check. "
                                             "If the task complete equals true you can not edit it."
                                   )
    force_complete = models.BooleanField(default=False, help_text="Shows if the task was closed by admins.")
    reopened = models.BooleanField(
        default=False,
        help_text="Indicates that task was returned to user, "
                  "usually because of pingpong stages. Boolean type.")

    class Meta:
        UniqueConstraint(
            fields=['integrator_group', 'stage'],
            name='unique_integrator_group')

    class ImpossibleToUncomplete(Exception):
        pass

    class ImpossibleToOpenPrevious(Exception):
        pass

    class AlreadyCompleted(Exception):
        pass

    class CompletionInProgress(Exception):
        pass

    def set_complete(self, responses=None, force=False, complete=True):
        """
        The set_complete method preventing race condition. Depending on transaction it can raise exception like:
        - AlreadyCompleted (if task have been completed)
        - CompletionInProgress (if task completion in progress)
        Otherwise, it will update task fields, and set complete.
        :param responses:
        :param force:
        :param complete:
        :return:
        """
        if self.complete:
            raise Task.AlreadyCompleted

        with transaction.atomic():
            try:
                task = Task.objects.select_for_update(nowait=True).get(pk=self.id)
            except OperationalError:
                raise Task.CompletionInProgress
            # task = Task.objects.select_for_update().filter(id=self.id)[0]
            # task.complete = True
            if task.complete:
                raise Task.AlreadyCompleted

            if responses:
                task.responses = responses
            if force:
                task.force_complete = True
            if complete:
                task.complete = True
            task.save()
            return task

    def set_not_complete(self):
        if self.complete:
            if self.stage.assign_user_by == "IN":
                if len(self.out_tasks.all()) == 1:
                    if not self.out_tasks.all()[0].complete:
                        self.complete = False
                        self.reopened = True
                        self.save()
                        return self
        raise Task.ImpossibleToUncomplete

    def get_direct_previous(self):
        """
        The method get_direct_previous returns the previous direct task. If there are no previous tasks it returns None.
        :return:
        """
        in_tasks = self.in_tasks.all()
        if len(in_tasks) == 1:
            if self._are_directly_connected(in_tasks[0], self):
                return in_tasks[0]
        return None

    def get_direct_next(self):
        """
        The method get_direct_next returns the next direct task. If there are no next tasks it returns None.
        :return:
        """
        out_tasks = self.out_tasks.all()
        if len(out_tasks) == 1:
            if self._are_directly_connected(self, out_tasks[0]):
                return out_tasks[0]
        return None

    def open_previous(self):
        """
        The method open_previous open previous task if these condition is true:
        - self.complete is not true;
        - self.stage.allow_go_back is true;
        - previous stage is exist;
        - prev_task assignee equals is self.assignee;
        Otherwise, the method returns Task.ImpossibleToOpenPrevious exception
        :return:
        """
        if not self.complete and self.stage.allow_go_back:
            prev_task = self.get_direct_previous()
            if prev_task:
                if prev_task.assignee == self.assignee:
                    self.complete = True
                    prev_task.complete = False
                    prev_task.reopened = True
                    self.save()
                    prev_task.save()
                    return prev_task, self
        raise Task.ImpossibleToOpenPrevious

    def get_campaign(self) -> Campaign:
        return self.stage.get_campaign()

    def get_displayed_prev_tasks(self, public=False):
        """
        Returns all previous tasks of the current task.
        :param public:
        :return:
        """
        tasks = Task.objects.filter(case=self.case) \
            .filter(stage__in=self.stage.displayed_prev_stages.all()) \
            .exclude(id=self.id)
        if public:
            tasks = tasks.filter(stage__is_public=True)
        return tasks

    def _are_directly_connected(self, task1, task2):
        """
        The method _are_directly_connected check if the tasks connected directly
        :param task1:
        :param task2:
        :return:
        """
        in_tasks = task2.in_tasks.all()
        if in_tasks and len(in_tasks) == 1 and task1 == in_tasks[0]:
            if len(task2.stage.in_stages.all()) == 1 and \
                    task2.stage.in_stages.all()[0] == task1.stage:
                if len(task1.stage.out_stages.all()) == 1:
                    if task1.out_tasks.all().count() == 1:
                        return True
        return False

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
        help_text="Stages id."
    )
    track = models.ForeignKey(
        "Track",
        related_name="ranks",
        on_delete=models.CASCADE,
        help_text="Track(id) this rank belongs to.",
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
        help_text="Campaign id."
    )
    default_rank = models.ForeignKey(
        Rank,
        related_name="default_track",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Rank id."
    )

    def get_campaign(self) -> Campaign:
        return self.campaign

    def __str__(self):
        return self.name


class RankRecord(BaseDatesModel, CampaignInterface):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        help_text="User id who will be connect to the rank."
    )
    rank = models.ForeignKey(
        Rank,
        on_delete=models.CASCADE,
        help_text="Rank id which will be connected to the user."
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
        help_text="Rank id that gets limits."
    )
    stage = models.ForeignKey(
        TaskStage,
        on_delete=models.CASCADE,
        related_name="ranklimits",
        help_text="Stage id that gets limits"
    )
    open_limit = models.IntegerField(
        default=0,
        help_text="The maximum number of tasks that "
                  "can be opened at the same time for a user. Default 0."
                  "0 - unlimited."
    )
    total_limit = models.IntegerField(
        default=0,
        help_text="The maximum number of tasks that user can obtain. Default 0."
                  "0 - unlimited."

    )
    is_listing_allowed = models.BooleanField(
        default=False,
        help_text="Allow user to see the list of created tasks. Default False"
    )
    is_submission_open = models.BooleanField(
        default=True,
        help_text="Allow user to submit a task. Default True"
    )
    is_selection_open = models.BooleanField(
        default=True,
        help_text="Allow user to select a task. Default True"
    )
    is_creation_open = models.BooleanField(
        default=True,
        help_text="Allow user to create a task. Default True"
    )

    class Meta:
        unique_together = ['rank', 'stage']

    def get_campaign(self) -> Campaign:
        return self.stage.get_campaign()

    # def __str__(self):
    #     return str("Rank limit: " +
    #                self.rank.__str__() +
    #                " " +
    #                self.stage.__str__())


class Log(BaseDatesModel, CampaignInterface):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    json = models.JSONField(blank=True)
    campaign = models.ForeignKey(
        Campaign,
        related_name="logs",
        on_delete=models.CASCADE,
        help_text="Campaign related to the issue in the log."
    )
    chain = models.ForeignKey(
        Chain,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Chain related to the issue in the log."
    )
    stage = models.ForeignKey(
        Stage,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Stage related to the issue in the log."
    )
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Case related to the issue in the log."
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Task related to the issue in the log."
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="User related to the issue in the log."
    )
    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Track related to the issue in the log."
    )
    rank = models.ForeignKey(
        Rank,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="Rank related to the issue in the log."
    )
    rank_limit = models.ForeignKey(
        RankLimit,
        on_delete=models.CASCADE,
        related_name="logs",
        blank=True,
        null=True,
        help_text="RankLimit related to the issue in the log."
    )
    rank_record = models.ForeignKey(
        RankLimit,
        on_delete=models.CASCADE,
        related_name="rr_logs",
        blank=True,
        null=True,
        help_text="RankRecord related to the issue in the log."
    )

    def get_campaign(self) -> Campaign:
        return self.campaign


class Notification(BaseDates, CampaignInterface):
    title = models.CharField(
        max_length=150,
        help_text="Instance title."
    )

    text = models.TextField(
        null=True,
        blank=True,
        help_text="Text notification."
    )

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="Campaign id."
    )

    importance = models.IntegerField(
        default=3,
        help_text="The lower the more important.")

    rank = models.ForeignKey(
        Rank,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text="Rank id."
    )

    target_user = models.ForeignKey(
        CustomUser,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text="User id."
    )

    def open(self, request):
        """
        The open method gets the user from the request and creates new notification status.
        This method implements the opening function of the notification.
        :param request:
        :return:
        """
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
        help_text="User id."
    )

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        help_text="Notification id.",
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
