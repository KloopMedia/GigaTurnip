from django.db import models


class Country(models.Model):
    name = models.CharField(
        max_length=526,
        unique=True,
        help_text="Country name"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Countries"
