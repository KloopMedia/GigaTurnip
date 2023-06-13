import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants
from api.models import *
from api.tests import GigaTurnipTestHelper

class CaseTest(GigaTurnipTestHelper):

    def test_case_info_for_map(self):
        json_schema = {
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": ["mon", "tue", "wed", "thu", "fri"]
                },
                "time": {
                    "type": "string",
                    "title": "What time",
                    "enum": ["10:00", "11:00", "12:00", "13:00", "14:00"]
                }
            }
        }
        self.initial_stage.json_schema = json.dumps(json_schema)
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name='Second Task Stage',
                json_schema=self.initial_stage.json_schema,
                assign_user_by='ST',
                assign_user_from_stage=self.initial_stage,
            )
        )

        responses = {"weekday": "mon", "time": "10:00"}
        task = self.create_initial_task()
        self.complete_task(task, responses)

        response = self.get_objects("case-info-by-case", pk=task.case.id)
        maps_info = [
            {'stage': self.initial_stage.id, 'stage__name': self.initial_stage.name, 'complete': [True],
             'force_complete': [False], 'id': [task.id]},
            {'stage': second_stage.id, 'stage__name': second_stage.name, 'complete': [False], 'force_complete': [False],
             'id': [task.out_tasks.get().id]}
        ]

        self.assertEqual(status.HTTP_200_OK, response.data['status'])
        for i in maps_info:
            self.assertIn(i, response.data['info'])
