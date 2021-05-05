from django.db import models
from polymorphic.models import PolymorphicModel


# Create your models here.


class BaseModel(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        abstract = True


class SchemaProvider(models.Model):
    json_schema = models.JSONField(null=True)
    ui_schema = models.JSONField(null=True)
    library = models.CharField(max_length=200, blank=True)

    class Meta:
        abstract = True


class Campaign(BaseModel):

    def __str__(self):
        return str("Campaign: " + self.name)


class Chain(BaseModel):
    campaign = models.ForeignKey(Campaign,
                                 on_delete=models.CASCADE,
                                 related_name="chains")

    def __str__(self):
        return str("Chain: " +
                   self.name + " " +
                   self.campaign.__str__())


class Stage(PolymorphicModel, BaseModel):
    chain = models.ForeignKey(Chain,
                              on_delete=models.CASCADE,
                              related_name="stages")

    out_stages = models.ManyToManyField("self",
                                       related_name="in_stages",
                                       symmetrical=False,
                                       blank=True)

    def __str__(self):
        return str("Stage: " +
                   self.name + " " +
                   self.chain.__str__())


class TaskStage(Stage, SchemaProvider):

    copy_input = models.BooleanField()
    displayed_prev_stages = models.ManyToManyField(Stage,
                                                   related_name="displayed_following_stages",
                                                   blank=True)

    def __str__(self):
        return str("Task Stage Filler for " +
                   self.stage.__str__())


class WebHookStage(Stage, SchemaProvider):

    web_hook_address = models.TextField()

    def __str__(self):
        return str("Web Hook Stage Filler for " + self.stage.__str__())


class ConditionalStage(Stage):

    conditions_schema = ""
    conditions = models.JSONField(null=True)

    def __str__(self):
        return str("Conditional Stage Filler for " + self.stage__str__())


class Case(models.Model):
    chain = models.ForeignKey(Chain,
                              on_delete=models.CASCADE,
                              related_name="cases")

    def __str__(self):
        return str("Case #" +
                   str(self.id) + " " +
                   self.chain.__str__())


class Task(models.Model):
    stage = models.ForeignKey(TaskStage,
                              on_delete=models.CASCADE,
                              related_name="tasks")
    case = models.ForeignKey(Case,
                             on_delete=models.CASCADE,
                             related_name="tasks")
    responses = models.JSONField(null=True)
    in_tasks = models.ManyToManyField("self",
                                      related_name="out_tasks",
                                      blank=True,
                                      symmetrical=False)

    def __str__(self):
        return str("Task #:" + str(self.id) + self.case.__str__())
