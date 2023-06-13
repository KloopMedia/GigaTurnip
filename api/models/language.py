from django.db import models
from rest_framework.exceptions import ValidationError


def validate_language_code(val):
    if len(val) == 2 and val.isalpha():
        return val.lower()
    raise ValidationError(
        "This field is two letters code(format ISO 639-1).\n"
        "Check available codes in wikipedia: \"https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes\"."
    )


class Language(models.Model):
    name = models.CharField(
        max_length=128,
        blank=False,
        null=False,
        help_text="ISO language name."
    )
    code = models.CharField(
        max_length=2,
        blank=False,
        null=False,
        validators=[validate_language_code],
        help_text="Two letters code of language."
    )

    def __str__(self):
        return "{}: {}".format(self.name, self.code)
