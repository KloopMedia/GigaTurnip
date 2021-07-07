from django.contrib.auth.models import AbstractUser
from django.db import models
from polymorphic.models import PolymorphicModel


class CustomUser(AbstractUser):
    ranks = models.ManyToManyField("Rank",
                                   through='RankRecord',
                                   related_name="users")


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
    default_track = models.ForeignKey("Track",
                                      on_delete=models.CASCADE,
                                      blank=True,
                                      null=True,
                                      related_name="default_campaign")

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
    x_pos = models.DecimalField(max_digits=17, decimal_places=14)
    y_pos = models.DecimalField(max_digits=17, decimal_places=14)
    chain = models.ForeignKey(Chain,
                              on_delete=models.CASCADE,
                              related_name="stages")

    in_stages = models.ManyToManyField("self",
                                       related_name="out_stages",
                                       symmetrical=False,
                                       blank=True)

    def __str__(self):
        return str("Stage: " +
                   self.name + " " +
                   self.chain.__str__())


class TaskStage(Stage, SchemaProvider):
    copy_input = models.BooleanField(default=False)
    allow_multiple_files = models.BooleanField(default=False)
    is_creatable = models.BooleanField(default=False)
    count_complete = models.BooleanField(default=False)
    displayed_prev_stages = models.ManyToManyField(Stage,
                                                   related_name="displayed_following_stages",
                                                   blank=True)


class WebHookStage(Stage, SchemaProvider):

    web_hook_address = models.TextField()

    def __str__(self):
        return str("Web Hook Stage Filler for " + self.stage.__str__())


class ConditionalStage(Stage):
    conditions = models.JSONField(null=True)
    pingpong = models.BooleanField(default=False)

    # def __str__(self):
    #     return str("Conditional Stage Filler for " + self.stage__str__())


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


class Rank(BaseModel):
    stages = models.ManyToManyField(TaskStage,
                                    related_name="ranks",
                                    through="RankStageLimits")


class Track(BaseModel):
    campaign = models.ForeignKey(Campaign,
                                 related_name="ranks",
                                 on_delete=models.CASCADE)
    ranks = models.ManyToManyField(Rank, related_name="tracks")
    default_rank = models.ForeignKey(Rank,
                                     on_delete=models.CASCADE,
                                     blank=True,
                                     null=True)


class RankRecord(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    rank = models.ForeignKey(Rank, on_delete=models.CASCADE)


class RankStageLimits(models.Model):
    rank = models.ForeignKey(Rank, on_delete=models.CASCADE)
    stage = models.ForeignKey(TaskStage, on_delete=models.CASCADE)
    open_limit = models.IntegerField(default=0)
    total_limit = models.IntegerField(default=0)
    list_permission = models.BooleanField(default=False)
    close_submission = models.BooleanField(default=False)
    close_selection = models.BooleanField(default=False)
