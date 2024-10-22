from django.db import models

from okutool.constants import QuestionAttachmentType


class Test(models.Model):
    stage = models.OneToOneField(
        "api.TaskStage",
        on_delete=models.CASCADE,
        related_name="test",
    )
    question_limit = models.IntegerField(
        default=0,
        help_text="Limit the number of questions shown",
    )
    passing_score = models.IntegerField(default=0)
    order_by = models.CharField(
        max_length=3,
        default="RND",
        choices=[
            ("RND", "Random"),
            ("IND", "Index"),
        ],
    )

    def __str__(self) -> str:
        return f"#{self.id} - {self.stage.name}"


class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="questions")
    index = models.PositiveIntegerField(default=0)
    title = models.TextField(null=True, blank=True)
    json_schema = models.JSONField(null=True, blank=True)
    ui_schema = models.JSONField(null=True, blank=True)
    correct_answer = models.JSONField(null=True, blank=True)

    def __str__(self) -> str:
        return self.title


def attachment_upload_path(instance, filename):
    return f"attachments/{instance.question.test.id}/{filename}"


class QuestionAttachment(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    type = models.CharField(
        max_length=2,
        choices=[
            (QuestionAttachmentType.AUDIO, "Audio"),
            (QuestionAttachmentType.IMAGE, "Image"),
            (QuestionAttachmentType.VIDEO, "Video"),
            (QuestionAttachmentType.OTHER, "Other file types"),
        ],
    )
    file = models.FileField(upload_to=attachment_upload_path)

    def __str__(self) -> str:
        return self.question.title
