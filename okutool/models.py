from django.db import models

from okutool.constants import QuestionAttachmentType, StageType


class Volume(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)


class Stage(models.Model):
    volume = models.ForeignKey(Volume, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=2,
        choices=[
            (StageType.THEORY, "Theoretical lesson"),
            (StageType.PRACTICE, "Practical lesson"),
            (StageType.TEST, "Test"),
        ],
    )
    richtext = models.TextField(null=True, blank=True)
    json_form = models.JSONField(null=True, blank=True)
    in_stages = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="out_stages",
        blank=True,
    )


class Task(models.Model):
    assignee = models.ForeignKey(
        "api.CustomUser",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    stage = models.ForeignKey(
        Stage,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    in_tasks = models.ManyToManyField(
        "self",
        related_name="out_tasks",
        blank=True,
        symmetrical=False,
    )
    complete = models.BooleanField(default=False)
    total_count = models.IntegerField(default=0)
    succesful_count = models.IntegerField(default=0)
    last_score = models.IntegerField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)


class Question(models.Model):
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE)
    title = models.TextField(null=True, blank=True)
    form = models.JSONField(null=True, blank=True)
    correct_answer = models.JSONField(null=True, blank=True)


class QuestionAttachment(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=2,
        choices=[
            (QuestionAttachmentType.AUDIO, "Audio"),
            (QuestionAttachmentType.IMAGE, "Image"),
            (QuestionAttachmentType.VIDEO, "Video"),
            (QuestionAttachmentType.OTHER, "Other file types"),
        ],
    )
    file = models.FileField()
