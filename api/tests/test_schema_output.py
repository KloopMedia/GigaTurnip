import json

from rest_framework import status
from api.constans import TaskStageSchemaSourceConstants
from api.tests import GigaTurnipTestHelper


class DanceVocabreTest(GigaTurnipTestHelper):
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
