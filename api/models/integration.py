from django.apps import apps
from django.db import models

from api.models import BaseDatesModel


class Integration(BaseDatesModel):
    task_stage = models.OneToOneField(
        "TaskStage",
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
        integrator_task = apps.get_model("api.task").objects.get_or_create(
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
