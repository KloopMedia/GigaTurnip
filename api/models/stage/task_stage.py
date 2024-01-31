import json

from django.db import models

from . import Stage
from . import SchemaProvider
from ...constans import TaskStageSchemaSourceConstants, TaskStageConstants


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
    STAGE_TYPES = (
        ("PR", "Proactive"),
        ("AC", "Reactive"),
        ("PB", "Proactive buttons"),
    )
    stage_type = models.CharField(
        choices=STAGE_TYPES,
        max_length=2,
        blank=True,
        default="AC",
        null=True,
        help_text="Stage type."
    )

    SCHEMA_SOURCE_CHOICES = [
        (TaskStageSchemaSourceConstants.STAGE, 'Stage'),
        (TaskStageSchemaSourceConstants.TASK, 'Task'),
    ]
    schema_source = models.CharField(
        max_length=2,
        choices=SCHEMA_SOURCE_CHOICES,
        default=TaskStageSchemaSourceConstants.STAGE,
        help_text="Flag indicating from where Task should get its schema.")

    sms_complete_task_allow = models.BooleanField(
        default=False,
        null=True,
            help_text="If the Task Stage accept tasks via sms."
    )

    skip_empty_individual_tasks = models.BooleanField(
        default=False,
        help_text="If in individuals chains this stage don't have any tasks - it wouldn't be returned in chain individuals."
    )
    available_from = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Available from."
    )
    available_to = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Available to."
    )

    complete_individual_chain = models.BooleanField(
        default=False,
        help_text="If true and user have tasks on this chain - so chain will be considered as completed."
    )

    filter_fields_schema = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "This filed will store schema for filters."
        )
    )

    fast_track_rank = models.ForeignKey(
        "Rank",
        related_name="fast_track_rank",
        blank=True,
        null=True,
        on_delete = models.SET_NULL,
        help_text="Rank that will be given when using fast_track"
    )

    take_task_button_text = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text="Text that will be shown on the take task button"
    )

    external_renderer_url = models.URLField(
        null=True,
        blank=True,
        max_length=1000,
        help_text=(
            "External renderer url"
        )
    )

    def get_integration(self):
        if hasattr(self, 'integration'):
            return self.integration
        return None

    def get_previous_manual_to_assign(self):
        if hasattr(self, 'previous_manual_to_assign'):
            return self.previous_manual_to_assign
        return None

    @property
    def _translation_adapter(self):
        return getattr(self, 'translation_adapter', None)

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
