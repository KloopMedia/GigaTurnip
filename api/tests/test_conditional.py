import json

from rest_framework import status
from rest_framework.reverse import reverse

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class ConditionalTest(GigaTurnipTestHelper):

    def test_conditional_stage_api_creation(self):
        self.user.managed_campaigns.add(self.campaign)
        url = 'conditionalstage-list'

        conditional = {
            'name': 'Checker', 'chain': self.chain.id, 'x_pos': 1, 'y_pos': 1,
            'conditions': []
        }

        response = self.client.post(reverse(url), data=conditional)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        conditional = {
            'name': 'Checker', 'chain': self.chain.id, 'x_pos': 1, 'y_pos': 1,
            'conditions': json.dumps([{"ssf": "world"}])
        }

        response = self.client.post(reverse(url), data=conditional)
        self.assertEqual(response.data['detail'],
                         'Invalid data in 1 index. Please, provide \'type\' field')

        conditional = {
            'name': 'Checker', 'chain': self.chain.id, 'x_pos': 1, 'y_pos': 1,
            'conditions': json.dumps([{"type": "herere"}])
        }

        response = self.client.post(reverse(url), data=conditional)
        self.assertEqual(response.data['detail'],
                         'Invalid data in 1 index. Please, provide valid type')

        conditional = {
            'name': 'Checker', 'chain': self.chain.id, 'x_pos': 1, 'y_pos': 1,
            'conditions': json.dumps([
                {"type": "string", 'value': "something",
                 'field': 'verification', 'condition': '=='}
            ])
        }

        response = self.client.post(reverse(url), data=conditional)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_conditional_stage(self):
        self.user.managed_campaigns.add(self.campaign)
        conditions = [{
            "field": "verified",
            "value": "Нет",
            "condition": "=="
        }]
        conditional_stage = {
            "name": "My Conditional Stage",
            "chain": self.initial_stage.chain.id,
            "x_pos": 1,
            "y_pos": 1,
            "conditions": json.dumps(conditions),
            "pingpong": False,
        }
        response = self.client.post(reverse('conditionalstage-list'),
                                    data=conditional_stage)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'],
                         "Invalid data in 1 index. Please, provide 'type' field")

        conditions[0]['type'] = 'number'
        conditional_stage['conditions'] = json.dumps(conditions)
        response = self.client.post(reverse('conditionalstage-list'),
                                    data=conditional_stage)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'],
                         "Invalid data in 1 index. 'Нет' is not of type 'number'")

        conditions[0]['value'] = 15
        conditional_stage['conditions'] = json.dumps(conditions)
        response = self.client.post(reverse('conditionalstage-list'),
                                    data=conditional_stage)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_conditional_limit_main_logic(self):
        first_schema = {"type": "object", "title": "Поздоровайтесь ",
                        "properties": {
                            "newInput1": {"title": "Hi!", "type": "integer"}},
                        "dependencies": {}, "required": []}
        self.initial_stage.json_schema = json.dumps(first_schema)
        self.initial_stage.save()

        # create conditional stages and limits
        conditional_water = self.initial_stage.add_stage(
            ConditionalStage(
                name='Вопрос воды',
                conditions=[
                    {"type": "integer", "field": "newInput1", "value": 1,
                     "condition": ">"}]
            )
        )
        cond_limit_1 = ConditionalLimit.objects.create(
            conditional_stage=conditional_water,
            order=3
        )

        conditional_gas = self.initial_stage.add_stage(
            ConditionalStage(
                name='Вопрос газа',
                conditions=[
                    {"type": "integer", "field": "newInput1", "value": 1,
                     "condition": ">"}]
            )
        )
        cond_limit_2 = ConditionalLimit.objects.create(
            conditional_stage=conditional_gas,
            order=1
        )

        conditional_cheburek = self.initial_stage.add_stage(
            ConditionalStage(
                name='Вопрос чебуреков',
                conditions=[
                    {"type": "integer", "field": "newInput1", "value": 1,
                     "condition": ">"}]
            )
        )
        cond_limit_3 = ConditionalLimit.objects.create(
            conditional_stage=conditional_cheburek,
            order=2
        )

        # create further stages with questions
        finish_water = conditional_water.add_stage(
            TaskStage(
                name='Цена воды',
                json_schema='{"type":"object","title":"цена воды такая-то"}',
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage
            )
        )
        finish_gas = conditional_gas.add_stage(
            TaskStage(
                name='Цена газа',
                json_schema='{"type":"object","title":"цена газа такая-то"}',
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage
            )
        )
        finish_cheburek = conditional_cheburek.add_stage(
            TaskStage(
                name='Цена чебуреков',
                json_schema='{"type":"object","title":"цена чебуреков такая-то"}',
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage
            )
        )

        responses = {'newInput1': 0}
        initial_task = self.create_initial_task()
        initial_task = self.complete_task(initial_task, responses)
        self.assertEqual(initial_task.out_tasks.count(), 1)
        self.assertEqual(initial_task.out_tasks.get().stage, finish_gas)
        next_task = self.complete_task(initial_task.out_tasks.get())

        initial_task = self.create_initial_task()
        initial_task = self.complete_task(initial_task, responses)
        self.assertEqual(initial_task.out_tasks.count(), 1)
        self.assertEqual(initial_task.out_tasks.get().stage, finish_cheburek)
        next_task = self.complete_task(initial_task.out_tasks.get())

        initial_task = self.create_initial_task()
        initial_task = self.complete_task(initial_task, responses)
        self.assertEqual(initial_task.out_tasks.count(), 1)
        self.assertEqual(initial_task.out_tasks.get().stage, finish_water)
        next_task = self.complete_task(initial_task.out_tasks.get())

        self.assertEqual(Task.objects.filter(assignee=self.user).count(), 6)

    def test_passing_conditional(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "verified": {
                    "enum": ["yes", "no"],
                    "type": "string"}
            },
            "required": ["verified"]
        })
        self.initial_stage.save()

        conditional_stage = self.initial_stage.add_stage(
            ConditionalStage(
                conditions=[
                    {"field": "verified", "type": "string", "value": "yes",
                     "condition": "=="}]
            ))
        last_task_stage = conditional_stage.add_stage(TaskStage())
        initial_task = self.create_initial_task()
        responses = {"verified": "yes"}
        self.complete_task(initial_task, responses)
        new_task = initial_task.case.tasks.get(stage=last_task_stage)
        self.check_task_auto_creation(new_task, last_task_stage, initial_task)

    def test_failing_conditional(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "verified": {
                    "enum": ['yes', 'no'],
                    "type": "string"
                }
            },
            "required": ["verified"]
        })
        self.initial_stage.save()

        conditional_stage = ConditionalStage()
        conditional_stage.conditions = [
            {"field": "verified", "type": "string", "value": "yes",
             "condition": "=="}
        ]
        conditional_stage = self.initial_stage.add_stage(conditional_stage)
        last_task_stage = conditional_stage.add_stage(TaskStage())
        initial_task = self.create_initial_task()
        responses = {"verified": "no"}
        initial_task = self.update_task_responses(initial_task, responses)
        self.complete_task(initial_task, responses)
        new_task = initial_task.case.tasks.filter(
            stage=last_task_stage).exists()
        self.assertFalse(new_task)

    def test_pingpong(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"]
        })
        self.initial_stage.save()

        verification_task_stage = self.initial_stage \
            .add_stage(
            ConditionalStage(
                conditions=[
                    {"field": "verified", "type": "string", "value": "no",
                     "condition": "=="}],
                pingpong=True
            )
        ).add_stage(TaskStage())

        final_task_stage = verification_task_stage.add_stage(TaskStage())
        verification_client = self.prepare_client(verification_task_stage)

        initial_task = self.create_initial_task()
        responses = {"answer": "something"}
        initial_task = self.complete_task(initial_task, responses)

        verification_task = initial_task.out_tasks.get()

        self.request_assignment(verification_task, verification_client)

        verification_task = self.complete_task(
            verification_task,
            responses={"verified": "no"},
            client=verification_client)

        self.assertTrue(verification_task.complete)
        self.assertEqual(len(Task.objects.filter(case=initial_task.case)), 2)
        self.assertEqual(len(Task.objects.filter()), 2)

        initial_task = Task.objects.get(id=initial_task.id)

        self.assertEqual(initial_task.stage, self.initial_stage)
        self.assertFalse(initial_task.complete)
        self.assertFalse(initial_task.force_complete)
        self.assertTrue(initial_task.reopened)
        self.assertIsNone(initial_task.integrator_group)
        self.assertFalse(initial_task.in_tasks.exists())
        self.assertEqual(initial_task.responses, responses)
        self.assertEqual(len(Task.objects.filter(stage=initial_task.stage)), 1)

        initial_task = self.complete_task(initial_task)

        self.assertTrue(initial_task.complete)

        verification_task = Task.objects.get(id=verification_task.id)

        self.assertFalse(verification_task.complete)
        self.assertTrue(verification_task.reopened)
        self.assertEqual(len(Task.objects.filter()), 2)

        verification_task = self.complete_task(verification_task,
                                               responses={"verified": "yes"},
                                               client=verification_client)

        self.assertTrue(verification_task.complete)

        initial_task = Task.objects.get(id=initial_task.id)

        self.assertTrue(initial_task.complete)

        self.assertEqual(len(Task.objects.filter()), 3)
        self.assertEqual(len(Task.objects.filter(case=initial_task.case,
                                                 stage=final_task_stage)), 1)

        final_task = Task.objects.get(case=initial_task.case,
                                      stage=final_task_stage)

        self.assertFalse(final_task.complete)
        self.assertIsNone(final_task.assignee)

    def test_pingpong_first_pass(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"]
        })
        self.initial_stage.save()

        verification_task_stage = self.initial_stage \
            .add_stage(
            ConditionalStage(
                conditions=[
                    {"field": "verified", "type": "string", "value": "no",
                     "condition": "=="}],
                pingpong=True)
        ).add_stage(TaskStage())
        verification_task_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "verified": {
                    "enum": ['yes', 'no'],
                    "type": "string"
                }
            },
            "required": ["verified"]
        })
        verification_task_stage.save()

        final_task_stage = verification_task_stage.add_stage(TaskStage())

        verification_client = self.prepare_client(verification_task_stage)

        initial_task = self.create_initial_task()
        initial_task = self.complete_task(initial_task,
                                          {"answer": "something"})

        verification_task = initial_task.out_tasks.get()
        self.check_task_auto_creation(
            verification_task,
            verification_task_stage,
            initial_task)
        self.request_assignment(verification_task, verification_client)

        verification_task = self.complete_task(
            verification_task,
            {"verified": "yes"},
            verification_client)

        self.assertTrue(verification_task.complete)
        self.assertEqual(len(Task.objects.filter(case=initial_task.case)), 3)
        self.assertEqual(len(Task.objects.filter()), 3)

        initial_task = Task.objects.get(id=initial_task.id)

        self.assertTrue(initial_task.complete)
        self.assertEqual(len(Task.objects.filter()), 3)
        self.assertEqual(len(Task.objects.filter(case=initial_task.case,
                                                 stage=final_task_stage)), 1)

        final_task = Task.objects.get(case=initial_task.case,
                                      stage=final_task_stage)

        self.check_task_auto_creation(
            final_task,
            final_task_stage,
            verification_task)
        self.assertFalse(final_task.assignee)

    def test_conditional_ping_pong_pass(self):
        self.initial_stage.json_schema = '{"type":"object","properties":{"answer":{"type":"string"}}}'
        self.initial_stage.save()

        conditional_stage = self.initial_stage.add_stage(
            ConditionalStage(
                conditions=[{"field": "verified", "type": "string", "value": "no", "condition": "=="}],
                pingpong=True
            )
        )

        verification_task_stage = conditional_stage.add_stage(TaskStage(
            name="Verification task stage",
            json_schema='{"type":"object","properties":{"verified":{"type":"string"}}}'

        ))

        final_task_stage = verification_task_stage.add_stage(TaskStage(
            name="Final task stage",
            assign_user_from_stage=self.initial_stage,
            assign_user_by=TaskStageConstants.STAGE
        ))

        verification_client = self.prepare_client(verification_task_stage)

        initial_task = self.create_initial_task()
        initial_task = self.update_task_responses(initial_task, {"answer": "something"})
        initial_task = self.complete_task(initial_task)

        verification_task = Task.objects \
            .get(stage=verification_task_stage, case=initial_task.case)

        verification_task = self.request_assignment(verification_task, verification_client)

        verification_task = self.complete_task(
            verification_task,
            {"verified": "yes"},
            verification_client)

        initial_task = Task.objects.get(id=initial_task.id)

        self.assertTrue(initial_task.complete)
        self.assertFalse(initial_task.reopened)

        self.assertTrue(verification_task.complete)

        self.assertEqual(Task.objects.count(), 3)

        final_task = Task.objects.get(case=initial_task.case, stage=final_task_stage)

        self.assertEqual(final_task.assignee, self.user)

    def test_conditional_ping_pong_copy_input_if_task_returned_again(self):
        self.initial_stage.json_schema = '{"type":"object","properties":{"answer":{"type":"string"}}}'
        self.initial_stage.save()

        conditional_stage = self.initial_stage.add_stage(
            ConditionalStage(
                conditions=[{"field": "verified", "type": "string", "value": "no", "condition": "=="}],
                pingpong=True
            )
        )

        verification_task_stage = conditional_stage.add_stage(TaskStage(
            name="Verification task stage",
            json_schema='{"type":"object","properties":{"answer":{"type":"string"},"verified":{"type":"string"}}}',
            copy_input=True
        ))

        final_task_stage = verification_task_stage.add_stage(TaskStage(
            name="Final task stage",
            assign_user_from_stage=self.initial_stage,
            assign_user_by=TaskStageConstants.STAGE
        ))

        verification_client = self.prepare_client(verification_task_stage)

        initial_task = self.create_initial_task()
        responses = {"answer": "something"}
        initial_task = self.update_task_responses(initial_task, responses)
        initial_task = self.complete_task(initial_task)

        verification_task = Task.objects \
            .get(stage=verification_task_stage, case=initial_task.case)

        verification_task = self.request_assignment(verification_task, verification_client)

        self.assertEqual(responses, verification_task.responses)

        verification_task.responses['verified'] = 'no'

        verification_task = self.complete_task(
            verification_task,
            verification_task.responses,
            verification_client)

        initial_task = Task.objects.get(id=initial_task.id)

        self.assertTrue(initial_task.reopened)
        self.assertFalse(initial_task.complete)
        self.assertTrue(verification_task.complete)
        self.assertEqual(Task.objects.count(), 2)

        initial_task = self.complete_task(initial_task, {"answer": "something new"})

        verification_task = initial_task.out_tasks.get()

        self.assertEqual(verification_task.responses, {"answer": "something new", "verified": "no"})

        verification_task.responses['verified'] = 'yes'

        verification_task = self.complete_task(
            verification_task,
            verification_task.responses,
            verification_client)

        initial_task = Task.objects.get(id=initial_task.id)

        self.assertTrue(initial_task.complete)
        self.assertTrue(initial_task.reopened)

        self.assertTrue(verification_task.complete)

        self.assertEqual(Task.objects.count(), 3)

        final_task = Task.objects.get(case=initial_task.case, stage=final_task_stage)

        self.assertEqual(final_task.assignee, self.user)

    def test_conditional_ping_pong_doesnt_pass(self):
        self.initial_stage.json_schema = '{"type":"object","properties":{"answer":{"type":"string"}}}'
        self.initial_stage.save()

        conditional_stage = self.initial_stage.add_stage(
            ConditionalStage(
                conditions=[{"field": "verified", "type": "string", "value": "no", "condition": "=="}],
                pingpong=True
            )
        )

        verification_task_stage = conditional_stage.add_stage(TaskStage(
            name="Verification task stage",
            json_schema='{"type":"object","properties":{"answer":{"type":"string"},"verified":{"type":"string"}}}'

        ))

        final_task_stage = verification_task_stage.add_stage(TaskStage(
            name="Final task stage",
            assign_user_from_stage=self.initial_stage,
            assign_user_by=TaskStageConstants.STAGE
        ))

        verification_client = self.prepare_client(verification_task_stage)

        initial_task = self.create_initial_task()
        initial_task = self.complete_task(initial_task, {"answer": "something"})

        verification_task = initial_task.out_tasks.get()

        verification_task = self.request_assignment(verification_task, verification_client)
        verification_task = self.complete_task(
            verification_task,
            {"verified": "no"},
            verification_client)

        initial_task = Task.objects.get(id=initial_task.id)

        self.assertTrue(initial_task.reopened)
        self.assertFalse(initial_task.complete)
        self.assertTrue(verification_task.complete)
        self.assertEqual(Task.objects.count(), 2)

        initial_task = self.complete_task(initial_task, {"answer": "something new"})

        verification_task = initial_task.out_tasks.get()
        verification_task = self.complete_task(
            verification_task,
            {"verified": "yes"},
            verification_client)

        initial_task = Task.objects.get(id=initial_task.id)

        self.assertTrue(initial_task.complete)
        self.assertTrue(initial_task.reopened)
        self.assertTrue(verification_task.complete)
        self.assertEqual(Task.objects.count(), 3)

        final_task = Task.objects.get(case=initial_task.case, stage=final_task_stage)

        self.assertEqual(final_task.assignee, self.user)

    def test_conditional_ping_pong_copy_field_if_task_returned_again(self):
        self.initial_stage.json_schema = '{"type":"object","properties":{"answer":{"type":"string"}}}'
        self.initial_stage.save()

        conditional_stage = self.initial_stage.add_stage(
            ConditionalStage(
                conditions=[{"field": "verified", "type": "string", "value": "no", "condition": "=="}],
                pingpong=True
            )
        )

        verification_task_stage = conditional_stage.add_stage(TaskStage(
            name="Verification task stage",
            json_schema='{"type":"object","properties":{"answerField":{"type":"string"}, "verified":{"enum":["yes", "no"],"type":"string"}}}'
        ))

        final_task_stage = verification_task_stage.add_stage(TaskStage(
            name="Final task stage",
            assign_user_from_stage=self.initial_stage,
            assign_user_by=TaskStageConstants.STAGE
        ))

        CopyField.objects.create(
            copy_by=CopyFieldConstants.CASE,
            task_stage=verification_task_stage,
            copy_from_stage=self.initial_stage,
            fields_to_copy="answer->answerField"
        )
        # returning
        return_notification = Notification.objects.create(
            title='Your task have been returned!',
            campaign=self.campaign
        )
        auto_notification_1 = AutoNotification.objects.create(
            trigger_stage=verification_task_stage,
            recipient_stage=self.initial_stage,
            notification=return_notification,
            go=AutoNotificationConstants.BACKWARD
        )

        complete_notification = Notification.objects.create(
            title='You have been complete task successfully!',
            campaign=self.campaign
        )
        auto_notification_2 = AutoNotification.objects.create(
            trigger_stage=verification_task_stage,
            recipient_stage=self.initial_stage,
            notification=complete_notification,
            go=AutoNotificationConstants.FORWARD
        )

        verification_client = self.prepare_client(verification_task_stage)

        initial_task = self.create_initial_task()
        initial_task = self.complete_task(initial_task, {"answer": "something"})

        verification_task = initial_task.out_tasks.get()
        verification_task = self.request_assignment(verification_task, verification_client)

        self.assertEqual({"answerField": "something"}, verification_task.responses)

        verification_task.responses['verified'] = 'no'

        verification_task = self.complete_task(
            verification_task,
            verification_task.responses,
            verification_client)

        initial_task = Task.objects.get(id=initial_task.id)

        self.assertTrue(initial_task.reopened)
        self.assertFalse(initial_task.complete)
        self.assertTrue(verification_task.complete)
        self.assertEqual(Task.objects.count(), 2)
        user_notifications = Notification.objects.filter(target_user=self.user)
        self.assertEqual(user_notifications.count(), 1)
        self.assertEqual(user_notifications[0].title, return_notification.title)

        initial_task = self.complete_task(initial_task, {"answer": "something new"})

        verification_task = initial_task.out_tasks.get()
        self.assertEqual(verification_task.responses, {"answerField": "something new", "verified": "no"})

        verification_task.responses['verified'] = 'yes'
        verification_task = self.complete_task(
            verification_task,
            verification_task.responses,
            verification_client)

        initial_task = Task.objects.get(id=initial_task.id)

        self.assertTrue(initial_task.complete)
        self.assertTrue(initial_task.reopened)
        self.assertTrue(verification_task.complete)
        self.assertEqual(Task.objects.count(), 3)

        bw_notifications = self.user.notifications.filter(sender_task=verification_task,
                                                          receiver_task=initial_task,
                                                          trigger_go=AutoNotificationConstants.BACKWARD)
        fw_notifications = self.user.notifications.filter(sender_task=verification_task,
                                                          receiver_task=initial_task,
                                                          trigger_go=AutoNotificationConstants.FORWARD)
        self.assertEqual(self.user.notifications.count(), 2)
        self.assertEqual(bw_notifications.count(), 1)
        self.assertEqual(fw_notifications.count(), 1)
        self.assertEqual(bw_notifications[0].title, auto_notification_1.notification.title)
        self.assertEqual(fw_notifications[0].title, auto_notification_2.notification.title)

    def test_forking_chain_with_conditional_happy(self):
        self.initial_stage.json_schema = {"type": "object",
                                          "properties": {"1": {"enum": ["a", "b", "c", "d"], "type": "string"}}}
        self.initial_stage.json_schema = json.dumps(self.initial_stage.json_schema)
        self.initial_stage.save()

        first_cond_stage = self.initial_stage.add_stage(
            ConditionalStage(
                name='If a',
                conditions=[{"field": "1", "type": "string", "value": "a", "condition": "=="}]
            )
        )

        second_cond_stage = self.initial_stage.add_stage(
            ConditionalStage(
                name='If b',
                conditions=[{"field": "1", "type": "string", "value": "b", "condition": "=="}]
            )
        )

        second_stage = first_cond_stage.add_stage(TaskStage(
            name='You have complete task successfully',
            json_schema=self.initial_stage.json_schema,
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage
        ))

        rating_stage = second_cond_stage.add_stage(TaskStage(
            name='Rating stage',
            json_schema=self.initial_stage.json_schema,
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage
        ))

        task = self.create_initial_task()
        responses = {"1": "a"}
        response = self.complete_task(task, responses=responses, whole_response=True)
        task = Task.objects.get(id=response.data["id"])
        self.assertEqual(task.out_tasks.get().id, response.data['next_direct_id'])

    def test_conditional_and_operator(self):
        task_correct_responses = self.create_initial_task()
        correct_responses = {"1": "a", "2": "a", "3": "a", "4": "a", "5": "a"}
        self.initial_stage.json_schema = {
            "type": "object",
            "properties": {
                "1": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 1", "type": "string"
                },
                "2": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 2", "type": "string"
                },
                "3": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 3", "type": "string"
                },
                "4": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 4", "type": "string"
                },
                "5": {
                    "enum": ["a", "b", "c", "d"], "title": "Question 5", "type": "string"
                }
            },
            "dependencies": {},
            "required": ["1", "2", "3", "4", "5"]
        }
        self.initial_stage.json_schema = json.dumps(self.initial_stage.json_schema)
        self.initial_stage.save()
        task_correct_responses = self.complete_task(
            task_correct_responses,
            responses=correct_responses)
        Quiz.objects.create(
            task_stage=self.initial_stage,
            correct_responses_task=task_correct_responses
        )

        conditional_one = self.initial_stage.add_stage(ConditionalStage(
            name='60 <= x <= 90',
            conditions=[
                {"field": Quiz.SCORE, "type": "integer", "value": "60", "condition": "<="},
                {"field": Quiz.SCORE, "type": "integer", "value": "90", "condition": ">="},
            ]
        ))

        final = conditional_one.add_stage(TaskStage(
            name='Final stage',
            assign_user_by=TaskStageConstants.AUTO_COMPLETE,
            json_schema='{}'
        ))

        notification = Notification.objects.create(
            title='Congrats!',
            campaign=self.campaign
        )
        auto_notification = AutoNotification.objects.create(
            trigger_stage=final,
            recipient_stage=self.initial_stage,
            notification=notification,
            go=AutoNotificationConstants.LAST_ONE
        )

        task = self.create_initial_task()
        responses = {"1": "a", "2": "a", "3": "a", "4": "a", "5": "b"}
        task = self.complete_task(task, responses=responses)

        self.assertEqual(task.case.tasks.count(), 2)
        self.assertEqual(Notification.objects.count(), 2)
        self.assertTrue(self.user.notifications.all()[0].sender_task)
        self.assertEqual(self.user.notifications.all()[0].sender_task.stage, final)
        self.assertEqual(self.user.notifications.all()[0].receiver_task.stage, self.initial_stage)
        self.assertEqual(self.user.notifications.all()[0].trigger_go, auto_notification.go)

    def test_return_task_after_conditional(self):
        self.initial_stage.json_schema = json.dumps(
            {"type": "object", "properties": {"answer": {"type": "string"}}}
        )
        self.initial_stage.save()
        # fourth ping pong
        conditional_stage = self.initial_stage.add_stage(
            ConditionalStage(
                name='Conditional ping-pong stage',
                conditions=[
                    {"field": "answer", "type": "string", "value": "pass",
                     "condition": "=="}],
            )
        )

        final = conditional_stage.add_stage(TaskStage(
            name='Final stage',
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage,
            json_schema='{}'
        ))

        task = self.create_initial_task()
        response = self.complete_task(
            task,
            {"answer": "nopass"},
            whole_response=True
        )
        self.assertEqual(json.loads(response.content),
                         {"message": "Task saved.", "id": task.id})
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(self.user.tasks.filter(case=task.case).count(), 1)
        self.assertEqual(self.user.tasks.count(), 1)

        task = self.create_initial_task()
        response = self.complete_task(
            task,
            {"answer": "pass"},
            whole_response=True
        )
        self.assertEqual(json.loads(response.content),
                         {"message": "Next direct task is available.",
                          "id": task.id,
                          "is_new_campaign": False,
                          "next_direct_id": task.out_tasks.get().id})
        self.assertEqual(Task.objects.count(), 3)
        self.assertEqual(self.user.tasks.filter(case=task.case).count(), 2)
        self.assertEqual(self.user.tasks.count(), 3)
