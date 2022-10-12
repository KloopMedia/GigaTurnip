import datetime
import json
import re
from abc import ABCMeta, abstractmethod, ABC
from json import JSONDecodeError

import requests
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator
from django.db import models, transaction, OperationalError
from django.db.models import UniqueConstraint
from django.http import HttpResponse
from polymorphic.models import PolymorphicModel
from jsonschema import validate
from api.constans import TaskStageConstants, CopyFieldConstants, AutoNotificationConstants


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

    login_via_sms = models.BooleanField(
        default=False,
        help_text="User is login via sms"
    )

    phone_number = models.CharField(
        max_length=250,
        blank=True,
        help_text='Users phone number'
    )

    def __str__(self):
        if self.login_via_sms:
            return self.phone_number
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
        on_delete=models.SET_NULL,
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

    sms_login_allow = models.BooleanField(
        default=False,
        help_text='User that logged in via sms can enter in the campaign'
    )

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

    def __str__(self):
        return f"{self.campaign.name} - {self.user}"


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
        return f"ID: {self.id}; {self.name}"


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
    external_metadata = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "To show slides."
        )
    )

    ASSIGN_BY_CHOICES = [
        (TaskStageConstants.RANK, 'Rank'),
        (TaskStageConstants.STAGE, 'Stage'),
        (TaskStageConstants.AUTO_COMPLETE, 'Auto-complete'),
        (TaskStageConstants.PREVIOUS_MANUAL, 'Previous manual')
    ]
    assign_user_by = models.CharField(
        max_length=2,
        choices=ASSIGN_BY_CHOICES,
        default=TaskStageConstants.RANK,
        help_text='User assignment method.\n'
                  'Rank means that all task assignments will be based on ranks. If the user has this rank.\n'
                  'Stage means that created task will be assign automatically based on assign_user_from_stage. '
                  'So you must pass assign_user_from_stage if you choose assign_user_by.\n'
                  'Auto-complete means that this task will complete automatically without any condition.\n'
                  'Previous manual means that task will assign manually by user. '
                  'For this feature You must create new instance in '
                  'Previous Manual model and pass this stage in field task_stage_to_assign.',
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
        help_text="Indicates that previous task can be opened."
    )

    allow_release = models.BooleanField(
        default=False,
        help_text="Indicates task can be released."
    )

    is_public = models.BooleanField(
        default=False,
        help_text="Indicates tasks of this stage "
                  "may be accessed by unauthenticated users."
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
    card_json_schema = models.TextField(
        null=True,
        blank=True,
        help_text=""  # todo: add help text for card json schema
    )
    card_ui_schema = models.TextField(
        null=True,
        blank=True,
        help_text=""  # todo: add help text for card ui schema
    )

    def get_integration(self):
        if hasattr(self, 'integration'):
            return self.integration
        return None

    def get_previous_manual_to_assign(self):
        if hasattr(self, 'previous_manual_to_assign'):
            return self.previous_manual_to_assign
        return None

    def get_webhook(self):
        if hasattr(self, 'webhook'):
            return self.webhook
        return None

    def get_quiz(self):
        if hasattr(self, 'quiz'):
            return self.quiz
        return None

    def get_columns_from_js_schema(self):
        ordered = {}
        ui = json.loads(self.get_ui_schema())
        schema = json.loads(self.get_json_schema())
        for i, section_name in enumerate(ui.get("ui:order")):
            property = schema['properties'].get(section_name)
            if property:
                root_dependencies = schema.get('dependencies')
                if root_dependencies is not None and section_name in list(root_dependencies.keys()):
                    section_dependencies = root_dependencies.get(section_name)
                else:
                    section_dependencies = None
                js = self.__get_all_columns_and_priority(property, section_dependencies,
                                                         section_name, ordered,
                                                         extra_dependencies=root_dependencies)
                ordered.update(js)
        return ordered

    def __get_all_columns_and_priority(self, properties, dependencies, key, js, extra_dependencies={}):
        last_key = key.split("__")[-1]

        ui = json.loads(self.ui_schema)
        if last_key in ui.get("ui:order"):
            priority = ui.get("ui:order").index(last_key) + 1
        else:
            priority = -1
        js[last_key] = {"priority": priority}

        if dependencies and dependencies.get("oneOf"):
            for i in dependencies.get("oneOf"):
                js = self.__parse_dependencies(key, i, extra_dependencies, js)
        elif dependencies:
            js = self.__parse_dependencies(key, dependencies, extra_dependencies, js)
        if properties:
            sup_props = properties.get("properties")
            if sup_props:
                for k, v in sup_props.items():
                    all_dependencies = properties.get("dependencies")
                    if all_dependencies and all_dependencies.get(k):
                        current_deps = all_dependencies.get(k)
                    else:
                        current_deps = None
                    d = self.__get_all_columns_and_priority(v, current_deps, f"{key}__{k}", js[last_key],
                                                            extra_dependencies=all_dependencies)
                    js[last_key].update(d)

        return js

    def __parse_dependencies(self, key, dependency, extra_dependencies, js):
        last_key = key.split("__")[-1]
        sub_columns = dependency.get("properties")
        if last_key in sub_columns.keys():
            del sub_columns[last_key]
        for k, v in sub_columns.items():
            d = self.__get_all_columns_and_priority(v, extra_dependencies.get(k), f"{key}__{k}", js)
            js.update(d)
            if v.get("properties"):
                for sub_k, sub_v in v.get("properties").items():
                    c = self.__get_all_columns_and_priority(sub_v, v.get("dependencies").get(sub_k),
                                                            f"{key}__{k}__{sub_k}", {})
                    for j in c[sub_k].items():
                        if j[0] != 'priority':
                            js[last_key][k][j[0]] = j[1]

        return js


    def parse_section(self, key, section, array):
        if isinstance(section, dict) and len(section.keys()) > 1:
            self.parse(section, key, array)
        else:
            return key

    def parse(self, to_parse, key, array):
        for k, v in to_parse.items():
            path = F"{key}__{k}"
            if isinstance(v, dict):
                path = f'{v.get("priority")}.{path}'
            x = self.parse_section(path, v, array)
            if x is not None:
                array.append(x)

    def order_columns(self, path, key, arr):
        if len(path) > 1:
            while len(arr) < int(path[0]):
                arr.append([])
            i = int(path[0])
            if i == -1:
                arr = self.order_columns(path[1:], key, arr)
            else:
                arr[i - 1] = self.order_columns(path[1:], key, arr[i - 1])
            return arr
        else:
            if isinstance(arr, str):
                arr = [arr]
            position = int(path[0])
            if position != -1:
                while len(arr) < position:
                    arr.append([])
                arr[position - 1] = key
            else:
                arr.append(key)
            return arr

    def make_columns_ordered(self):
        prioritized_js = self.get_columns_from_js_schema()

        all_columns = []
        self.parse(prioritized_js, '', all_columns)

        pre_order_columns = []
        for i in all_columns:
            if i is not None and i.split("__")[-1] != 'priority':
                prioritet = i.split("__")[0].split('.')[:-1]
                prioritet.reverse()
                pre_order_columns = self.order_columns(prioritet, i, pre_order_columns)

        ordered_columns = []
        self.make_1d_arr(pre_order_columns, ordered_columns)

        return ordered_columns

    def make_1d_arr(self, arr, end_arr):
        for i in arr:
            if isinstance(i, list) or isinstance(i, tuple):
                self.make_1d_arr(i, end_arr)
            else:
                end_arr.append(i)

    def get_json_schema(self):
        if not self.json_schema:
            return '{}'
        return self.json_schema

    def get_ui_schema(self):
        if not self.ui_schema:
            return '{}'
        return self.ui_schema


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

    def get_or_create_integrator_task(self, task):  # TODO Check for race condition
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
        help_text="Parent TaskStage")

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
            "Headers sent to webhook."
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

    is_triggered = models.BooleanField(
        blank=False,
        default=True,
        help_text="Sometimes there are cases when a webhook is used by a non-taskstage "
                  "and then we need to mark it accordingly"
    )

    def trigger(self, task):
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

    def post(self, data):
        response = requests.post(self.url, json=data, headers=self.headers)
        return response


