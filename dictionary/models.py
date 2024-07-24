from django.db import models


class ProficiencyLevel(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Word(models.Model):
    text = models.CharField(max_length=255)
    translation = models.CharField(max_length=255)
    definition = models.TextField(blank=True)
    audio = models.FileField(upload_to="audios", null=True)
    image = models.FileField(upload_to="images", null=True)
    examples = models.JSONField(null=True)
    level = models.ForeignKey(ProficiencyLevel, null=True, on_delete=models.SET_NULL)
    category = models.ForeignKey(Category, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.text} - {self.translation}"
