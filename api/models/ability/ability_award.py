from django.db import models
from api.models.base import BaseModel


class AbilityAward(models.Model):
    TYPE_CHOICES = [
        ('points', 'Баллы'),
        ('money', 'Деньги'),
    ]

    ability = models.ForeignKey('Ability', on_delete=models.CASCADE, related_name='awards')
    award_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='points')
    amount = models.IntegerField()

    def __str__(self):
        return f"{self.ability.name} ({self.get_award_type_display()} - {self.amount})"
