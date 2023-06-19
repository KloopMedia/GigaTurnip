import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class PreviousManualTest(GigaTurnipTestHelper):

    def test_assign_by_previous_manual_user_without_rank(self):
        js_schema = {
            "type": "object",
            "properties": {
                "email_field": {
                    "type": "string",
                    "title": "email to assign",
                }
            }
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        second_stage_schema = {
            "type": "object",
            "properties": {
                "foo": {
                    "type": "string",
                    "title": "what is ur name",
                }
            }
        }
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name='Second stage',
                assign_user_by=TaskStageConstants.PREVIOUS_MANUAL,
                json_schema=json.dumps(second_stage_schema)
            )
        )

        PreviousManual.objects.create(
            field=["email_field"],
            task_stage_to_assign=second_stage,
            task_stage_email=self.initial_stage,
        )

        responses = {"email_field": "employee@email.com"}
        task = self.create_initial_task()
        bad_response = self.complete_task(task, responses)

        self.assertEqual(bad_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad_response.data['message'], 'User is not in the campaign.')

    def test_assign_by_previous_manual_user_with_rank_of_campaign(self):
        js_schema = {
            "type": "object",
            "properties": {
                "email_field": {
                    "type": "string",
                    "title": "email to assign",
                }
            }
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        second_stage_schema = {
            "type": "object",
            "properties": {
                "foo": {
                    "type": "string",
                    "title": "what is ur name",
                }
            }
        }
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name='Second stage',
                assign_user_by=TaskStageConstants.PREVIOUS_MANUAL,
                json_schema=json.dumps(second_stage_schema)
            )
        )

        PreviousManual.objects.create(
            field=["email_field"],
            task_stage_to_assign=second_stage,
            task_stage_email=self.initial_stage,
        )

        campaign_rank = RankLimit.objects.filter(stage__chain__campaign_id=self.campaign)[0].rank
        self.employee.ranks.add(campaign_rank)

        responses = {"email_field": "employee@email.com"}
        task = self.create_initial_task()
        task = self.complete_task(task, responses)

        new_task = Task.objects.get(stage=second_stage, case=task.case)

        self.assertEqual(new_task.assignee, CustomUser.objects.get(email='employee@email.com'))

    def test_assign_by_previous_manual_conditional_previous_happy(self):
        js_schema = {
            "type": "object",
            "properties": {
                "email_field": {
                    "type": "string",
                    "title": "email to assign",
                },
                'foo': {
                    "type": "string",
                }
            }
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        conditional_stage = self.initial_stage.add_stage(ConditionalStage(
            conditions=[{"field": "foo", "type": "string", "value": "boo", "condition": "=="}]
        ))

        final_stage_schema = {
            "type": "object",
            "properties": {
                "foo": {
                    "type": "string",
                    "title": "what is ur name",
                }
            }
        }
        final_stage = conditional_stage.add_stage(
            TaskStage(
                name='Final stage',
                assign_user_by=TaskStageConstants.PREVIOUS_MANUAL,
                json_schema=json.dumps(final_stage_schema)
            )
        )

        PreviousManual.objects.create(
            field=["email_field"],
            task_stage_to_assign=final_stage,
            task_stage_email=self.initial_stage,
        )

        campaign_rank = RankLimit.objects.filter(stage__chain__campaign_id=self.campaign)[0].rank
        self.employee.ranks.add(campaign_rank)

        responses = {"email_field": "employee@email.com", "foo": "boo"}
        task = self.create_initial_task()
        task = self.complete_task(task, responses)
        new_task = Task.objects.get(stage=final_stage, case=task.case)

        self.assertEqual(new_task.assignee, CustomUser.objects.get(email='employee@email.com'))

    def test_assign_by_previous_manual_conditional_previous_wrong_no_rank(self):
        js_schema = {
            "type": "object",
            "properties": {
                "email_field": {
                    "type": "string",
                    "title": "email to assign",
                },
                'foo': {
                    "type": "string",
                }
            }
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        conditional_stage = self.initial_stage.add_stage(ConditionalStage(
            conditions=[{"field": "foo", "type": "string", "value": "boo", "condition": "=="}]
        ))

        final_stage_schema = {
            "type": "object",
            "properties": {
                "foo": {
                    "type": "string",
                    "title": "what is ur name",
                }
            }
        }
        final_stage = conditional_stage.add_stage(
            TaskStage(
                name='Final stage',
                assign_user_by=TaskStageConstants.PREVIOUS_MANUAL,
                json_schema=json.dumps(final_stage_schema)
            )
        )

        PreviousManual.objects.create(
            field=["email_field"],
            task_stage_to_assign=final_stage,
            task_stage_email=self.initial_stage,
        )

        responses = {"email_field": "employee@email.com", "foo": "boo"}
        task = self.create_initial_task()
        bad_response = self.complete_task(task, responses)

        task = Task.objects.get(id=task.id)

        self.assertEqual(bad_response.data['message'], 'User is not in the campaign.')
        self.assertTrue(task.reopened)
        self.assertFalse(task.complete)
        self.assertEqual(Task.objects.count(), 1)

    def test_assign_by_previous_manual_conditional_previous_wrong_user_does_not_exist(self):
        js_schema = {
            "type": "object",
            "properties": {
                "email_field": {
                    "type": "string",
                    "title": "email to assign",
                },
                'foo': {
                    "type": "string",
                }
            }
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        conditional_stage = self.initial_stage.add_stage(ConditionalStage(
            conditions=[{"field": "foo", "type": "string", "value": "boo", "condition": "=="}]
        ))

        final_stage_schema = {
            "type": "object",
            "properties": {
                "foo": {
                    "type": "string",
                    "title": "what is ur name",
                }
            }
        }
        final_stage = conditional_stage.add_stage(
            TaskStage(
                name='Final stage',
                assign_user_by=TaskStageConstants.PREVIOUS_MANUAL,
                json_schema=json.dumps(final_stage_schema)
            )
        )

        PreviousManual.objects.create(
            field=["email_field"],
            task_stage_to_assign=final_stage,
            task_stage_email=self.initial_stage,
        )

        responses = {"email_field": "employe@email.com", "foo": "boo"}
        task = self.create_initial_task()
        bad_response = self.complete_task(task, responses)

        task = Task.objects.get(id=task.id)

        self.assertEqual(bad_response.data['message'], 'User employe@email.com doesn\'t exist.')
        self.assertTrue(task.reopened)
        self.assertFalse(task.complete)
        self.assertEqual(Task.objects.count(), 1)
