from django.db import models, transaction, OperationalError
from django.db.models import UniqueConstraint, Q

from api.constans import TaskStageConstants
from api.models import BaseDatesModel, CampaignInterface
from api.models.stage.schema_provider import SchemaProvider


class Task(BaseDatesModel, CampaignInterface, SchemaProvider):
    assignee = models.ForeignKey(
        "CustomUser",
        on_delete=models.CASCADE,  # TODO Change deletion
        related_name="tasks",
        blank=True,
        null=True,
        help_text="User id who is responsible for the task"
    )
    stage = models.ForeignKey(
        "TaskStage",
        on_delete=models.CASCADE,
        related_name="tasks",
        help_text="Stage id"
    )
    case = models.ForeignKey(
        "Case",
        on_delete=models.CASCADE,
        related_name="tasks",
        blank=True,
        null=True,
        help_text="Case id"
    )
    responses = models.JSONField(
        null=True,
        blank=True,
        help_text="User generated responses "
                  "(answers)"
    )
    in_tasks = models.ManyToManyField(
        "self",
        related_name="out_tasks",
        blank=True,
        symmetrical=False,
        help_text="Preceded tasks"
    )
    integrator_group = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text="Response fields that must be shared "
                  "by all tasks being integrated."
    )
    complete = models.BooleanField(default=False)
    force_complete = models.BooleanField(default=False)
    reopened = models.BooleanField(
        default=False,
        help_text="Indicates that task was returned to user, "
                  "usually because of pingpong stages.")
    internal_metadata = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text='The field for internal data that wouldn\'t be shown to the user.'
    )
    start_period = models.DateTimeField(
        blank=True,
        null=True,
        help_text='the time from which this task is available'
    )
    end_period = models.DateTimeField(
        blank=True,
        null=True,
        help_text='the time until which this task is available'
    )

    class Meta:
        UniqueConstraint(
            fields=['integrator_group', 'stage'],
            name='unique_integrator_group')

    class ImpossibleToUncomplete(Exception):
        pass

    class ImpossibleToOpenPrevious(Exception):
        pass

    class AlreadyCompleted(Exception):
        pass

    class CompletionInProgress(Exception):
        pass

    def set_complete(self, responses=None, force=False, complete=True):
        if self.complete and not self.stage.chain.is_individual:
            raise Task.AlreadyCompleted

        with transaction.atomic():
            try:
                task = Task.objects.select_for_update(nowait=True).get(pk=self.id)
            except OperationalError:
                raise Task.CompletionInProgress
            # task = Task.objects.select_for_update().filter(id=self.id)[0]
            # task.complete = True
            if task.complete and not self.stage.chain.is_individual:
                raise Task.AlreadyCompleted

            if responses:
                task.responses = responses
            if force:
                task.force_complete = True
            if complete:
                task.complete = True
            task.save()
            return task

    def set_not_complete(self):
        if self.complete:
            if self.stage.assign_user_by == "IN":
                if len(self.out_tasks.all()) == 1:
                    if not self.out_tasks.all()[0].complete:
                        self.complete = False
                        self.reopened = True
                        self.save()
                        return self
        raise Task.ImpossibleToUncomplete

    def get_direct_previous(self):
        in_tasks = self.in_tasks.all()
        if len(in_tasks) == 1:
            if Task.are_directly_connected(in_tasks[0], self):
                return in_tasks[0]
        return None

    def get_next_demo(self):
        filter_next_tasks = {
            Q(stage__assign_user_by=TaskStageConstants.AUTO_COMPLETE)
            | Q(assignee=self.assignee)
        }
        tasks = list(self.out_tasks.filter(*filter_next_tasks))
        used_tasks = list()
        while tasks:
            current = tasks.pop()
            used_tasks.append(current.id)

            if current.assignee == self.assignee:
                return current
            else:
                tasks = tasks + list(
                    current.out_tasks.filter(*filter_next_tasks).exclude(
                        id__in=used_tasks
                    )
                )
        return None

    def get_direct_next(self):
        out_tasks = self.out_tasks.all()
        if len(out_tasks) == 1:
            if Task.are_directly_connected(self, out_tasks[0]):
                return out_tasks[0]
        return None

    def open_previous(self):
        if not self.complete and self.stage.allow_go_back:
            prev_task = self.get_direct_previous()
            if prev_task:
                if prev_task.assignee == self.assignee:
                    self.complete = True
                    prev_task.complete = False
                    prev_task.reopened = True
                    self.save()
                    prev_task.save()
                    return prev_task, self
        raise Task.ImpossibleToOpenPrevious

    def get_campaign(self):
        return self.stage.get_campaign()

    def get_displayed_prev_tasks(self, public=False):
        tasks = Task.objects.filter(case=self.case) \
            .filter(stage__in=self.stage.displayed_prev_stages.all()) \
            .exclude(id=self.id)
        if public:
            tasks = tasks.filter(stage__is_public=True)
        return tasks

    @staticmethod
    def are_directly_connected(task1, task2):
        in_tasks = task2.in_tasks.all()
        if in_tasks and len(in_tasks) == 1 and task1 == in_tasks[0]:
            if len(task2.stage.in_stages.all()) == 1 and \
                    task2.stage.in_stages.all()[0] == task1.stage:
                if len(task1.stage.out_stages.all()) == 1:
                    if task1.out_tasks.all().count() == 1:
                        return True
        return False

    def evaluate_quiz(self):
        quiz = self.stage.get_quiz()
        is_reopened = False
        if quiz and quiz.is_ready():
            score, incorrect_questions = quiz.check_score(self.responses)
            self.responses["meta_quiz_score"] = score
            self.responses["meta_quiz_incorrect_questions"] = incorrect_questions
            if quiz.threshold is not None and score < quiz.threshold:
                self.complete = False
                self.reopened = True
                is_reopened = True
            self.save()
        return self, is_reopened

    def __str__(self):
        return str("Task #:" + str(self.id) + self.case.__str__())
