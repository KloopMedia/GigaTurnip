from django.db import models


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
