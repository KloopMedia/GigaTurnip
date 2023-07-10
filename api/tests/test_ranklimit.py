import json

from rest_framework import status
from rest_framework.reverse import reverse

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class RankLimitTest(GigaTurnipTestHelper):

    def test_closed_submission(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "dependencies": {},
            "required": ["answer"]
        })
        self.initial_stage.save()
        task = self.create_initial_task()
        responses = {"answer": "check"}
        updated_task = self.update_task_responses(task, responses)
        self.assertEqual(updated_task.responses, responses)
        client = self.prepare_client(
            task.stage,
            self.user,
            RankLimit(is_submission_open=False))
        task_update_url = reverse("task-detail", kwargs={"pk": task.pk})
        response = client.patch(task_update_url, {"complete": True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

