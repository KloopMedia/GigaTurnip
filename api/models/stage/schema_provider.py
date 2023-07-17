from django.db import models

from api.models import BaseDatesModel


class SchemaProvider(models.Model):
    json_schema = models.JSONField(
        null=True,
        blank=True,
        help_text="Defines the underlying data to be shown in the UI "
                  "(objects, properties, and their types)"
    )
    ui_schema = models.JSONField(
        null=True,
        blank=True,
        default=dict(),
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


class StagePublisher(BaseDatesModel, SchemaProvider):
    task_stage = models.OneToOneField(
        "TaskStage",
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
