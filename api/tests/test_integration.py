import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class IntegrationTest(GigaTurnipTestHelper):

    def test_integration(self):
        schema = {
            "type": "object",
            "properties": {
                "oik": {"type": "integer"},
                "data": {"type": "string"}}
        }
        self.initial_stage.json_schema = json.dumps(schema)
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(TaskStage())
        Integration.objects.create(
            task_stage=second_stage,
            group_by="oik")
        initial_task1 = self.create_initial_task()
        self.complete_task(initial_task1, responses={"oik": 4, "data": "elkfj"})
        initial_task2 = self.create_initial_task()
        self.complete_task(initial_task2, responses={"oik": 4, "data": "wlfij"})
        initial_task3 = self.create_initial_task()
        self.complete_task(initial_task3, responses={"oik": 4, "data": "sqj"})
        initial_task4 = self.create_initial_task()
        self.complete_task(initial_task4, responses={"oik": 5, "data": "saxha"})
        initial_task5 = self.create_initial_task()
        self.complete_task(initial_task5, responses={"oik": 5, "data": "sodhj"})

        self.assertEqual(Task.objects.filter(stage=second_stage).count(), 2)

        oik_4_integrator = Task.objects.get(integrator_group={"oik": 4})
        oik_5_integrator = Task.objects.get(integrator_group={"oik": 5})

        self.assertEqual(oik_4_integrator.in_tasks.all().count(), 3)
        self.assertEqual(oik_5_integrator.in_tasks.all().count(), 2)

        self.assertIn(initial_task1.id,
                      oik_4_integrator.in_tasks.all().values_list("id", flat=True))
        self.assertIn(initial_task2.id,
                      oik_4_integrator.in_tasks.all().values_list("id", flat=True))
        self.assertIn(initial_task3.id,
                      oik_4_integrator.in_tasks.all().values_list("id", flat=True))

        self.assertIn(initial_task4.id,
                      oik_5_integrator.in_tasks.all().values_list("id", flat=True))
        self.assertIn(initial_task5.id,
                      oik_5_integrator.in_tasks.all().values_list("id", flat=True))
