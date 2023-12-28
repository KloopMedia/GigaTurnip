from django.db import models

from api.models import BaseDatesModel, TaskStage


class CountTasksModifier(BaseDatesModel):
    task_stage = models.ForeignKey(
        TaskStage,
        on_delete=models.CASCADE,
        related_name="count_tasks_modifier",
        help_text="Parent TaskStage")

    stage_to_count_tasks_from = models.ForeignKey(
        TaskStage,
        on_delete=models.CASCADE,
        related_name="task_counter",
        help_text="TaskStage whose tasks will be counted"
    )

    field_to_write_count_to = models.TextField(
        help_text="JSON field in the Task to write count to",
        default="task_count"
    )

    count_unique_users = models.BooleanField(
        help_text="Remove tasks with duplicate user id from count",
        default=False
    )

    field_to_write_count_complete = models.TextField(
        help_text="JSON field in the Task to write count complete tasks",
        default='task_count_complete'
    )
