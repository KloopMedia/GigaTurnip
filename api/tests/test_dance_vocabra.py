import json

from rest_framework import status
from api.constans import WebhookConstants, TaskStageConstants, TaskStageSchemaSourceConstants, CopyFieldConstants, \
    RequestMethodConstants
from api.models import Task, Webhook, TaskStage, CopyField
from api.tests import GigaTurnipTestHelper


class DanceVocabraTest(GigaTurnipTestHelper):

    def test_task_own_schema(self):
        stage_schema = {
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"]
        }
        stage_ui_schema = {"ui:order": ["answer"]}
        task_schema = {
            "type": "object",
            "properties": {
                "answer_to_generated_question": {"type": "string"}
            },
            "required": ["answer"]
        }
        task_ui_schema = {"ui:order": ["answer_to_generated_question"]}

        self.initial_stage.schema_source = TaskStageSchemaSourceConstants.TASK

        self.initial_stage.json_schema = json.dumps(stage_schema)
        self.initial_stage.ui_schema = json.dumps(stage_ui_schema)
        self.initial_stage.save()

        task = self.create_initial_task()
        task.schema = json.dumps(task_schema)
        task.ui_schema = json.dumps(task_ui_schema)
        task.save()

        response = self.get_objects("task-detail", pk=task.pk)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.data["stage"]["json_schema"]),
                         task_schema)
        self.assertEqual(json.loads(response.data["stage"]["ui_schema"]),
                         task_ui_schema)

    def test_task_stage_schema(self):
        stage_schema = {
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"]
        }
        stage_ui_schema = {"ui:order": ["answer"]}
        task_schema = {
            "type": "object",
            "properties": {
                "answer_to_generated_question": {"type": "string"}
            },
            "required": ["answer"]
        }
        task_ui_schema = {"ui:order": ["answer_to_generated_question"]}

        self.initial_stage.json_schema = json.dumps(stage_schema)
        self.initial_stage.ui_schema = json.dumps(stage_ui_schema)
        self.initial_stage.save()

        task = self.create_initial_task()
        task.schema = json.dumps(task_schema)
        task.ui_schema = json.dumps(task_ui_schema)
        task.save()

        response = self.get_objects("task-detail", pk=task.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["stage"]["json_schema"],
                         json.dumps(stage_schema))
        self.assertEqual(response.data["stage"]["ui_schema"],
                         json.dumps(stage_ui_schema))

    def test_schema_provider_webhook_creatable_task(self):
        # return # todo: test with long timeout
        data = {
            "type": "SK",
            "system": 1,
            "learner_external_id": {"@TURNIP_USER_ID": {}},
            "test_language": "EN",
            "native_language": "RU",
            "collection": None,
            "regenerate_stack": False,
            "clear_excluded": False,
            "review": False,
            "stack_size": 10
        }
        headers = {"Authorization": "Token 23bd338120b4116b298c5f25ead64c234bc3ebd9"}

        Webhook.objects.create(
            task_stage=self.initial_stage,
            headers=headers,
            schema_field="questions",
            ui_schema_field="uischema",
            target_responses=False,
            target_schema=True,
            target_ui_schema=True,
            data=data,
            url='http://172.17.0.1:8001/api/v1/answersheet/',
            is_triggered=True,
            which_responses=WebhookConstants.MODIFIER_FIELD,
        )

        task = self.create_initial_task()

        self.assertEqual(task.schema, {'type': 'object', 'properties': {'go': {'type': 'boolean', 'title': 'go'}, 'car': {'type': 'boolean', 'title': 'car'}, 'sun': {'type': 'boolean', 'title': 'sun'}, 'rain': {'type': 'boolean', 'title': 'rain'}, 'road': {'type': 'boolean', 'title': 'road'}, 'snow': {'type': 'boolean', 'title': 'snow'}, 'wind': {'type': 'boolean', 'title': 'wind'}, 'house': {'type': 'boolean', 'title': 'house'}, 'human': {'type': 'boolean', 'title': 'human'}, 'people': {'type': 'boolean', 'title': 'people'}}})
        self.assertEqual(task.ui_schema, {'ui:order': ['car', 'house', 'go', 'people', 'human', 'rain', 'road', 'sun', 'snow', 'wind']})

    def test_schema_provider_webhook_second_task(self):
        # return # todo: test with long timeout
        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Get on verification",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage
        ))

        data = {
            "type": "SK",
            "system": 1,
            "learner_external_id": {"@TURNIP_USER_ID": {}},
            "test_language": "EN",
            "native_language": "RU",
            "collection": None,
            "regenerate_stack": False,
            "clear_excluded": False,
            "review": False,
            "stack_size": 10
        }
        headers = {"Authorization": "Token 23bd338120b4116b298c5f25ead64c234bc3ebd9"}

        Webhook.objects.create(
            task_stage=second_stage,
            headers=headers,
            schema_field="questions",
            ui_schema_field="uischema",
            target_responses=False,
            target_schema=True,
            target_ui_schema=True,
            data=data,
            url='http://172.17.0.1:8001/api/v1/answersheet/',
            is_triggered=True,
            which_responses=WebhookConstants.MODIFIER_FIELD,
        )

        task = self.create_initial_task()
        task = self.complete_task(task)

        task = Task.objects.get(id=task.id)
        next_task = task.out_tasks.get()

        self.assertEqual(next_task.schema, {'type': 'object', 'properties': {'go': {'type': 'boolean', 'title': 'go'}, 'car': {'type': 'boolean', 'title': 'car'}, 'sun': {'type': 'boolean', 'title': 'sun'}, 'rain': {'type': 'boolean', 'title': 'rain'}, 'road': {'type': 'boolean', 'title': 'road'}, 'snow': {'type': 'boolean', 'title': 'snow'}, 'wind': {'type': 'boolean', 'title': 'wind'}, 'house': {'type': 'boolean', 'title': 'house'}, 'human': {'type': 'boolean', 'title': 'human'}, 'people': {'type': 'boolean', 'title': 'people'}}})
        self.assertEqual(next_task.ui_schema, {'ui:order': ['car', 'house', 'go', 'people', 'human', 'rain', 'road', 'sun', 'snow', 'wind']})

    def test_schema_provider_webhook_manual_trigger(self):
        # return # todo: test with long timeout
        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Get on verification",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage
        ))
        data = {
            "type": "SK",
            "system": 1,
            "learner_external_id": {"@TURNIP_USER_ID": {}},
            "test_language": "EN",
            "native_language": "RU",
            "collection": None,
            "regenerate_stack": False,
            "clear_excluded": False,
            "review": False,
            "stack_size": 10
        }
        headers = {"Authorization": "Token 23bd338120b4116b298c5f25ead64c234bc3ebd9"}

        Webhook.objects.create(
            task_stage=self.initial_stage,
            headers=headers,
            schema_field="questions",
            ui_schema_field="uischema",
            internal_meta_field="stack_size",
            target_responses=False,
            target_schema=True,
            target_ui_schema=True,
            target_internal_metadata=True,
            data=data,
            url='http://172.17.0.1:8001/api/v1/answersheet/',
            is_triggered=False,
            which_responses=WebhookConstants.MODIFIER_FIELD,
        )
        Webhook.objects.create(
            task_stage=second_stage,
            headers=headers,
            schema_field="questions",
            ui_schema_field="uischema",
            target_responses=False,
            target_schema=True,
            target_ui_schema=True,
            data=data,
            url='http://172.17.0.1:8001/api/v1/answersheet/',
            is_triggered=False,
            which_responses=WebhookConstants.MODIFIER_FIELD,
        )

        task = self.create_initial_task()

        self.assertIsNone(task.schema)
        self.assertIsNone(task.ui_schema)
        self.get_objects('task-trigger-webhook', pk=task.pk)
        task = Task.objects.get(id=task.id)
        self.assertEqual(task.schema, {
            'type': 'object',
            'properties': {'go': {'type': 'boolean', 'title': 'go'}, 'car': {'type': 'boolean', 'title': 'car'},
                           'sun': {'type': 'boolean', 'title': 'sun'}, 'rain': {'type': 'boolean', 'title': 'rain'},
                           'road': {'type': 'boolean', 'title': 'road'}, 'snow': {'type': 'boolean', 'title': 'snow'},
                           'wind': {'type': 'boolean', 'title': 'wind'}, 'house': {'type': 'boolean', 'title': 'house'},
                           'human': {'type': 'boolean', 'title': 'human'},
                           'people': {'type': 'boolean', 'title': 'people'}}})
        self.assertEqual(task.ui_schema,
                         {'ui:order': ['car', 'house', 'go', 'people', 'human', 'rain', 'road', 'sun', 'snow', 'wind']})
        self.assertEqual(task.internal_metadata["stack_size"], data["stack_size"])

        task = self.complete_task(task)

        next_task = task.out_tasks.get()
        self.assertIsNone(next_task.schema)
        self.assertIsNone(next_task.ui_schema)
        self.get_objects('task-trigger-webhook', pk=next_task.pk)
        next_task = Task.objects.get(id=next_task.id)
        self.assertEqual(next_task.schema, {
            'type': 'object',
            'properties': {'go': {'type': 'boolean', 'title': 'go'}, 'car': {'type': 'boolean', 'title': 'car'},
                           'sun': {'type': 'boolean', 'title': 'sun'}, 'rain': {'type': 'boolean', 'title': 'rain'},
                           'road': {'type': 'boolean', 'title': 'road'}, 'snow': {'type': 'boolean', 'title': 'snow'},
                           'wind': {'type': 'boolean', 'title': 'wind'}, 'house': {'type': 'boolean', 'title': 'house'},
                           'human': {'type': 'boolean', 'title': 'human'},
                           'people': {'type': 'boolean', 'title': 'people'}}})
        self.assertEqual(next_task.ui_schema,
                         {'ui:order': ['car', 'house', 'go', 'people', 'human', 'rain', 'road', 'sun', 'snow', 'wind']})

    def test_individual_chain_update_task(self):
        self.chain.is_individual = True
        self.chain.save()

        self.initial_stage.json_schema = '{"type": "object","properties": {"firstName": {"type": "string"}}}'
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Second Stage",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage,
        ))
        second_stage.json_schema = '{"type": "object","properties": {"lastName": {"type": "string"}}}'
        second_stage.save()

        third_stage = second_stage.add_stage(TaskStage(
            name="Second Stage",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage,
        ))
        third_stage.json_schema = '{"type": "object","properties": {"phoneNumber": {"type": "string"}}}'
        third_stage.save()

        # Adjust copy name in second stage
        CopyField.objects.create(
            copy_by=CopyFieldConstants.CASE,
            task_stage=second_stage,
            copy_from_stage=self.initial_stage,
            fields_to_copy="firstName->firstName")
        CopyField.objects.create(
            copy_by=CopyFieldConstants.CASE,
            task_stage=third_stage,
            copy_from_stage=second_stage,
            fields_to_copy="firstName->firstName lastName->lastName")

        response_1 = {"firstName": "Ivan"}
        task_1 = self.create_task(self.initial_stage)
        task_1 = self.complete_task(task_1, response_1)
        self.check_task_completion(task_1, self.initial_stage, response_1)

        task_2 = task_1.out_tasks.first()
        self.assertFalse(task_2.complete)
        self.assertFalse(task_2.reopened)
        self.assertEqual(task_2.responses, {"firstName": "Ivan"})

        # update first task and watch how it is affect
        task_1 = self.complete_task(task_1, {"firstName": "Mark Bulah"})
        self.assertIsInstance(task_1, Task)
        self.assertEqual(Task.objects.count(), 2)
        self.assertEqual(task_1.out_tasks.first().responses,
                         {"firstName": "Mark Bulah"})

        response_2 = {"firstName": "Mark Bulah", "lastName": "Ivanov"}
        task_2 = self.complete_task(task_2, response_2)
        self.assertTrue(task_2.complete)
        self.assertFalse(task_2.reopened)
        self.assertEqual(task_2.responses, response_2)
        self.assertEqual(Task.objects.count(), 3)

        task_3 = task_2.out_tasks.first()
        self.assertEqual(task_3.responses, {"lastName": "Ivanov", "firstName": "Mark Bulah"})
        self.assertFalse(task_3.complete)
        self.assertFalse(task_3.reopened)

        # update second task
        task_2 = self.complete_task(task_2, {"lastName": "Zubarev"})
        self.assertIsInstance(task_2, Task)
        self.assertEqual(task_2.out_tasks.first().responses,
                         {"firstName": "Mark Bulah", "lastName": "Zubarev"})
        task_3 = task_2.out_tasks.first()
        # self.assertEqual(task_3.responses, {"firstName": "Mark", "lastName": "Ivanov"}) todo: it is may be bug
        response_3 = {"firstName": "Mark Bulah", "lastName": "Zubarev", "phone": 123}
        task_3 = self.complete_task(task_3, response_3)
        self.assertIsInstance(task_3, Task)
        self.assertTrue(task_3.complete)
        self.assertFalse(task_3.reopened)
        self.assertEqual(Task.objects.count(), 3)

    def test_schema_provider_webhook_manual_trigger(self):
        # return # todo: test with long timeout
        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Get on verification",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage
        ))
        data = {
            "type": "SK",
            "system": 1,
            "learner_external_id": {"@TURNIP_USER_ID": {}},
            "test_language": "EN",
            "native_language": "RU",
            "collection": None,
            "regenerate_stack": False,
            "clear_excluded": False,
            "review": False,
            "stack_size": 10
        }
        headers = {"Authorization": "Token 23bd338120b4116b298c5f25ead64c234bc3ebd9"}

        Webhook.objects.create(
            task_stage=self.initial_stage,
            headers=headers,
            schema_field="questions",
            ui_schema_field="uischema",
            internal_meta_field="stack_size",
            target_responses=False,
            target_schema=True,
            target_ui_schema=True,
            target_internal_metadata=True,
            data=data,
            url='http://172.17.0.1:8001/api/v1/answersheet/',
            is_triggered=False,
            which_responses=WebhookConstants.MODIFIER_FIELD,
        )
        Webhook.objects.create(
            task_stage=second_stage,
            headers=headers,
            schema_field="questions",
            ui_schema_field="uischema",
            target_responses=False,
            target_schema=True,
            target_ui_schema=True,
            data=data,
            url='http://172.17.0.1:8001/api/v1/answersheet/',
            is_triggered=False,
            which_responses=WebhookConstants.MODIFIER_FIELD,
        )

        task = self.create_initial_task()

        self.assertIsNone(task.schema)
        self.assertIsNone(task.ui_schema)
        self.get_objects('task-trigger-webhook', pk=task.pk)
        task = Task.objects.get(id=task.id)
        self.assertEqual(task.schema, {
            'type': 'object',
            'properties': {'go': {'type': 'boolean', 'title': 'go'}, 'car': {'type': 'boolean', 'title': 'car'},
                           'sun': {'type': 'boolean', 'title': 'sun'}, 'rain': {'type': 'boolean', 'title': 'rain'},
                           'road': {'type': 'boolean', 'title': 'road'},
                           'snow': {'type': 'boolean', 'title': 'snow'},
                           'wind': {'type': 'boolean', 'title': 'wind'},
                           'house': {'type': 'boolean', 'title': 'house'},
                           'human': {'type': 'boolean', 'title': 'human'},
                           'people': {'type': 'boolean', 'title': 'people'}}})
        self.assertEqual(task.ui_schema,
                         {'ui:order': ['car', 'house', 'go', 'people', 'human', 'rain', 'road', 'sun', 'snow',
                                       'wind']})
        self.assertEqual(task.internal_metadata["stack_size"], data["stack_size"])

        task = self.complete_task(task)

        next_task = task.out_tasks.get()
        self.assertIsNone(next_task.schema)
        self.assertIsNone(next_task.ui_schema)
        self.get_objects('task-trigger-webhook', pk=next_task.pk)
        next_task = Task.objects.get(id=next_task.id)
        self.assertEqual(next_task.schema, {
            'type': 'object',
            'properties': {'go': {'type': 'boolean', 'title': 'go'}, 'car': {'type': 'boolean', 'title': 'car'},
                           'sun': {'type': 'boolean', 'title': 'sun'}, 'rain': {'type': 'boolean', 'title': 'rain'},
                           'road': {'type': 'boolean', 'title': 'road'},
                           'snow': {'type': 'boolean', 'title': 'snow'},
                           'wind': {'type': 'boolean', 'title': 'wind'},
                           'house': {'type': 'boolean', 'title': 'house'},
                           'human': {'type': 'boolean', 'title': 'human'},
                           'people': {'type': 'boolean', 'title': 'people'}}})
        self.assertEqual(next_task.ui_schema,
                         {'ui:order': ['car', 'house', 'go', 'people', 'human', 'rain', 'road', 'sun', 'snow',
                                       'wind']})

    def test_dance_vocabre_integration(self):
        headers = {"Authorization": "Token 23bd338120b4116b298c5f25ead64c234bc3ebd9"}

        data_initial_stage = {
            "type": "SK",
            "system": 1,
            "learner_external_id": {"@TURNIP_USER_ID": {}},
            "test_language": "EN",
            "native_language": "RU",
            "collection": None,
            "regenerate_stack": False,
            "clear_excluded": False,
            "review": False,
            "stack_size": 10
        }

        Webhook.objects.create(
            task_stage=self.initial_stage,
            headers=headers,
            schema_field="questions",
            ui_schema_field="uischema",
            internal_meta_field="id",
            target_responses=False,
            target_schema=True,
            target_ui_schema=True,
            target_internal_metadata=True,
            data=data_initial_stage,
            url='http://172.17.0.1:8001/api/v1/answersheet/',
            is_triggered=True,
            which_responses=WebhookConstants.MODIFIER_FIELD,
        )

        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Submit known selection",
            assign_user_by=TaskStageConstants.AUTO_COMPLETE
        ))

        Webhook.objects.create(
            task_stage=second_stage,
            request_method=RequestMethodConstants.PUT,
            headers=headers,
            internal_meta_field="score",
            target_responses=True,
            response_field="score",
            target_internal_metadata=True,
            data={"learner_answers": {"@TURNIP_RESPONSES": {"stage": "in_task"}}},
            url=(
                'http://172.17.0.1:8001/api/v1/answersheet/'
                '{"@TURNIP_INTERNAL_META": {"stage": "in_task", "field": "id"}}/'
            ),
            is_triggered=True,
            which_responses=WebhookConstants.MODIFIER_FIELD,
        )

        third_stage = second_stage.add_stage(TaskStage(
            name="Select familiar",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage
        ))

        data_third_stage = {
            "type": "SF",
            "system": 1,
            "learner_external_id": {"@TURNIP_USER_ID": {"stage": self.initial_stage.pk}},
            "test_language": "EN",
            "native_language": "RU",
            "collection": None,
            "regenerate_stack": True,
            "clear_excluded": False,
            "review": False,
            "stack_size": 10
        }

        Webhook.objects.create(
            task_stage=third_stage,
            headers=headers,
            schema_field="questions",
            ui_schema_field="uischema",
            internal_meta_field="id",
            target_responses=False,
            target_schema=True,
            target_ui_schema=True,
            target_internal_metadata=True,
            data=data_third_stage,
            url='http://172.17.0.1:8001/api/v1/answersheet/',
            is_triggered=True,
            which_responses=WebhookConstants.MODIFIER_FIELD,
        )

        fourth_stage = third_stage.add_stage(TaskStage(
            name="Submit and check familiar",
            assign_user_by=TaskStageConstants.AUTO_COMPLETE
        ))

        Webhook.objects.create(
            task_stage=fourth_stage,
            request_method=RequestMethodConstants.PUT,
            headers=headers,
            internal_meta_field="score",
            target_responses=True,
            response_field="score",
            target_internal_metadata=True,
            data={"learner_answers": {"@TURNIP_RESPONSES": {"stage": "in_task"}}},
            url=(
                'http://172.17.0.1:8001/api/v1/answersheet/'
                '{"@TURNIP_INTERNAL_META": {"stage": "in_task", "field": "id"}}/'
            ),
            is_triggered=True,
            which_responses=WebhookConstants.MODIFIER_FIELD,
        )

        first_task = self.create_initial_task()
        first_task.responses = {"go": False, "car": False}
        first_task.save()
        self.complete_task(first_task)

        third_task = first_task.out_tasks.get().out_tasks.get()

        third_task.responses = {"go": True}
        third_task.save()
        self.complete_task(third_task)

        fourth_task = third_task.out_tasks.get()

        self.assertEqual(fourth_task.internal_metadata.get("score", None), 50)
        self.assertEqual(fourth_task.responses.get("score", None), 50)

    # def test_task_stage_schema(self):
    #     stage_schema = {
    #         "type": "object",
    #         "properties": {
    #             "answer": {"type": "string"}
    #         },
    #         "required": ["answer"]
    #     }
    #     stage_ui_schema = {"ui:order": ["answer"]}
    #     task_schema = {
    #         "type": "object",
    #         "properties": {
    #             "answer_to_generated_question": {"type": "string"}
    #         },
    #         "required": ["answer"]
    #     }
    #     task_ui_schema = {"ui:order": ["answer_to_generated_question"]}
    #
    #     self.initial_stage.json_schema = json.dumps(stage_schema)
    #     self.initial_stage.ui_schema = json.dumps(stage_ui_schema)
    #     self.initial_stage.save()
    #
    #     task = self.create_initial_task()
    #     task.schema = json.dumps(task_schema)
    #     task.ui_schema = json.dumps(task_ui_schema)
    #     task.save()
    #
    #     response = self.get_objects("task-detail", pk=task.pk)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(response.data["stage"]["json_schema"],
    #                      json.dumps(stage_schema))
    #     self.assertEqual(response.data["stage"]["ui_schema"],
    #                      json.dumps(stage_ui_schema))

    # def test_task_own_schema(self):
    #     # todo: test with long timeout
    #     stage_schema = {
    #         "type": "object",
    #         "properties": {
    #             "answer": {"type": "string"}
    #         },
    #         "required": ["answer"]
    #     }
    #     stage_ui_schema = {"ui:order": ["answer"]}
    #     task_schema = {
    #         "type": "object",
    #         "properties": {
    #             "answer_to_generated_question": {"type": "string"}
    #         },
    #         "required": ["answer"]
    #     }
    #     task_ui_schema = {"ui:order": ["answer_to_generated_question"]}
    #
    #     self.initial_stage.schema_source = TaskStageSchemaSourceConstants.TASK
    #
    #     self.initial_stage.json_schema = json.dumps(stage_schema)
    #     self.initial_stage.ui_schema = json.dumps(stage_ui_schema)
    #     self.initial_stage.save()
    #
    #     task = self.create_initial_task()
    #     task.schema = task_schema
    #     task.ui_schema = task_ui_schema
    #     task.save()
    #
    #     response = self.get_objects("task-detail", pk=task.pk)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(json.loads(response.data["stage"]["json_schema"]),
    #                      task_schema)
    #     self.assertEqual(json.loads(response.data["stage"]["ui_schema"]),
    #                      task_ui_schema)

    # def test_schema_provider_webhook_creatable_task(self):
    #     # todo: test with long timeout
    #     data = {
    #         "type": "SK",
    #         "system": 1,
    #         "learner_external_id": "@TURNIP_USER_ID",
    #         "test_language": "EN",
    #         "native_language": "RU",
    #         "collection": None,
    #         "regenerate_stack": False,
    #         "clear_excluded": False,
    #         "review": False,
    #         "stack_size": 10
    #     }
    #     headers = {"Authorization": "Token 23bd338120b4116b298c5f25ead64c234bc3ebd9"}
    #
    #     Webhook.objects.create(
    #         task_stage=self.initial_stage,
    #         headers=headers,
    #         schema_field="questions",
    #         ui_schema_field="uischema",
    #         target_responses=False,
    #         target_schema=True,
    #         target_ui_schema=True,
    #         data=data,
    #         url='http://172.17.0.1:8001/api/v1/answersheet/',
    #         is_triggered=True,
    #         which_responses=WebhookConstants.MODIFIER_FIELD,
    #     )
    #
    #     task = self.create_initial_task()
    #
    #     self.assertEqual(task.schema, {'type': 'object', 'properties': {'go': {'type': 'boolean', 'title': 'go'}, 'car': {'type': 'boolean', 'title': 'car'}, 'sun': {'type': 'boolean', 'title': 'sun'}, 'rain': {'type': 'boolean', 'title': 'rain'}, 'road': {'type': 'boolean', 'title': 'road'}, 'snow': {'type': 'boolean', 'title': 'snow'}, 'wind': {'type': 'boolean', 'title': 'wind'}, 'house': {'type': 'boolean', 'title': 'house'}, 'human': {'type': 'boolean', 'title': 'human'}, 'people': {'type': 'boolean', 'title': 'people'}}})
    #     self.assertEqual(task.ui_schema, {'ui:order': ['car', 'house', 'go', 'people', 'human', 'rain', 'road', 'sun', 'snow', 'wind']})
    #
    # def test_schema_provider_webhook_second_task(self):
    #     second_stage = self.initial_stage.add_stage(TaskStage(
    #         name="Get on verification",
    #         assign_user_by=TaskStageConstants.STAGE,
    #         assign_user_from_stage=self.initial_stage
    #     ))
    #
    #     data = {
    #         "type": "SK",
    #         "system": 1,
    #         "learner_external_id": "@TURNIP_USER_ID",
    #         "test_language": "EN",
    #         "native_language": "RU",
    #         "collection": None,
    #         "regenerate_stack": False,
    #         "clear_excluded": False,
    #         "review": False,
    #         "stack_size": 10
    #     }
    #     headers = {"Authorization": "Token 23bd338120b4116b298c5f25ead64c234bc3ebd9"}
    #
    #     Webhook.objects.create(
    #         task_stage=second_stage,
    #         headers=headers,
    #         schema_field="questions",
    #         ui_schema_field="uischema",
    #         target_responses=False,
    #         target_schema=True,
    #         target_ui_schema=True,
    #         data=data,
    #         url='http://172.17.0.1:8001/api/v1/answersheet/',
    #         is_triggered=True,
    #         which_responses=WebhookConstants.MODIFIER_FIELD,
    #     )
    #
    #     task = self.create_initial_task()
    #     task = self.complete_task(task)
    #
    #     task = Task.objects.get(id=task.id)
    #     next_task = task.out_tasks.get()
    #
    #     self.assertEqual(next_task.schema, {'type': 'object', 'properties': {'go': {'type': 'boolean', 'title': 'go'}, 'car': {'type': 'boolean', 'title': 'car'}, 'sun': {'type': 'boolean', 'title': 'sun'}, 'rain': {'type': 'boolean', 'title': 'rain'}, 'road': {'type': 'boolean', 'title': 'road'}, 'snow': {'type': 'boolean', 'title': 'snow'}, 'wind': {'type': 'boolean', 'title': 'wind'}, 'house': {'type': 'boolean', 'title': 'house'}, 'human': {'type': 'boolean', 'title': 'human'}, 'people': {'type': 'boolean', 'title': 'people'}}})
    #     self.assertEqual(next_task.ui_schema, {'ui:order': ['car', 'house', 'go', 'people', 'human', 'rain', 'road', 'sun', 'snow', 'wind']})
    #
    # def test_schema_provider_webhook_manual_trigger(self):
    #     second_stage = self.initial_stage.add_stage(TaskStage(
    #         name="Get on verification",
    #         assign_user_by=TaskStageConstants.STAGE,
    #         assign_user_from_stage=self.initial_stage
    #     ))
    #     data = {
    #         "type": "SK",
    #         "system": 1,
    #         "learner_external_id": "@TURNIP_USER_ID",
    #         "test_language": "EN",
    #         "native_language": "RU",
    #         "collection": None,
    #         "regenerate_stack": False,
    #         "clear_excluded": False,
    #         "review": False,
    #         "stack_size": 10
    #     }
    #     headers = {"Authorization": "Token 23bd338120b4116b298c5f25ead64c234bc3ebd9"}
    #
    #     Webhook.objects.create(
    #         task_stage=self.initial_stage,
    #         headers=headers,
    #         schema_field="questions",
    #         ui_schema_field="uischema",
    #         internal_meta_field="stack_size",
    #         target_responses=False,
    #         target_schema=True,
    #         target_ui_schema=True,
    #         target_internal_metadata=True,
    #         data=data,
    #         url='http://172.17.0.1:8001/api/v1/answersheet/',
    #         is_triggered=False,
    #         which_responses=WebhookConstants.MODIFIER_FIELD,
    #     )
    #     Webhook.objects.create(
    #         task_stage=second_stage,
    #         headers=headers,
    #         schema_field="questions",
    #         ui_schema_field="uischema",
    #         target_responses=False,
    #         target_schema=True,
    #         target_ui_schema=True,
    #         data=data,
    #         url='http://172.17.0.1:8001/api/v1/answersheet/',
    #         is_triggered=False,
    #         which_responses=WebhookConstants.MODIFIER_FIELD,
    #     )
    #
    #     task = self.create_initial_task()
    #
    #     self.assertIsNone(task.schema)
    #     self.assertIsNone(task.ui_schema)
    #     self.get_objects('task-trigger-webhook', pk=task.pk)
    #     task = Task.objects.get(id=task.id)
    #     self.assertEqual(task.schema, {
    #         'type': 'object',
    #         'properties': {'go': {'type': 'boolean', 'title': 'go'}, 'car': {'type': 'boolean', 'title': 'car'},
    #                        'sun': {'type': 'boolean', 'title': 'sun'}, 'rain': {'type': 'boolean', 'title': 'rain'},
    #                        'road': {'type': 'boolean', 'title': 'road'}, 'snow': {'type': 'boolean', 'title': 'snow'},
    #                        'wind': {'type': 'boolean', 'title': 'wind'}, 'house': {'type': 'boolean', 'title': 'house'},
    #                        'human': {'type': 'boolean', 'title': 'human'},
    #                        'people': {'type': 'boolean', 'title': 'people'}}})
    #     self.assertEqual(task.ui_schema,
    #                      {'ui:order': ['car', 'house', 'go', 'people', 'human', 'rain', 'road', 'sun', 'snow', 'wind']})
    #     self.assertEqual(task.internal_metadata["stack_size"], data["stack_size"])
    #
    #     task = self.complete_task(task)
    #
    #     next_task = task.out_tasks.get()
    #     self.assertIsNone(next_task.schema)
    #     self.assertIsNone(next_task.ui_schema)
    #     self.get_objects('task-trigger-webhook', pk=next_task.pk)
    #     next_task = Task.objects.get(id=next_task.id)
    #     self.assertEqual(next_task.schema, {
    #         'type': 'object',
    #         'properties': {'go': {'type': 'boolean', 'title': 'go'}, 'car': {'type': 'boolean', 'title': 'car'},
    #                        'sun': {'type': 'boolean', 'title': 'sun'}, 'rain': {'type': 'boolean', 'title': 'rain'},
    #                        'road': {'type': 'boolean', 'title': 'road'}, 'snow': {'type': 'boolean', 'title': 'snow'},
    #                        'wind': {'type': 'boolean', 'title': 'wind'}, 'house': {'type': 'boolean', 'title': 'house'},
    #                        'human': {'type': 'boolean', 'title': 'human'},
    #                        'people': {'type': 'boolean', 'title': 'people'}}})
    #     self.assertEqual(next_task.ui_schema,
    #                      {'ui:order': ['car', 'house', 'go', 'people', 'human', 'rain', 'road', 'sun', 'snow', 'wind']})
    #
    # def test_schema_provider_webhook_manual_trigger(self):
    #     second_stage = self.initial_stage.add_stage(TaskStage(
    #         name="Get on verification",
    #         assign_user_by=TaskStageConstants.STAGE,
    #         assign_user_from_stage=self.initial_stage
    #     ))
    #     data = {
    #         "type": "SK",
    #         "system": 1,
    #         "learner_external_id": "@TURNIP_USER_ID",
    #         "test_language": "EN",
    #         "native_language": "RU",
    #         "collection": None,
    #         "regenerate_stack": False,
    #         "clear_excluded": False,
    #         "review": False,
    #         "stack_size": 10
    #     }
    #     headers = {"Authorization": "Token 23bd338120b4116b298c5f25ead64c234bc3ebd9"}
    #
    #     Webhook.objects.create(
    #         task_stage=self.initial_stage,
    #         headers=headers,
    #         schema_field="questions",
    #         ui_schema_field="uischema",
    #         internal_meta_field="stack_size",
    #         target_responses=False,
    #         target_schema=True,
    #         target_ui_schema=True,
    #         target_internal_metadata=True,
    #         data=data,
    #         url='http://172.17.0.1:8001/api/v1/answersheet/',
    #         is_triggered=False,
    #         which_responses=WebhookConstants.MODIFIER_FIELD,
    #     )
    #     Webhook.objects.create(
    #         task_stage=second_stage,
    #         headers=headers,
    #         schema_field="questions",
    #         ui_schema_field="uischema",
    #         target_responses=False,
    #         target_schema=True,
    #         target_ui_schema=True,
    #         data=data,
    #         url='http://172.17.0.1:8001/api/v1/answersheet/',
    #         is_triggered=False,
    #         which_responses=WebhookConstants.MODIFIER_FIELD,
    #     )
    #
    #     task = self.create_initial_task()
    #
    #     self.assertIsNone(task.schema)
    #     self.assertIsNone(task.ui_schema)
    #     self.get_objects('task-trigger-webhook', pk=task.pk)
    #     task = Task.objects.get(id=task.id)
    #     self.assertEqual(task.schema, {
    #         'type': 'object',
    #         'properties': {'go': {'type': 'boolean', 'title': 'go'}, 'car': {'type': 'boolean', 'title': 'car'},
    #                        'sun': {'type': 'boolean', 'title': 'sun'}, 'rain': {'type': 'boolean', 'title': 'rain'},
    #                        'road': {'type': 'boolean', 'title': 'road'}, 'snow': {'type': 'boolean', 'title': 'snow'},
    #                        'wind': {'type': 'boolean', 'title': 'wind'}, 'house': {'type': 'boolean', 'title': 'house'},
    #                        'human': {'type': 'boolean', 'title': 'human'},
    #                        'people': {'type': 'boolean', 'title': 'people'}}})
    #     self.assertEqual(task.ui_schema,
    #                      {'ui:order': ['car', 'house', 'go', 'people', 'human', 'rain', 'road', 'sun', 'snow', 'wind']})
    #     self.assertEqual(task.internal_metadata["stack_size"], data["stack_size"])
    #
    #     task = self.complete_task(task)
    #
    #     next_task = task.out_tasks.get()
    #     self.assertIsNone(next_task.schema)
    #     self.assertIsNone(next_task.ui_schema)
    #     self.get_objects('task-trigger-webhook', pk=next_task.pk)
    #     next_task = Task.objects.get(id=next_task.id)
    #     self.assertEqual(next_task.schema, {
    #         'type': 'object',
    #         'properties': {'go': {'type': 'boolean', 'title': 'go'}, 'car': {'type': 'boolean', 'title': 'car'},
    #                        'sun': {'type': 'boolean', 'title': 'sun'}, 'rain': {'type': 'boolean', 'title': 'rain'},
    #                        'road': {'type': 'boolean', 'title': 'road'}, 'snow': {'type': 'boolean', 'title': 'snow'},
    #                        'wind': {'type': 'boolean', 'title': 'wind'}, 'house': {'type': 'boolean', 'title': 'house'},
    #                        'human': {'type': 'boolean', 'title': 'human'},
    #                        'people': {'type': 'boolean', 'title': 'people'}}})
    #     self.assertEqual(next_task.ui_schema,
    #                      {'ui:order': ['car', 'house', 'go', 'people', 'human', 'rain', 'road', 'sun', 'snow', 'wind']})
    #
