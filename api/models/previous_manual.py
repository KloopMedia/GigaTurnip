from django.contrib.postgres.fields import ArrayField
from django.db import models

from api.models import BaseDatesModel


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
        "TaskStage",
        related_name='previous_manual_to_assign',
        on_delete=models.CASCADE,
        help_text='This task will assign to the user. '
                  'Also, you have to set assign_user_by as PM in this TaskStage to use manual assignment.'
    )
    task_stage_email = models.OneToOneField(
        "TaskStage",
        on_delete=models.CASCADE,
        help_text='Task stage to get email from responses to assign task'
    )

    def __str__(self):
        return f'ID {self.id}; {self.field[-1]}'
