import json

from rest_framework import status
from api.constans import WebhookConstants, TaskStageConstants, TaskStageSchemaSourceConstants
from api.models import Task, Webhook, TaskStage
from api.tests import GigaTurnipTestHelper


class DanceVocabraTest(GigaTurnipTestHelper):


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

    def test_schema_provider_webhook_creatable_task(self):
        # todo: test with long timeout
        data = {
            "type": "SK",
            "system": 1,
            "learner_external_id": "@TURNIP_USER_ID",
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
        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Get on verification",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage
        ))

        data = {
            "type": "SK",
            "system": 1,
            "learner_external_id": "@TURNIP_USER_ID",
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
        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Get on verification",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage
        ))
        data = {
            "type": "SK",
            "system": 1,
            "learner_external_id": "@TURNIP_USER_ID",
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

    def test_schema_provider_webhook_manual_trigger(self):
        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Get on verification",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage
        ))
        data = {
            "type": "SK",
            "system": 1,
            "learner_external_id": "@TURNIP_USER_ID",
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