class CopyField(BaseDatesModel):
    COPY_BY_CHOICES = [
        (CopyFieldConstants.USER, 'User'),
        (CopyFieldConstants.CASE, 'Case')
    ]
    copy_by = models.CharField(
        max_length=2,
        choices=COPY_BY_CHOICES,
        default=CopyFieldConstants.USER,
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
        if self.task_stage.get_campaign() != self.copy_from_stage.get_campaign():
            return task.responses
        if self.copy_by == CopyFieldConstants.USER:
            if task.assignee is None:
                return task.responses
            original_task = Task.objects.filter(
                assignee=task.assignee,
                stage=self.copy_from_stage,
                complete=True)
        else:
            original_task = task.case.tasks.filter(
                complete=True,
                stage=self.copy_from_stage
            )
        if original_task:
            original_task = original_task.latest("updated_at")
        else:
            return task.responses
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
        return responses


class StagePublisher(BaseDatesModel, SchemaProvider):
    task_stage = models.OneToOneField(
        TaskStage,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="publisher",
        help_text="Stage of the task that will be published")

    exclude_fields = models.TextField(
        blank=True,
        help_text="List of all first level fields to exclude "
                  "from publication separated by whitespaces."
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


class ResponseFlattener(BaseDatesModel, CampaignInterface):
    task_stage = models.OneToOneField(
        TaskStage,
        on_delete=models.CASCADE,
        related_name="response_flatteners",
        help_text="Stage of the task will be flattened.")
    copy_first_level = models.BooleanField(
        default=True,
        help_text="Copy all first level fields in responses "
                  "that are not dictionaries or arrays."
    )
    flatten_all = models.BooleanField(
        default=False,
        help_text="Copy all response fields even they deeper than "
                  "first level."
    )
    copy_system_fields = models.BooleanField(
        default=False,
        help_text="Copy all system fields fields in tasks."
    )
    exclude_list = models.JSONField(
        default=list,
        blank=True,
        help_text="List of all first level fields to exclude "
                  "separated by whitespaces. Dictionary and array "
                  "fields are excluded automatically."
    )
    columns = models.JSONField(
        default=list,
        blank=True,
        help_text='List of columns with with paths to values inside. '
                  'Also you can use: i - if you you want to find keys that have same word in key; r - if you want use '
                  'regular expressions. '
                  'For example: ["title", "oik__(i)uik", "oik__(r)question[\d]{1,2}"]'
    )

    def flatten_response(self, task):
        result = {"id": task.id}
        ui = json.loads(self.task_stage.get_ui_schema())
        if task.responses and not self.flatten_all:
            if self.copy_first_level:
                for key, value in task.responses.items():
                    if key not in self.exclude_list and \
                            not isinstance(value, dict) and \
                            not isinstance(value, list):
                        result[key] = value
            for path in list(self.columns):
                value = self.follow_path(task.responses, path, ui)
                if value:
                    result[path] = value
        elif self.flatten_all and task.responses:
            result = self.flatten_all_response(task, result, ui)
        if self.copy_system_fields:
            result.update(task.__dict__)
            list_of_unnecessary_keys = ['_state', 'responses']
            for unnecessary_key in list_of_unnecessary_keys:
                del result[unnecessary_key]

        return result

    def flatten_all_response(self, task, result, ui):
        all_keyses = []
        for key, value in task.responses.items():
            all_keyses += self.get_all_pathes(key, value)

        for path in all_keyses:
            value = self.follow_path(task.responses, path, ui)
            if value:
                result[path] = value
        return result

    def get_all_pathes(self, k, value):
        keys = []
        if isinstance(value, dict):
            for key, values in value.items():
                keys += self.get_all_pathes(k + "__" + key, values)
        # elif isinstance(value, list):
        # for i, item in value:
        #     keys += self.get_all_pathes(k + f"__" + i, item)
        elif isinstance(value, str) or isinstance(value, int) or isinstance(value, list):
            keys.append(k)

        return keys

    def is_list_of_ints(self, arr):
        res = []
        for i in arr:
            if isinstance(i, int):
                res.append(True)
        return len(res) == len(arr)

    def is_list_of_strings(self, arr):
        res = []
        for i in arr:
            if isinstance(i, str):
                res.append(True)
        return len(res) == len(arr)

    def __str__(self):
        return f"ID: {self.id}; TaskStage ID: {self.task_stage.id}"

    def follow_path(self, responses, path, ui=None):
        paths = path.split("__", 1)
        current_key = paths[0]
        next_key = paths[1] if len(paths) > 1 else None
        current_ui = ui.get(current_key) if ui else None

        if "(i)" in current_key or "(r)" in current_key:
            if not path.startswith("("):
                result = responses.get(path, None)
                if isinstance(result, dict) or isinstance(result, list):
                    return None
                return result
            elif path.startswith("("):
                return self.find_partial_key(responses, path)
        result = responses.get(current_key, None)
        if isinstance(result, dict):
            return self.follow_path(result, next_key, current_ui)
        elif not isinstance(result, dict):
            if current_ui and current_ui.get("ui:widget") == 'customfile':
                try:
                    file_path = json.loads(result)
                    files = []
                    for key, val in file_path.items():
                        result = "https://storage.cloud.google.com/gigaturnip-b6b5b.appspot.com/" + val + '?authuser=1'
                        files.append(result)
                    result = ", \n".join(files)
                except:
                    result = "CAN'T_PARSE_JSON_ERROR"+result
            return result
        return None

    def find_partial_key(self, responses, path):
        for key, value in responses.items():
            search_type = path[path.find("(") + 1: path.find(")")]
            keys = path.split(")", 1)[1].split("__", 1)
            key_to_find = keys[0]

            condition = False
            if search_type == 'i':
                condition = key_to_find in key and key_to_find != key
            elif search_type == 'r':
                condition = re.findall(rf"{key_to_find}", key)

            if condition:
                if not isinstance(value, dict) and not isinstance(value, list):
                    return value
                else:
                    return self.follow_path(value, keys[1])

        return None

    def ordered_columns(self):
        ordered_columns = self.task_stage.make_columns_ordered()

        system_columns = []
        if self.copy_system_fields:
            system_columns = list(Task().__dict__.keys())
            list_of_unnecessary_keys = ['id', '_state', 'responses']
            for i in list_of_unnecessary_keys:
                system_columns.remove(i)

        finally_columns = ['id'] + system_columns + [i.split("__", 1)[1] for i in ordered_columns]
        for i, col in enumerate(self.columns):
            position = i + 1 + len(system_columns)
            finally_columns.insert(position, col)
        return finally_columns

    def get_campaign(self) -> Campaign:
        return self.task_stage.get_campaign()


class Quiz(BaseDatesModel):
    task_stage = models.OneToOneField(
        TaskStage,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="quiz",
        help_text="Stage of the task that will be published")
    correct_responses_task = models.OneToOneField(
        "Task",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="quiz",
        help_text="Task containing correct responses to the quiz"
    )
    threshold = models.FloatField(
        blank=True,
        null=True,
        help_text="If set, task will not be closed with "
                  "quiz scores lower than this threshold"
    )

    def is_ready(self):
        return bool(self.correct_responses_task)

    def check_score(self, task):
        return self._determine_correctness_ratio(task.responses)

    def _determine_correctness_ratio(self, responses):
        correct_answers = self.correct_responses_task.responses
        correct = 0
        questions = eval(self.task_stage.json_schema).get('properties')
        incorrect_questions = []
        for key, answer in correct_answers.items():
            if str(responses.get(key)) == str(answer):
                correct += 1
            else:
                incorrect_questions.append(questions.get(key).get('title'))

        len_correct_answers = len(correct_answers)
        unnecessary_keys = ["meta_quiz_score", "meta_quiz_incorrect_questions"]
        for k in unnecessary_keys:
            if correct_answers.get(k):
                len_correct_answers -= 1

        correct_ratio = int(correct * 100 / len_correct_answers)
        return correct_ratio, "\n".join(incorrect_questions)


class ConditionalStage(Stage):
    conditions = models.JSONField(
        null=True,
        help_text='JSON logic conditions'
    )
    pingpong = models.BooleanField(
        default=False,
        help_text='If True, makes \'in stages\' task incomplete'
    )

    # def __str__(self):
    #     return str("Conditional Stage Filler for " + self.stage__str__())


class ConditionalLimit(BaseDatesModel, CampaignInterface):
    conditional_stage = models.OneToOneField(
        ConditionalStage,
        related_name='conditional_limit',
        on_delete=models.CASCADE,
        help_text='Allow to compare taskstage data in ConditionalStage'
    )
    order = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(1000000)]
    )
    def get_campaign(self) -> Campaign:
        return self.conditional_stage.get_campaign()


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
    reopened = models.BooleanField(
        default=False,
        help_text="Indicates that task was returned to user, "
                  "usually because of pingpong stages.")
    internal_metadata = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text='The field for internal data that wouldn\'t be shown to the user.'
    )

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
        in_tasks = self.in_tasks.all()
        if len(in_tasks) == 1:
            if self._are_directly_connected(in_tasks[0], self):
                return in_tasks[0]
        return None

    def get_next_demo(self): # todo: have to refactor
        tasks = self.out_tasks.filter(assignee=self.assignee)
        if tasks.count() == 1:
            return tasks[0]
        return None

    def get_direct_next(self):
        out_tasks = self.out_tasks.all()
        if len(out_tasks) == 1:
            if self._are_directly_connected(self, out_tasks[0]):
                return out_tasks[0]
        return None

    def open_previous(self):
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
        tasks = Task.objects.filter(case=self.case) \
            .filter(stage__in=self.stage.displayed_prev_stages.all()) \
            .exclude(id=self.id)
        if public:
            tasks = tasks.filter(stage__is_public=True)
        return tasks

    def _are_directly_connected(self, task1, task2):
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
    prerequisite_ranks = models.ManyToManyField(
        "self",
        related_name="postrequisite_ranks",
        blank=True,
        symmetrical=False,
        help_text="Preceded tasks"
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
        related_name='user_ranks',
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

    # def __str__(self):
    #     return str("Rank limit: " +
    #                self.rank.__str__() +
    #                " " +
    #                self.stage.__str__())


class TaskAward(BaseDatesModel, CampaignInterface):
    task_stage_completion = models.ForeignKey(
        TaskStage,
        on_delete=models.CASCADE,
        related_name="task_stage_completion",
        help_text="Task Stage completion. Usually, it is the stage that the user completes.")
    task_stage_verified = models.ForeignKey(
        TaskStage,
        on_delete=models.CASCADE,
        related_name="task_stage_verified",
        help_text="Task Stage verified. It is the stage that is checked by the verifier.")
    rank = models.ForeignKey(
        Rank,
        on_delete=models.CASCADE,
        help_text="Rank to create the record with a user. It is a rank that will be given user, as an award who "
                  "have completed a defined count of tasks")
    stop_chain = models.BooleanField(
        default=False,
        help_text='When rank will obtained by user chain will stop.'
    )
    count = models.PositiveIntegerField(help_text="The count of completed tasks to give an award.")
    notification = models.ForeignKey(
        'Notification',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Notification which will be sent on achieving new rank.'
    )

    def get_campaign(self) -> Campaign:
        return self.task_stage_completion.chain.campaign

    def connect_user_with_rank(self, task):
        """
        The method gives an award to the user if the user completed a defined count of tasks.
        In the beginning, we find all his tasks by cases and get all that haven't been force completed by the verifier.
        If the count is equal - we will create RankRecord with prize rank with the user.
        :param task:
        :return:
        """
        # Get user from task which stage is stage of completion
        user = task.case.tasks.filter(
            complete=True,
            force_complete=False,
            stage=self.task_stage_completion).last().assignee

        # Get tasks which was completed by user to get cases id
        cases_of_tasks = user.tasks.filter(
            stage=self.task_stage_completion,
            complete=True,
            force_complete=False).values_list('case', flat=True)

        # Get all tasks with our needing cases
        verified = Task.objects.filter(
            case__in=cases_of_tasks)\
            .filter(
                stage=self.task_stage_verified, force_complete=False)

        # if count is equal -> create notification and give rank
        if verified.count() == self.count:
            rank_record = user.user_ranks.filter(rank=self.rank)
            if rank_record:
                return rank_record[0]
            rank_record = RankRecord.objects.create(user=user, rank=self.rank)
            new_notification = self.notification
            new_notification.pk, new_notification.target_user = None, user
            new_notification.save()

            return rank_record
        else:
            return None

    def __str__(self):
        return f"Completion: {self.task_stage_completion.id} " \
               f"Verified: {self.task_stage_verified.id} " \
               f"Rank: {self.rank.id}"


class PreviousManual(BaseDatesModel):
    field = ArrayField(
        models.CharField(max_length=250),
        blank=False,
        null=False,
        help_text='User have to enter path to the field where places users email to assign new task'
    )
    is_id = models.BooleanField(
        default=False,
        help_text='If True, user have to enter id. Otherwise, user have to enter email'
    )
    task_stage_to_assign = models.OneToOneField(
        TaskStage,
        related_name='previous_manual_to_assign',
        on_delete=models.CASCADE,
        help_text='This task will assign to the user. '
                  'Also, you have to set assign_user_by as PM in this TaskStage to use manual assignment.'
    )
    task_stage_email = models.OneToOneField(
        TaskStage,
        on_delete=models.CASCADE,
        help_text='Task stage to get email from responses to assign task'
    )

    def __str__(self):
        return f'ID {self.id}; {self.field[-1]}'


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
        related_name='notifications',
        help_text="User id"
    )
    sender_task = models.ForeignKey(
        Task,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="sender_notifications"
    )
    receiver_task = models.ForeignKey(
        Task,
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
        notification_status, created = NotificationStatus \
            .objects.get_or_create(
                user=user,
                notification=self)
        return notification_status, created

    def get_campaign(self) -> Campaign:
        return self.campaign

    def __str__(self):
        return str(
            "#" + str(self.id) + ": " + self.title.__str__() + " - "
            + self.text.__str__()[:100]
        )


class AutoNotification(BaseDates):
    trigger_stage = models.ForeignKey(
        TaskStage,
        on_delete=models.CASCADE,
        related_name='auto_notification_trigger_stages',
        help_text='Stage that will be trigger notification'
    )
    recipient_stage = models.ForeignKey(
        TaskStage,
        on_delete=models.CASCADE,
        related_name='auto_notification_recipient_stages',
        help_text='Stage to get recipient user.'
    )
    notification = models.ForeignKey(
        Notification,
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

    def create_notification(self, task: Task, receiver_task: Task, user: CustomUser=None):
        new_notification = self.notification
        u = user if user else receiver_task.assignee
        new_notification.pk, new_notification.target_user = None, u
        new_notification.sender_task, new_notification.receiver_task = task, receiver_task
        new_notification.trigger_go = self.go
        new_notification.save()


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
        related_name='admin_preference',
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


class DynamicJson(BaseDatesModel, CampaignInterface):
    task_stage = models.ForeignKey(
        TaskStage,
        on_delete=models.CASCADE,
        related_name='dynamic_jsons',
        null=False,
        help_text="Stage where we want set answers dynamicly"
    )
    dynamic_fields = models.JSONField(
        default=None,
        null=False,
        help_text=(
            "Get top level fields with dynamic answers"
        )
    )
    webhook = models.ForeignKey(
        Webhook,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text='Webhook using for updating schema answers'
    )  # send schema and fields

    class Meta:
        ordering = ['created_at', 'updated_at', ]

    def get_campaign(self):
        return self.task_stage.get_campaign()

    def __str__(self):
        return self.task_stage.name