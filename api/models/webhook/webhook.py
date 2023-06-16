import traceback
from json import JSONDecodeError

import requests
from django.db import models

from api.constans import WebhookConstants, ReplaceConstants
from api.models import BaseDatesModel, TaskStage
from api.utils.injector import text_inject


class Webhook(BaseDatesModel):
    task_stage = models.OneToOneField(
        TaskStage,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="webhook",
        help_text="Parent TaskStage")

    REQUEST_METHOD_CHOICES = [
        (RequestMethodConstants.POST, 'POST'),
        (RequestMethodConstants.PATCH, 'PATCH'),
        (RequestMethodConstants.PUT, 'PUT'),
    ]

    request_method = models.CharField(
        max_length=6,
        choices=REQUEST_METHOD_CHOICES,
        default=RequestMethodConstants.POST,
        help_text="HTTP method used to make the webhook request."
    )

    url = models.CharField(
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

    target_responses = models.BooleanField(
        default=True,
        blank=False,
        help_text="Indicates that response from webhook should be copied into Task's responses"
    )

    response_field = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "JSON response field name to extract data from. If target is"
            "Schema, this field is used to access JSON schema. Field is "
            "ignored if webhook_address field is empty."
        )
    )

    target_schema = models.BooleanField(
        default=False,
        blank=False,
        help_text="Indicates that response from webhook should be copied into Task's JSON schema"
    )

    schema_field = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "JSON response field name to extract data from. If target is"
            "Schema, this field is used to access JSON schema. Field is "
            "ignored if webhook_address field is empty."
        )
    )

    target_ui_schema = models.BooleanField(
        default=False,
        blank=False,
        help_text="Indicates that response from webhook should be copied into Task's UI schema"
    )

    ui_schema_field = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "JSON response field name to get UI JSON schema from when target is"
            " Schema. Ignored when target is not Schema or webhook_address"
            " is empty."
        )
    )

    internal_meta_field = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "JSON response field name to extract data from. If target is"
            "Schema, this field is used to access JSON schema. Field is "
            "ignored if webhook_address field is empty."
        )
    )

    target_internal_metadata = models.BooleanField(
        default=False,
        blank=False,
        help_text=("Indicates that response from webhook should be copied "
                   "into Task's internal metadata")
    )

    is_triggered = models.BooleanField(
        blank=False,
        default=True,
        help_text="Sometimes there are cases when a webhook is used by a non-taskstage "
                  "and then we need to mark it accordingly"
    )
    WHICH_RESPONSES_CHOICES = [
        (WebhookConstants.IN_RESPONSES, 'In responses'),
        (WebhookConstants.CURRENT_TASK_RESPONSES, 'Current task responses'),
        (WebhookConstants.MODIFIER_FIELD, "Data field from this modifier")
    ]
    which_responses = models.CharField(
        max_length=2,
        choices=WHICH_RESPONSES_CHOICES,
        default=WebhookConstants.IN_RESPONSES,
        help_text="Where to copy fields from"
    )

    # TARGET_CHOICES = [
    #     (WebhookTargetConstants.RESPONSES, "Current task responses"),
    #     (WebhookTargetConstants.SCHEMA, "Current task schema")
    # ]

    # target = models.CharField(
    #     max_length=2,
    #     choices=TARGET_CHOICES,
    #     default=WebhookTargetConstants.RESPONSES,
    #     help_text="Where response from webhook will be saved."
    # )

    data = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text="Data that will be sent to webhook if such option is chosen."
    )

    def trigger(self, task):
        if self.which_responses == WebhookConstants.MODIFIER_FIELD:
            data = inject(self.data, task)
            print("INJECTED DATA:")
            print(str(data))
        else:
            data = self.get_responses(task)

        # print("!!!!! URL: " + self._get_url(task))
        # print("URL DONE")

        response = self.request(inject(self.url, task), data)

        # print("!!!!! RESPONSE: " + str(response.json()))

        if not response:
            task.generate_error(
                type(KeyError),
                "Response: {0}. Webhook: {1}".format(response.status_code, self.pk),
                tb_info=traceback.format_exc(),
                data=f"{data}\nStage: {task.stage}"
            )
            return False, task, response, "See response status code"

        # try:
        #     if self.response_field:
        #         data = response.json()[self.response_field]
        #     else:
        #         data = response.json()
        # except JSONDecodeError:
        #     return False, task, response, "JSONDecodeError"

        try:
            if self.target_responses:
                if task.responses:
                    task.responses.update(self._extract_data(response, self.response_field))
                else:
                    task.responses = self._extract_data(response, self.response_field)
            if self.target_schema:
                if task.schema:
                    task.schema.update(self._extract_data(response, self.schema_field))
                else:
                    task.schema = self._extract_data(response, self.schema_field)
            if self.target_ui_schema:
                if task.ui_schema:
                    task.ui_schema.update(self._extract_data(response, self.ui_schema_field))
                else:
                    task.ui_schema = self._extract_data(response, self.ui_schema_field)
            if self.target_internal_metadata:
                if task.internal_metadata:
                    task.internal_metadata.update(self._extract_data(response, self.internal_meta_field))
                else:
                    task.internal_metadata = self._extract_data(response, self.internal_meta_field)
        except JSONDecodeError:
            return False, task, response, "JSONDecodeError"

        # if self.target == WebhookTargetConstants.SCHEMA:
        #     task.schema = data
        #     task.ui_schema = (
        #         {} if self.ui_schema_field is None
        #         else response.json()[self.ui_schema_field]
        #     )
        # else:
        #     if task.responses:
        #         task.responses.update(data)  # TODO Add error related to updating
        #     else:
        #         task.responses = data
        task.save()
        return True, task, response, ""

    @staticmethod
    def _extract_data(response, field):
        if field:
            data = response.json()[field]
        else:
            data = response.json()
        if not isinstance(data, dict):  # TODO Looks strange. Check latter.
            data = {field: data}
        return data

    def request(self, url, data):
        if self.request_method == RequestMethodConstants.PATCH:
            return requests.patch(url, json=data, headers=self.headers)
        if self.request_method == RequestMethodConstants.PUT:
            return requests.put(url, json=data, headers=self.headers)
        return requests.post(url, json=data, headers=self.headers)

    def post(self, data):
        response = requests.post(self.url, json=data, headers=self.headers)
        return response

    def get_responses(self, task):
        if self.which_responses == WebhookConstants.IN_RESPONSES:
            return list(task.in_tasks.values_list('responses', flat=True))
        return task.responses

    # def process_data(self, task):
    #     replace_dict = {}
    #     replace_dict[ReplaceConstants.USER_ID] = task.assignee.pk
    #     return self.top_level_replace(self.data, replace_dict)
    #
    # def top_level_replace(self, data, replace_dict):
    #     for key in data:
    #         new_value = replace_dict.get(data[key])
    #         if new_value is not None:
    #             data[key] = new_value
    #     return data

    # def _get_url(self, task):
    #     return inject(self.url, task)

