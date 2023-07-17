import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class TaskAwardTest(GigaTurnipTestHelper):

    def test_task_awards_count_is_equal(self):
        self.initial_stage.json_schema = {
            "type": "object",
            "properties": {
                "answer": {
                    "title": "Question 1",
                    "type": "string"
                }
            },
            "required": [
                "answer"
            ]
        }
        self.initial_stage.save()
        verification_task_stage = self.initial_stage.add_stage(TaskStage(
            name='verification',
            assign_user_by=TaskStageConstants.RANK
        ))
        verification_task_stage.json_schema = {
            "type": "object",
            "properties": {
                "decision": {
                    "enum": ["reject", "pass"],
                    "title": "Question 1",
                    "type": "string"
                }
            },
            "required": [
                "decision"
            ]
        }
        verification_task_stage.save()

        verifier_rank = Rank.objects.create(name="verifier")
        RankRecord.objects.create(
            user=self.employee,
            rank=Rank.objects.get(name="Initial"))
        RankRecord.objects.create(
            user=self.user,
            rank=verifier_rank)

        prize_rank = Rank.objects.create(name="SUPERMAN")
        notification = Notification.objects.create(
            title="You achieve new rank",
            text="Congratulations! You achieve new rank!",
            campaign=self.campaign
        )
        task_awards = TaskAward.objects.create(
            task_stage_completion=self.initial_stage,
            task_stage_verified=verification_task_stage,
            rank=prize_rank,
            count=3,
            notification=notification
        )

        rank_l = RankLimit.objects.create(
            rank=verifier_rank,
            stage=verification_task_stage,
            open_limit=5,
            total_limit=0,
            is_creation_open=False,
            is_listing_allowed=True,
            is_selection_open=True,
            is_submission_open=True)

        for i in range(3):
            task = self.create_task(self.initial_stage, self.employee_client)
            task = self.complete_task(task, {"answer": "norm"}, self.employee_client)

            response_assign = self.get_objects("task-request-assignment", pk=task.out_tasks.all()[0].id)
            self.assertEqual(response_assign.status_code, status.HTTP_200_OK)
            task_to_check = Task.objects.get(assignee=self.user, case=task.case)
            task_to_check = self.complete_task(task_to_check, {"decision": "pass"}, client=self.client)

        employee_ranks = [i.rank for i in RankRecord.objects.filter(user=self.employee)]
        self.assertEqual(len(employee_ranks), 2)
        self.assertIn(prize_rank, employee_ranks)

        user_notifications = Notification.objects.filter(target_user=self.employee,
                                                         title=task_awards.notification.title)
        self.assertEqual(user_notifications.count(), 1)

    def test_task_awards_count_is_lower(self):
        self.initial_stage.json_schema = {
            "type": "object",
            "properties": {
                "answer": {
                    "title": "Question 1",
                    "type": "string"
                }
            },
            "required": [
                "answer"
            ]
        }
        self.initial_stage.save()

        verification_task_stage = self.initial_stage.add_stage(TaskStage(
            name='verification',
            assign_user_by=TaskStageConstants.RANK
        ))
        verification_task_stage.json_schema = {
            "type": "object",
            "properties": {
                "decision": {
                    "enum": ["reject", "pass"],
                    "title": "Question 1",
                    "type": "string"
                }
            },
            "required": [
                "decision"
            ]
        }
        verification_task_stage.save()

        verifier_rank = Rank.objects.create(name="verifier")
        RankRecord.objects.create(
            user=self.employee,
            rank=Rank.objects.get(name="Initial"))
        RankRecord.objects.create(
            user=self.user,
            rank=verifier_rank)

        prize_rank = Rank.objects.create(name="SUPERMAN")
        notification = Notification.objects.create(
            title="You achieve new rank",
            text="Congratulations! You achieve new rank!",
            campaign=self.campaign
        )
        task_awards = TaskAward.objects.create(
            task_stage_completion=self.initial_stage,
            task_stage_verified=verification_task_stage,
            rank=prize_rank,
            count=3,
            notification=notification
        )

        rank_l = RankLimit.objects.create(
            rank=verifier_rank,
            stage=verification_task_stage,
            open_limit=5,
            total_limit=0,
            is_creation_open=False,
            is_listing_allowed=True,
            is_selection_open=True,
            is_submission_open=True)

        for i in range(2):
            task = self.create_task(self.initial_stage, self.employee_client)
            task = self.complete_task(task, {"answer": "norm"}, client=self.employee_client)

            response_assign = self.get_objects("task-request-assignment", {"decision": "pass"},
                                               pk=task.out_tasks.all()[0].id)
            self.assertEqual(response_assign.status_code, status.HTTP_200_OK)
            task_to_check = Task.objects.get(assignee=self.user, case=task.case)
            task_to_check = self.complete_task(task_to_check, {"decision": "pass"}, client=self.client)

        employee_ranks = [i.rank for i in RankRecord.objects.filter(user=self.employee)]
        self.assertEqual(len(employee_ranks), 1)
        self.assertNotIn(prize_rank, employee_ranks)

        user_notifications = Notification.objects.filter(target_user=self.employee,
                                                         title=task_awards.notification.title)
        self.assertEqual(user_notifications.count(), 0)

    def test_task_awards_count_many_task_stages(self):
        self.initial_stage.json_schema = {
            "type": "object",
            "properties": {
                "answer": {
                    "title": "Question 1",
                    "type": "string"
                }
            },
            "required": [
                "answer"
            ]
        }
        self.initial_stage.save()

        second_task_stage = self.initial_stage.add_stage(TaskStage(
            name='Second stage',
            json_schema=self.initial_stage.json_schema,
            assign_user_by="ST",
            assign_user_from_stage=self.initial_stage))
        verification_task_stage = second_task_stage.add_stage(TaskStage(
            name='verification',
            assign_user_by=TaskStageConstants.RANK
        ))
        verification_task_stage.json_schema = {
            "type": "object",
            "properties": {
                "decision": {
                    "enum": ["reject", "pass"],
                    "title": "Question 1",
                    "type": "string"
                }
            },
            "required": [
                "decision"
            ]
        }
        verification_task_stage.save()

        verifier_rank = Rank.objects.create(name="verifier")
        RankRecord.objects.create(
            user=self.employee,
            rank=Rank.objects.get(name="Initial"))
        RankRecord.objects.create(
            user=self.user,
            rank=verifier_rank)

        prize_rank = Rank.objects.create(name="SUPERMAN")
        notification = Notification.objects.create(
            campaign=self.campaign,
            title="You achieve new rank",
            text="Congratulations! You achieve new rank!"
        )
        task_awards = TaskAward.objects.create(
            task_stage_completion=self.initial_stage,
            task_stage_verified=verification_task_stage,
            rank=prize_rank,
            count=3,
            notification=notification
        )

        rank_l = RankLimit.objects.create(
            rank=verifier_rank,
            stage=verification_task_stage,
            open_limit=5,
            total_limit=0,
            is_creation_open=False,
            is_listing_allowed=True,
            is_selection_open=True,
            is_submission_open=True)

        for i in range(3):
            task = self.create_task(self.initial_stage, self.employee_client)
            task = self.complete_task(task, {"answer": "norm"}, client=self.employee_client)
            task_2 = task.out_tasks.all()[0]
            task_2 = self.complete_task(task_2, {"answer": "norm2"}, client=self.employee_client)

            response_assign = self.get_objects("task-request-assignment", {"decision": "pass"},
                                               pk=task_2.out_tasks.all()[0].id)
            self.assertEqual(response_assign.status_code, status.HTTP_200_OK)
            task_to_check = Task.objects.get(assignee=self.user, case=task.case)
            task_to_check = self.complete_task(task_to_check, {"decision": "pass"}, client=self.client)

        employee_ranks = [i.rank for i in RankRecord.objects.filter(user=self.employee)]
        self.assertEqual(len(employee_ranks), 2)
        self.assertIn(prize_rank, employee_ranks)

        user_notifications = Notification.objects.filter(target_user=self.employee,
                                                         title=task_awards.notification.title)
        self.assertEqual(user_notifications.count(), 1)

    def test_task_awards_for_giving_ranks(self):
        self.initial_stage.json_schema = {
            "type": "object",
            "properties": {
                "answer": {
                    "title": "Question 1",
                    "type": "string"
                }
            },
            "required": [
                "answer"
            ]
        }
        self.initial_stage.save()
        conditional_stage = ConditionalStage()
        conditional_stage.conditions = [{"field": "answer", "type": "string", "value": "norm", "condition": "=="}]
        conditional_stage = self.initial_stage.add_stage(conditional_stage)
        verification_task_stage = conditional_stage.add_stage(TaskStage(
            name='verification',
            assign_user_by="AU"
        ))
        verification_task_stage.json_schema = {
            "type": "object",
            "properties": {
                "decision": {
                    "enum": ["reject", "pass"],
                    "title": "Question 1",
                    "type": "string"
                }
            },
            "required": [
                "decision"
            ]
        }
        verification_task_stage.save()

        verifier_rank = Rank.objects.create(name="verifier")
        RankRecord.objects.create(
            user=self.employee,
            rank=Rank.objects.get(name="Initial"))
        RankRecord.objects.create(
            user=self.user,
            rank=verifier_rank)

        prize_rank = Rank.objects.create(name="SUPERMAN")
        notification = Notification.objects.create(
            title="You achieve new rank",
            text="Congratulations! You achieve new rank!",
            campaign=self.campaign
        )
        task_awards = TaskAward.objects.create(
            task_stage_completion=self.initial_stage,
            task_stage_verified=verification_task_stage,
            rank=prize_rank,
            count=3,
            notification=notification
        )

        rank_l = RankLimit.objects.create(
            rank=verifier_rank,
            stage=verification_task_stage,
            open_limit=5,
            total_limit=0,
            is_creation_open=False,
            is_listing_allowed=True,
            is_selection_open=True,
            is_submission_open=True)

        for i in range(3):
            task = self.create_task(self.initial_stage, self.employee_client)
            task = self.complete_task(task, {"answer": "norm"}, self.employee_client)

        employee_ranks = [i.rank for i in RankRecord.objects.filter(user=self.employee)]
        self.assertEqual(len(employee_ranks), 2)
        self.assertIn(prize_rank, employee_ranks)

        user_notifications = Notification.objects.filter(target_user=self.employee,
                                                         title=task_awards.notification.title)
        self.assertEqual(user_notifications.count(), 1)

