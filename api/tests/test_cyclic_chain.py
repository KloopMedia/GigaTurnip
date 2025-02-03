import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class CyclicChainTest(GigaTurnipTestHelper):

    def create_cyclic_chain(self):
        js_schema = {
            "type": "object",
            "properties": {
                'name': {
                    "type": "string",
                }
            }
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        second_stage_schema = {
            "type": "object",
            "properties": {
                'foo': {
                    "type": "string",
                }
            }
        }

        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name="Test pronunciation",
                json_schema=json.dumps(second_stage_schema),
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage
            )
        )

        conditional_stage = second_stage.add_stage(ConditionalStage(
            conditions=[{"field": "foo", "type": "string", "value": "boo", "condition": "=="}]
        ))

        conditional_stage_cyclic = second_stage.add_stage(ConditionalStage(
            conditions=[{"field": "foo", "type": "string", "value": "boo", "condition": "!="}]
        ))

        final_stage_schema = {
            "type": "object",
            "properties": {
                "too": {
                    "type": "string",
                    "title": "what is ur name",
                }
            }
        }

        final_stage = conditional_stage.add_stage(
            TaskStage(
                name='Final stage',
                assign_user_by=TaskStageConstants.STAGE,
                json_schema=json.dumps(final_stage_schema)
            )
        )

        conditional_stage_cyclic.out_stages.add(second_stage)
        conditional_stage_cyclic.save()

        return second_stage, conditional_stage, conditional_stage_cyclic, final_stage

    # def test_cyclic_chain_ST(self):
    #     second_stage, conditional_stage, conditional_stage_cyclic, final_stage = self.create_cyclic_chain()

    #     task = self.create_initial_task()
    #     task = self.complete_task(task, {"name": "Kloop"})

    #     second_task_1 = task.out_tasks.get()
    #     second_task_1 = self.complete_task(second_task_1, {"foo": "not right"})
    #     self.assertEqual(Task.objects.filter(case=task.case).count(), 3)
    #     self.assertEqual(Task.objects.filter(case=task.case, stage=second_stage).count(), 2)

    #     second_task_2 = second_task_1.out_tasks.get()

    #     response = self.get_objects('case-info-by-case', pk=task.case.id)
    #     info_by_case = [
    #         {'stage': self.initial_stage.id, 'stage__name': 'Initial', 'complete': [True], 'force_complete': [False],
    #          'id': [task.id]},
    #         {'stage': second_stage.id, 'stage__name': 'Test pronunciation', 'complete': [False, True],
    #          'force_complete': [False, False],
    #          'id': [second_task_2.id, second_task_1.id]}
    #     ]
    #     self.assertEqual(len(response.data['info']), 2)
    #     for i in info_by_case:
    #         self.assertIn(i, response.data['info'])

    #     second_task_2 = self.complete_task(second_task_2, {"foo": "boo"})
    #     self.assertEqual(Task.objects.filter(case=task.case).count(), 4)
    #     self.assertEqual(Task.objects.filter(case=task.case, stage=second_stage).count(), 2)
    #     self.assertEqual(Task.objects.filter(case=task.case, stage=final_stage).count(), 1)

    def test_cyclic_chain_RA(self):
        js_schema = {
            "type": "object",
            "properties": {
                'name': {
                    "type": "string",
                }
            }
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        second_stage_schema = {
            "type": "object",
            "properties": {
                'foo': {
                    "type": "string",
                }
            }
        }

        verifier_rank = Rank.objects.create(name="test pronounce")
        RankRecord.objects.create(
            user=self.user,
            rank=verifier_rank)

        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name="Test pronunciation",
                json_schema=json.dumps(second_stage_schema),
                assign_user_by=TaskStageConstants.RANK,
            )
        )
        rank_l = RankLimit.objects.create(
            rank=verifier_rank,
            stage=second_stage,
            open_limit=0,
            total_limit=0,
            is_creation_open=False,
            is_listing_allowed=True,
            is_selection_open=True,
            is_submission_open=True)

        conditional_stage = second_stage.add_stage(ConditionalStage(
            conditions=[{"field": "foo", "type": "string", "value": "boo", "condition": "=="}]
        ))

        conditional_stage_cyclic = second_stage.add_stage(ConditionalStage(
            conditions=[{"field": "foo", "type": "string", "value": "boo", "condition": "!="}]
        ))

        final_stage_schema = {
            "type": "object",
            "properties": {
                "too": {
                    "type": "string",
                    "title": "what is ur name",
                }
            }
        }

        final_stage = conditional_stage.add_stage(
            TaskStage(
                name='Final stage',
                assign_user_by=TaskStageConstants.STAGE,
                json_schema=json.dumps(final_stage_schema)
            )
        )

        conditional_stage_cyclic.out_stages.add(second_stage)
        conditional_stage_cyclic.save()

        task = self.create_initial_task()
        task = self.complete_task(task, {"name": "Kloop"})

        response_assign = self.get_objects('task-request-assignment', pk=task.out_tasks.get().id)
        self.assertEqual(response_assign.status_code, status.HTTP_200_OK)

        second_task_1 = task.out_tasks.get()
        second_task_1 = self.complete_task(second_task_1, {"foo": "not right"})
        self.assertEqual(Task.objects.filter(case=task.case).count(), 3)
        self.assertEqual(Task.objects.filter(case=task.case, stage=second_stage).count(), 2)

        response_assign = self.get_objects('task-request-assignment', pk=second_task_1.out_tasks.get().id)
        self.assertEqual(response_assign.status_code, status.HTTP_200_OK)

        second_task_2 = second_task_1.out_tasks.get()
        second_task_2 = self.complete_task(second_task_2, {"foo": "boo"})
        self.assertEqual(Task.objects.filter(case=task.case).count(), 4)
        self.assertEqual(Task.objects.filter(case=task.case, stage=second_stage).count(), 2)
        self.assertEqual(Task.objects.filter(case=task.case, stage=final_stage).count(), 1)

    def test_conditional_ping_pong_cyclic_chain(self):
        # first book
        self.initial_stage.json_schema = '{"type":"object","properties":{"foo":{"type":"string"}}}'
        # second creating task
        task_creation_stage = self.initial_stage.add_stage(
            TaskStage(
                name='Creating task using webhook',
                webhook_address='https://us-central1-journal-bb5e3.cloudfunctions.net/random_int_between_0_9',
                webhook_params={"action": "create"}
            )
        )
        # third taks
        completion_stage = task_creation_stage.add_stage(
            TaskStage(
                name='Completion stage',
                json_schema='{"type": "object","properties": {"expression": {"title": "Expression", "type": "string"},"answer": {"type": "integer"}}}',
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage,
                copy_input=True
            )
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
                json_schema='{"type":"object","properties":{"is_right":{"type":"string"}}}',
                webhook_address='https://us-central1-journal-bb5e3.cloudfunctions.net/random_int_between_0_9',
                copy_input=True,
                webhook_params={"action": "check"}

            )
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

        init_task = self.create_initial_task()
        init_task = self.complete_task(init_task, {"foo": 'hello world'})
        test_task = init_task.out_tasks.get().out_tasks.get()

        for i in range(task_awards.count):
            expression = test_task.responses['expression'].split(' ')
            sum_of_expression = int(expression[0]) + int(expression[2])
            responses = test_task.responses
            responses['answer'] = sum_of_expression

            test_task = self.complete_task(test_task, responses)
            if i + 1 < task_awards.count:
                test_task = test_task.out_tasks.get().out_tasks.get().out_tasks.get().out_tasks.get()

        self.assertEqual(self.user.ranks.count(), 2)
        self.assertEqual(init_task.case.tasks.filter(stage=completion_stage).count(), 5)
        all_tasks = init_task.case.tasks.all()
        self.assertEqual(all_tasks.count(), 21)
        # self.assertEqual(all_tasks[20].stage, award_stage)
