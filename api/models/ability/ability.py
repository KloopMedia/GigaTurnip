from django.db import models
from api.models.base import BaseModel


class Ability(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name
