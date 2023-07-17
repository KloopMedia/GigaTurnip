import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class RankTest(GigaTurnipTestHelper):

    def test_assignee_new_ranks_based_on_prerequisite(self):
        prize_rank_1 = Rank.objects.create(name='Good', track=self.user.ranks.all()[0].track)
        prize_rank_2 = Rank.objects.create(name='Best', track=self.user.ranks.all()[0].track)
        prize_rank_3 = Rank.objects.create(name='Superman', track=self.user.ranks.all()[0].track)
        prize_rank_3.prerequisite_ranks.add(prize_rank_1)
        prize_rank_3.prerequisite_ranks.add(prize_rank_2)
        notification = Notification.objects.create(
            title="You achieve new rank",
            text="Congratulations! You achieve new rank!",
            campaign=self.campaign
        )
        schema = {"type": "object", "properties": {"foo": {"type": "string", "title": "what is ur name"}}}

        self.initial_stage.json_schema = schema
        self.initial_stage.save()
        task_award_1 = TaskAward.objects.create(
            task_stage_completion=self.initial_stage,
            task_stage_verified=self.initial_stage,
            rank=prize_rank_1,
            count=5,
            notification=notification
        )

        another_chain = Chain.objects.create(name='Chain for getting best', campaign=self.campaign)
        new_initial = TaskStage.objects.create(
            name="Initial for Good persons",
            x_pos=1,
            y_pos=1,
            json_schema=self.initial_stage.json_schema,
            chain=another_chain,
            is_creatable=True)
        rank_limit = RankLimit.objects.create(
            rank=prize_rank_1,
            stage=new_initial,
            open_limit=0,
            total_limit=0,
            is_listing_allowed=True,
            is_creation_open=True
        )
        task_award_2 = TaskAward.objects.create(
            task_stage_completion=new_initial,
            task_stage_verified=new_initial,
            rank=prize_rank_2,
            count=5,
            notification=notification
        )

        responses = {"foo": "Kloop"}
        task = self.create_initial_task()
        for i in range(task_award_1.count):
            task = self.complete_task(task, responses)
            if task_award_1.count - 1 > i:
                task = self.create_initial_task()
                self.assertNotIn(prize_rank_2, self.user.ranks.all())
                self.assertNotIn(prize_rank_3, self.user.ranks.all())
            else:
                self.assertIn(prize_rank_1, self.user.ranks.all())
        self.assertIn(prize_rank_1, self.user.ranks.all())
        self.assertNotIn(prize_rank_2, self.user.ranks.all())
        self.assertNotIn(prize_rank_3, self.user.ranks.all())
        another_rank_1 = Rank.objects.create(name='Barmaley', track=self.user.ranks.all()[0].track)
        another_rank_2 = Rank.objects.create(name='Jeenbekov', track=self.user.ranks.all()[0].track)
        self.user.ranks.add(another_rank_2)
        self.user.ranks.add(another_rank_1)
        self.user.ranks.add(prize_rank_1)

        task = self.create_task(new_initial)
        for i in range(task_award_2.count):
            task = self.complete_task(task, responses)
            if task_award_2.count - 1 > i:
                task = self.create_task(new_initial)
                self.assertIn(prize_rank_1, self.user.ranks.all())
                self.assertNotIn(prize_rank_2, self.user.ranks.all())
                self.assertNotIn(prize_rank_3, self.user.ranks.all())
            else:
                self.assertIn(prize_rank_2, self.user.ranks.all())
                self.assertIn(prize_rank_3, self.user.ranks.all())
        self.assertIn(prize_rank_1, self.user.ranks.all())
        self.assertIn(prize_rank_2, self.user.ranks.all())
        self.assertIn(prize_rank_3, self.user.ranks.all())

    def test_assign_rank_by_parent_rank(self):
        schema = {"type": "object", "properties": {"foo": {"type": "string", "title": "what is ur name"}}}
        self.initial_stage.json_schema = schema
        prize_rank_1 = Rank.objects.create(name='GOOD RANK')
        notification = Notification.objects.create(
            title="You achieve new rank",
            text="Congratulations! You achieve new rank!",
            campaign=self.campaign
        )
        task_awards = TaskAward.objects.create(
            task_stage_completion=self.initial_stage,
            task_stage_verified=self.initial_stage,
            rank=prize_rank_1,
            count=1,
            notification=notification
        )

        second_stage = self.initial_stage.add_stage(TaskStage(
            name='Second stage',
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage,
            json_schema=self.initial_stage.json_schema
        ))
        prize_rank_2 = Rank.objects.create(name='BEST RANK')
        task_awards = TaskAward.objects.create(
            task_stage_completion=second_stage,
            task_stage_verified=second_stage,
            rank=prize_rank_2,
            count=1,
            notification=notification
        )

        super_rank = Rank.objects.create(name='SUPERMAN RANK')
        super_rank.prerequisite_ranks.add(prize_rank_1)
        super_rank.prerequisite_ranks.add(prize_rank_2)
        super_rank.save()
        resp = {"foo": "hello world"}
        task = self.create_initial_task()
        task = self.complete_task(task, resp)
        second_task = task.out_tasks.get()
        second_task = self.complete_task(second_task, resp)

        self.assertEqual(Notification.objects.count(), 3)
        self.assertEqual(self.user.ranks.count(), 4)

