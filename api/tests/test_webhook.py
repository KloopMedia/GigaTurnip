import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants, WebhookConstants, ErrorConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class WebhookTest(GigaTurnipTestHelper):

    def test_test_webhook(self):
        task = self.create_initial_task()

        self.initial_stage.json_schema = {"type": "object","required": ["first_term","second_term"],"properties": {"first_term": {"type": "integer","title": "First term"},"second_term": {"type": "integer","title": "Second term"}}}
        self.initial_stage.save()
        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Second",
            x_pos=1,
            y_pos=1,
        ))
        webhook = Webhook.objects.create(
            task_stage=second_stage,
            url='https://us-central1-journal-bb5e3.cloudfunctions.net/for_test_webhook',
        )
        expected_task = Task.objects.create(
            stage_id=second_stage.id,
            responses={'sum': 3}
        )

        responses = {"first_term": 1, "second_term": 2}

        task = self.complete_task(task, responses)
        task2 = task.out_tasks.get()
        self.assertEqual(task2.responses, expected_task.responses)

    def test_conditional_ping_pong_with_shuffle_sentence_webhook(self):
        # first book
        self.initial_stage.json_schema = {"type":"object","properties":{"foo":{"type":"string"}}}
        # second creating task
        task_creation_stage = self.initial_stage.add_stage(
            TaskStage(
                name='Creating task using webhook',
                webhook_address='https://us-central1-journal-bb5e3.cloudfunctions.net/shuffle_sentence',
                webhook_params={"action": "create"}
            )
        )
        # third taks
        completion_stage = task_creation_stage.add_stage(
            TaskStage(
                name='Completion stage',
                json_schema={"type": "object","properties": {"exercise": {"title": "Put the words in the correct order", "type": "string"},"answer": {"type": "string"}}},
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage
            )
        )
        CopyField.objects.create(
            copy_by=CopyFieldConstants.CASE,
            task_stage=completion_stage,
            copy_from_stage=task_creation_stage,
            fields_to_copy='exercise->exercise'
        )
        # fourth ping pong
        conditional_stage = completion_stage.add_stage(
            ConditionalStage(
                name='Conditional ping-pong stage',
                conditions=[{"field": "is_right", "type": "string", "value": "no", "condition": "=="}],
                pingpong=True
            )
        )
        # fifth webhook verification
        verification_webhook_stage = conditional_stage.add_stage(
            TaskStage(
                name='Verification stage using webhook',
                json_schema={"type":"object","properties":{"is_right":{"type":"string"}}},
                webhook_address='https://us-central1-journal-bb5e3.cloudfunctions.net/shuffle_sentence',
                webhook_params={"action": "check"}

            )
        )
        CopyField.objects.create(
            copy_by=CopyFieldConstants.CASE,
            task_stage=verification_webhook_stage,
            copy_from_stage=task_creation_stage,
            fields_to_copy='sentence->sentence'
        )
        # sixth autocomplete task award
        award_stage = verification_webhook_stage.add_stage(
            TaskStage(
                name='Award stage',
                assign_user_by=TaskStageConstants.AUTO_COMPLETE
            )
        )
        award_stage.add_stage(task_creation_stage)

        prize_rank = Rank.objects.create(name="SUPERMAN")
        notification = Notification.objects.create(
            title="You achieve new rank",
            text="Congratulations! You achieve new rank!",
            campaign=self.campaign
        )
        task_awards = TaskAward.objects.create(
            task_stage_completion=completion_stage,
            task_stage_verified=award_stage,
            rank=prize_rank,
            count=5,
            stop_chain=True,
            notification=notification
        )
        notification_good = Notification.objects.create(
            title="Passed",
            text="Accept",
            campaign=self.campaign
        )
        notification_bad = Notification.objects.create(
            title="Fail",
            text="Remake your task",
            campaign=self.campaign
        )

        auto_notification_1 = AutoNotification.objects.create(
            trigger_stage=verification_webhook_stage,
            recipient_stage=self.initial_stage,
            notification=notification_good,
            go=AutoNotificationConstants.FORWARD
        )
        auto_notification_1 = AutoNotification.objects.create(
            trigger_stage=verification_webhook_stage,
            recipient_stage=self.initial_stage,
            notification=notification_bad,
            go=AutoNotificationConstants.BACKWARD

        )

        init_task = self.create_initial_task()
        init_task = self.complete_task(init_task, {"foo": 'hello world'})
        test_task = init_task.out_tasks.get().out_tasks.get()

        for i in range(task_awards.count):
            responses = test_task.responses
            right_answer = test_task.in_tasks.get().responses['sentence']
            responses['answer'] = right_answer[:-1]

            test_task = self.complete_task(test_task, responses)

            self.assertTrue(test_task.reopened)
            self.assertEqual(test_task.out_tasks.count(), 1)

            responses['answer'] = right_answer
            test_task = self.complete_task(test_task, responses)
            if i + 1 < task_awards.count:
                test_task = test_task.out_tasks.get().out_tasks.get().out_tasks.get().out_tasks.get()

        self.assertEqual(self.user.ranks.count(), 2)
        self.assertEqual(init_task.case.tasks.filter(stage=completion_stage).count(), 5)
        all_tasks = init_task.case.tasks.all()
        self.assertEqual(all_tasks.count(), 21)
        self.assertEqual(all_tasks[20].stage, award_stage)
        self.assertEqual(task_awards.count * 2 + 1, self.user.notifications.count())

    def test_error_creating_for_managers(self):
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
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name="Stage with webhook",
                json_schema=self.initial_stage.json_schema,
            )
        )
        Webhook.objects.create(
            task_stage=second_stage,
            url="https://us-central1-journal-bb5e3.cloudfunctions.net/exercise_translate_word",
            is_triggered=True,
        )
        task = self.create_initial_task()
        task = self.complete_task(task, {"answer": "hello world"})
        self.assertEqual(ErrorGroup.objects.count(), 1)
        self.assertEqual(ErrorItem.objects.count(), 1)

        task = self.create_initial_task()
        task = self.complete_task(task, {"answer": "hello world"})
        self.assertEqual(ErrorGroup.objects.count(), 1)
        self.assertEqual(ErrorItem.objects.count(), 2)

        err_campaigns = Campaign.objects.filter(name=ErrorConstants.ERROR_CAMPAIGN)
        self.assertEqual(err_campaigns.count(), 1)
        self.assertEqual(err_campaigns[0].chains.count(), 1)
        err_tasks = Task.objects.filter(stage__chain__campaign=err_campaigns[0])
        self.assertEqual(err_tasks.count(), 2)

    def test_trigger_webhook_endpoint(self):
        js_schema = {
            "type": "object",
            "properties": {
                'answer': {
                    "type": "string",
                }
            }
        }
        self.initial_stage.json_schema = js_schema
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Get on verification",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage,
            json_schema=js_schema
        ))
        Webhook.objects.create(
            task_stage=self.initial_stage,
            url='https://us-central1-journal-bb5e3.cloudfunctions.net/echo_function',
            is_triggered=False,
            which_responses=WebhookConstants.CURRENT_TASK_RESPONSES,
        )
        Webhook.objects.create(
            task_stage=second_stage,
            url='https://us-central1-journal-bb5e3.cloudfunctions.net/echo_function',
            is_triggered=False,
            which_responses=WebhookConstants.IN_RESPONSES,
        )

        task = self.create_initial_task()
        task = self.update_task_responses(task, {"answer": "Hello world!"})

        response = self.get_objects('task-trigger-webhook',  pk=task.pk)
        echo_response = {'echo': {'answer': 'Hello world!'},
                         'answer': 'Hello world!', 'status': 200}
        task = Task.objects.get(id=task.id)
        task = self.complete_task(task, task.responses)
        self.assertEqual(task.responses, echo_response)

        next_task = task.out_tasks.get()
        response = self.get_objects('task-trigger-webhook',  pk=next_task.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({'echo': [echo_response], 'status': 200},
                         Task.objects.get(id=next_task.id).responses)

    def test_webhook_url_injection(self):
        init_task = self.create_initial_task()
        init_task.internal_metadata = {"url_part": "echo_function"}

        init_task.save()

        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Get on verification",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage,
        ))
        Webhook.objects.create(
            task_stage=second_stage,
            url=(
                'https://us-central1-journal-bb5e3.cloudfunctions.net/'
                '{"@TURNIP_INTERNAL_META": {"stage": "in_task", "field": "url_part"}}'
            ),
            is_triggered=False,
            which_responses=WebhookConstants.IN_RESPONSES,
        )

        self.complete_task(init_task)

        next_task = init_task.out_tasks.get()

        response = self.get_objects('task-trigger-webhook', pk=next_task.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
