import json
import re

from django.apps import apps
from django.db import models

from api.models import BaseDatesModel, CampaignInterface


class ResponseFlattener(BaseDatesModel, CampaignInterface):
    task_stage = models.OneToOneField(
        "TaskStage",
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
        ui = self.task_stage.ui_schema
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
            system_columns = list(apps.get_model("api.task")().__dict__.keys())
            list_of_unnecessary_keys = ['id', '_state', 'responses']
            for i in list_of_unnecessary_keys:
                system_columns.remove(i)

        finally_columns = ['id'] + system_columns + [i.split("__", 1)[1] for i in ordered_columns]
        for i, col in enumerate(self.columns):
            position = i + 1 + len(system_columns)
            finally_columns.insert(position, col)
        return finally_columns

    def get_campaign(self):
        return self.task_stage.get_campaign()
