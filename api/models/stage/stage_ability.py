from django.db import models
from api.models.base import BaseModel


class StageAbilityAward(BaseModel, models.Model):
    stage = models.ForeignKey('Stage', on_delete=models.CASCADE)
    ability_award = models.ForeignKey('AbilityAward', on_delete=models.CASCADE)