from django.db import models
from api.models.base import BaseModel

class StageVolume(BaseModel, models.Model):
    stage = models.ForeignKey('Stage', on_delete=models.CASCADE)
    volume = models.ForeignKey('Volume', on_delete=models.CASCADE)