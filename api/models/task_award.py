from django.apps import apps
from django.db import models

from api.models import BaseDatesModel, CampaignInterface


class TaskAward(BaseDatesModel, CampaignInterface):
    task_stage_completion = models.ForeignKey(
        "TaskStage",
        on_delete=models.CASCADE,
        related_name="task_stage_completion",
        help_text="Task Stage completion. Usually, it is the stage that the user completes.")
    task_stage_verified = models.ForeignKey(
        "TaskStage",
        on_delete=models.CASCADE,
        related_name="task_stage_verified",
        help_text="Task Stage verified. It is the stage that is checked by the verifier.")
    rank = models.ForeignKey(
        "Rank",
        on_delete=models.CASCADE,
        help_text="Rank to create the record with a user. It is a rank that will be given user, as an award who "
                  "have completed a defined count of tasks")
    stop_chain = models.BooleanField(
        default=False,
        help_text='When rank will obtained by user chain will stop.'
    )
    count = models.PositiveIntegerField(help_text="The count of completed tasks to give an award.")
    notification = models.ForeignKey(
        'Notification',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Notification which will be sent on achieving new rank.'
    )

    def get_campaign(self):
        return self.task_stage_completion.chain.campaign

    def connect_user_with_rank(self, task):
        """
        The method gives an award to the user if the user completed a defined count of tasks.
        In the beginning, we find all his tasks by cases and get all that haven't been force completed by the verifier.
        If the count is equal - we will create RankRecord with prize rank with the user.
        :param task:
        :return:
        """
        # Get user from task which stage is stage of completion
        user = task.case.tasks.filter(
            complete=True,
            force_complete=False,
            stage=self.task_stage_completion).last().assignee

        # Get tasks which was completed by user to get cases id
        cases_of_tasks = user.tasks.filter(
            stage=self.task_stage_completion,
            complete=True,
            force_complete=False).values_list('case', flat=True)

        # Get all tasks with our needing cases
        verified = apps.get_model("api.task").objects.filter(
            case__in=cases_of_tasks)\
            .filter(
                stage=self.task_stage_verified, force_complete=False)

        # if count is equal -> create notification and give rank
        if verified.count() == self.count:
            rank_record = user.user_ranks.filter(rank=self.rank)
            if rank_record:
                return rank_record[0]
            rank_record = apps.get_model("api.rankrecord").objects.create(
                user=user, rank=self.rank)
            if self.notification:
                new_notification = self.notification
                new_notification.pk, new_notification.target_user = None, user
                new_notification.save()

            return rank_record
        else:
            return None

    def __str__(self):
        return f"Completion: {self.task_stage_completion.id} " \
               f"Verified: {self.task_stage_verified.id} " \
               f"Rank: {self.rank.id}"

