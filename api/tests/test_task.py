import json

from rest_framework import status
from rest_framework.reverse import reverse

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class TaskTest(GigaTurnipTestHelper):

    def test_answers_validation(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "price": {"type": "number"},
                "year": {"type": "number"},
                "name": {"type": "string"},
            },
            "required": ['price', 'name']
        })
        self.initial_stage.save()

        task = self.create_initial_task()
        response = self.complete_task(task, {'price': 'there must be digit',
                                             'year': 'there must be digit',
                                             'name': 'Kloop'}
                                      )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(json.loads(response.content)['pass'], ["properties", "price", "type"])

    def test_public_task(self):
        self.initial_stage.is_public = True
        self.initial_stage.json_schema = json.dumps({
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
        })
        self.initial_stage.save()

        task = self.create_initial_task()
        task = self.complete_task(task, {"answer": "My answer"})
        self.assertTrue(task.complete)

        response = self.get_objects("task-detail", pk=task.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["responses"], task.responses)
        self.assertEqual(response.data["stage"]["id"], self.initial_stage.id)
        self.assertIn("json_schema", response.data["stage"].keys())
        self.assertIn("ui_schema", response.data["stage"].keys())

    def test_initial_task_creation(self):
        task = self.create_initial_task()
        self.check_task_manual_creation(task, self.initial_stage)

    def test_initial_task_completion(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"]
        })
        self.initial_stage.save()
        task = self.create_initial_task()
        responses = {"answer": "check"}
        task = self.complete_task(task, responses=responses)

        self.check_task_completion(task, self.initial_stage, responses)

    def test_initial_task_update_and_completion(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"]
        })
        self.initial_stage.save()
        task = self.create_initial_task()
        responses = {"answer": "check"}
        updated_task = self.update_task_responses(task, responses)
        self.assertEqual(updated_task.responses, responses)
        new_responses = {"answer": "check check"}
        completed_task = self.complete_task(task, new_responses)
        self.check_task_completion(
            completed_task,
            self.initial_stage,
            new_responses)

    def test_initial_task_update_and_completion_no_responses(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"]
        })
        self.initial_stage.save()
        task = self.create_initial_task()
        responses = {"answer": "check"}
        updated_task = self.update_task_responses(task, responses)
        self.assertEqual(updated_task.responses, responses)
        completed_task = self.complete_task(task)
        self.check_task_completion(
            completed_task,
            self.initial_stage,
            responses)

    def test_get_tasks_selectable(self):
        second_stage = self.initial_stage.add_stage(TaskStage())
        self.client = self.prepare_client(second_stage, self.user)
        task_1 = self.create_initial_task()
        task_1 = self.complete_task(task_1)
        task_2 = task_1.out_tasks.all()[0]
        response = self.get_objects("task-user-selectable")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], task_2.id)

    def test_get_user_activity_csv_fail(self):
        self.create_initial_tasks(5)
        response = self.client.get(reverse('task-user-activity-csv') + "?csv=22")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_activity_on_stages(self):
        tasks = self.create_initial_tasks(5)
        self.user.managed_campaigns.add(self.campaign)

        ranks = [i['id'] for i in self.initial_stage.ranks.all().values('id')]
        in_stages = [i['id'] for i in
                     self.initial_stage.in_stages.all().values('id')]
        out_stages = [i['id'] for i in
                      self.initial_stage.out_stages.all().values('id')]
        # todo: add field 'users' to remove bug
        expected_activity = {
            'stage': self.initial_stage.id,
            'stage_name': self.initial_stage.name,
            'chain': self.initial_stage.chain.id,
            'chain_name': self.initial_stage.chain.name,
            'ranks': ranks or [None],
            'in_stages': in_stages or [None],
            'out_stages': out_stages or [None],
            'complete_true': 3,
            'complete_false': 2,
            'force_complete_false': 5,
            'force_complete_true': 0,
            'count_tasks': 5
        }

        if not expected_activity['in_stages']:
            expected_activity['in_stages'] = [None]
        if not expected_activity['out_stages']:
            expected_activity['out_stages'] = [None]

        for t in tasks[:3]:
            t.complete = True
            t.save()
        response = self.get_objects('task-user-activity')
        # Will Fail if your database isn't postgres. because of dj.func ArrayAgg. Make sure that your DB is PostgreSql
        self.assertEqual(
            json.loads(response.content)['results'], [expected_activity]
        )

    def test_timer_for_tasks(self):
        second_stage = self.initial_stage.add_stage(TaskStage(
            assign_user_by="RA"
        ))
        verifier_rank = Rank.objects.create(name="verifier")
        RankRecord.objects.create(
            user=self.employee,
            rank=verifier_rank)
        RankLimit.objects.create(
            rank=verifier_rank,
            stage=second_stage,
            open_limit=5,
            total_limit=0,
            is_creation_open=False,
            is_listing_allowed=True,
            is_selection_open=True,
            is_submission_open=True
        )
        DatetimeSort.objects.create(
            stage=second_stage,
            how_much=2,
            after_how_much=0.1
        )
        task1 = self.create_initial_task()
        task1 = self.complete_task(task1)
        task1.out_tasks.get()

        response = self.get_objects('task-user-selectable', client=self.employee_client)
        content = json.loads(response.content)
        self.assertEqual(len(content['results']), 0)

    def test_get_next_task_after_autocomplete_stage(self):
        self.initial_stage.json_schema = json.dumps(
            {"type": "object", "properties": {"answer": {"type": "string"}}}
        )
        self.initial_stage.save()
        # fourth ping pong
        autocomplete_stage = self.initial_stage.add_stage(
            TaskStage(
                name='Autocomplete',
                assign_user_by=TaskStageConstants.AUTO_COMPLETE
            )
        )

        final = autocomplete_stage.add_stage(TaskStage(
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
                         {"message": "Next direct task is available.",
                          "id": task.id,
                          "is_new_campaign": False,
                          "next_direct_id": task.id+2})

    def test_post_json_filter_json_fields(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "name": {
                    "type": "string"
                },
                "age": {
                    "type": "integer"
                }
            }
        })
        self.initial_stage.ui_schema = '{"ui:order": ["name", "age"]}'
        self.initial_stage.save()
        second_stage = self.initial_stage.add_stage(TaskStage())
        self.client = self.prepare_client(second_stage, self.user)

        tasks = self.create_initial_tasks(5)
        names = ['Artur', 'Karim', 'Atai', 'Xakim', 'Rinat']

        i = 1
        for t, n in zip(tasks, names):
            self.complete_task(t, {"name": n, "age": 10 * i})
            i += 1

        post_data = {
            "items_conditions": [
                {
                    "conditions": [
                        {
                            "operator": "<=",
                            "value": "20"
                        }
                    ],
                    "field": "age",
                    "type": "integer"
                },
            ],
            "stage": self.initial_stage.id,
            "search_stage": second_stage.id

        }

        response = self.client.post(reverse("task-user-selectable") + '?responses_filter_values=Yes', data=post_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)

        post_data = {
            "items_conditions": [
                {
                    "conditions": [
                        {
                            "operator": "<",
                            "value": "20"
                        }
                    ],
                    "field": "age",
                    "type": "integer"
                },
            ],
            "stage": self.initial_stage.id,
            "search_stage": second_stage.id

        }

        response = self.client.post(reverse("task-user-selectable") + '?responses_filter_values=Yes', data=post_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

        post_data = {
            "items_conditions": [
                {
                    "conditions": [
                        {
                            "operator": "<=",
                            "value": "50"
                        }
                    ],
                    "field": "age",
                    "type": "integer"
                },
            ],
            "stage": self.initial_stage.id,
            "search_stage": second_stage.id

        }

        response = self.client.post(reverse("task-user-selectable") + '?responses_filter_values=Yes', data=post_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 5)

        post_data = {
            "items_conditions": [
                {
                    "conditions": [
                        {
                            "operator": "<=",
                            "value": "50"
                        }
                    ],
                    "field": "age",
                    "type": "integer"
                },
                {
                    "conditions": [
                        {
                            "operator": ">",
                            "value": "20"
                        }
                    ],
                    "field": "age",
                    "type": "integer"
                }
            ],
            "stage": self.initial_stage.id,
            "search_stage": second_stage.id

        }

        response = self.client.post(reverse("task-user-selectable") + '?responses_filter_values=Yes', data=post_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 3)
        post_data = {
            "items_conditions": [
                {
                    "conditions": [
                        {
                            "operator": "<=",
                            "value": "50"
                        }
                    ],
                    "field": "age",
                    "type": "integer"
                },
                {
                    "conditions": [
                        {
                            "operator": ">",
                            "value": "20"
                        }
                    ],
                    "field": "age",
                    "type": "integer"
                },
                {
                    "conditions": [
                        {
                            "operator": "in",
                            "value": "t"
                        }
                    ],
                    "field": "name",
                    "type": "string"
                }
            ],
            "stage": self.initial_stage.id,
            "search_stage": second_stage.id

        }

        response = self.client.post(reverse("task-user-selectable") + '?responses_filter_values=Yes', data=post_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)

