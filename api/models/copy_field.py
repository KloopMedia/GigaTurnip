from django.apps import apps
from django.db import models

from api.constans import CopyFieldConstants
from api.models import BaseDatesModel


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
        "TaskStage",
        on_delete=models.CASCADE,
        related_name="copy_fields",
        help_text="Stage of the task that accepts data being copied")
    copy_from_stage = models.ForeignKey(
        "TaskStage",
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
            original_task = apps.get_model("api.task").objects.filter(
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