# class Webhook(BaseDatesModel):
#     task_stage = models.OneToOneField(
#         "TaskStage",
#         primary_key=True,
#         on_delete=models.CASCADE,
#         related_name="webhook",
#         help_text="Parent TaskStage")
#
#     url = models.CharField(
#         max_length=1000,
#         help_text=(
#             "Webhook URL address. If not empty, field indicates that "
#             "task should be given not to a user in the system, but to a "
#             "webhook. Only data from task directly preceding webhook is "
#             "sent. All fields related to user assignment are ignored,"
#             "if this field is not empty."
#         )
#     )
#
#     headers = models.JSONField(
#         default=dict,
#         blank=True,
#         help_text=(
#             "Headers sent to webhook."
#         )
#     )
#
#     target_responses = models.BooleanField(
#         default=True,
#         blank=False,
#         help_text="Indicates that response from webhook should be copied into Task's responses"
#     )
#
#     response_field = models.TextField(
#         null=True,
#         blank=True,
#         help_text=(
#             "JSON response field name to extract data from. If target is"
#             "Schema, this field is used to access JSON schema. Field is "
#             "ignored if webhook_address field is empty."
#         )
#     )
#
#     target_schema = models.BooleanField(
#         default=False,
#         blank=False,
#         help_text="Indicates that response from webhook should be copied into Task's JSON schema"
#     )
#
#     schema_field = models.TextField(
#         null=True,
#         blank=True,
#         help_text=(
#             "JSON response field name to extract data from. If target is"
#             "Schema, this field is used to access JSON schema. Field is "
#             "ignored if webhook_address field is empty."
#         )
#     )
#
#     target_ui_schema = models.BooleanField(
#         default=False,
#         blank=False,
#         help_text="Indicates that response from webhook should be copied into Task's UI schema"
#     )
#
#     ui_schema_field = models.TextField(
#         null=True,
#         blank=True,
#         help_text=(
#             "JSON response field name to get UI JSON schema from when target is"
#             " Schema. Ignored when target is not Schema or webhook_address"
#             " is empty."
#         )
#     )
#
#     internal_meta_field = models.TextField(
#         null=True,
#         blank=True,
#         help_text=(
#             "JSON response field name to extract data from. If target is"
#             "Schema, this field is used to access JSON schema. Field is "
#             "ignored if webhook_address field is empty."
#         )
#     )
#
#     target_internal_metadata = models.BooleanField(
#         default=False,
#         blank=False,
#         help_text=("Indicates that response from webhook should be copied "
#                    "into Task's internal metadata")
#     )
#
#     is_triggered = models.BooleanField(
#         blank=False,
#         default=True,
#         help_text="Sometimes there are cases when a webhook is used by a non-taskstage "
#                   "and then we need to mark it accordingly"
#     )
#     WHICH_RESPONSES_CHOICES = [
#         (WebhookConstants.IN_RESPONSES, 'In responses'),
#         (WebhookConstants.CURRENT_TASK_RESPONSES, 'Current task responses'),
#         (WebhookConstants.MODIFIER_FIELD, "Data field from this modifier")
#     ]
#     which_responses = models.CharField(
#         max_length=2,
#         choices=WHICH_RESPONSES_CHOICES,
#         default=WebhookConstants.IN_RESPONSES,
#         help_text="Where to copy fields from"
#     )
#
#     # TARGET_CHOICES = [
#     #     (WebhookTargetConstants.RESPONSES, "Current task responses"),
#     #     (WebhookTargetConstants.SCHEMA, "Current task schema")
#     # ]
#
#     # target = models.CharField(
#     #     max_length=2,
#     #     choices=TARGET_CHOICES,
#     #     default=WebhookTargetConstants.RESPONSES,
#     #     help_text="Where response from webhook will be saved."
#     # )
#
#     data = models.JSONField(
#         null=True,
#         blank=True,
#         default=None,
#         help_text="Data that will be sent to webhook if such option is chosen."
#     )
#
#     def trigger(self, task):
#         if self.which_responses == WebhookConstants.MODIFIER_FIELD:
#             data = self.process_data(task)
#         else:
#             data = self.get_responses(task)
#
#         response = requests.post(
#             self._get_url(task),
#             json=data,
#             headers=self.headers
#         )
#
#         if not response:
#             task.generate_error(
#                 type(KeyError),
#                 "Response: {0}. Webhook: {1}".format(response.status_code, self.pk),
#                 tb_info=traceback.format_exc(),
#                 data=f"{data}\nStage: {task.stage}"
#             )
#             return False, task, response, "See response status code"
#
#         # try:
#         #     if self.response_field:
#         #         data = response.json()[self.response_field]
#         #     else:
#         #         data = response.json()
#         # except JSONDecodeError:
#         #     return False, task, response, "JSONDecodeError"
#
#         try:
#             if self.target_responses:
#                 if task.responses:
#                     task.responses.update(self._extract_data(response, self.response_field))
#                 else:
#                     task.responses = self._extract_data(response, self.response_field)
#             if self.target_schema:
#                 if task.schema:
#                     task.schema.update(self._extract_data(response, self.schema_field))
#                 else:
#                     task.schema = self._extract_data(response, self.schema_field)
#             if self.target_ui_schema:
#                 if task.ui_schema:
#                     task.ui_schema.update(self._extract_data(response, self.ui_schema_field))
#                 else:
#                     task.ui_schema = self._extract_data(response, self.ui_schema_field)
#             if self.target_internal_metadata:
#                 if task.internal_metadata:
#                     task.internal_metadata.update(self._extract_data(response, self.internal_meta_field))
#                 else:
#                     task.internal_metadata = self._extract_data(response, self.internal_meta_field)
#         except JSONDecodeError:
#             return False, task, response, "JSONDecodeError"
#
#         # if self.target == WebhookTargetConstants.SCHEMA:
#         #     task.schema = data
#         #     task.ui_schema = (
#         #         {} if self.ui_schema_field is None
#         #         else response.json()[self.ui_schema_field]
#         #     )
#         # else:
#         #     if task.responses:
#         #         task.responses.update(data)  # TODO Add error related to updating
#         #     else:
#         #         task.responses = data
#         task.save()
#         return True, task, response, ""
#
#     @staticmethod
#     def _extract_data(response, field):
#         if field:
#             data = response.json()[field]
#         else:
#             data = response.json()
#         if not isinstance(data, dict):
#             data = {field: data}
#         return data
#
#     def post(self, data):
#         response = requests.post(self.url, json=data, headers=self.headers)
#         return response
#
#     def get_responses(self, task):
#         if self.which_responses == WebhookConstants.IN_RESPONSES:
#             return list(task.in_tasks.values_list('responses', flat=True))
#         return task.responses
#
#     def process_data(self, task):
#         replace_dict = {}
#         replace_dict[ReplaceConstants.USER_ID] = task.assignee.pk
#         return self.top_level_replace(self.data, replace_dict)
#
#     def top_level_replace(self, data, replace_dict):
#         for key in data:
#             new_value = replace_dict.get(data[key])
#             if new_value is not None:
#                 data[key] = new_value
#         return data
#
#     def _get_url(self, task):
#         return text_inject(self.url, task)
