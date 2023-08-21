import json

from django.http import QueryDict
from rest_framework import status
from rest_framework.reverse import reverse

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class TaskTest(GigaTurnipTestHelper):

    def test_retrieve_assigned_task(self):
        task = self.create_task(self.initial_stage)

        response = self.get_objects("task-detail", pk=task.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_unassigned_task(self):
        self.employee_client = self.prepare_client(
            self.initial_stage,
            self.employee,
            RankLimit(is_creation_open=True))
        task = self.create_task(self.initial_stage, self.employee_client)

        response = self.get_objects("task-detail", pk=task.id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_user_selectable_free_task(self):
        second_stage = self.initial_stage.add_stage(TaskStage())
        self.client = self.prepare_client(second_stage, self.user)
        task_1 = self.create_initial_task()
        task_1 = self.complete_task(task_1)
        task_2 = task_1.out_tasks.first() # task is user selectable

        response = self.get_objects("task-detail", pk=task_2.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_user_selectable_displayed_prev_stages(self):
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
        second_stage = self.initial_stage.add_stage(TaskStage())
        second_stage.displayed_prev_stages.add(self.initial_stage)
        self.client = self.prepare_client(second_stage, self.user)

        # act
        task_1 = self.create_initial_task()
        task_1 = self.complete_task(task_1)
        task_2 = task_1.out_tasks.first() # task is user selectable

        response = self.get_objects("task-user-selectable")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data["results"]), 1)

        actual_stage = response.data["results"][0]["stage"]

        self.assertEqual(actual_stage["id"], second_stage.id)
        self.assertEqual(actual_stage["name"], second_stage.name)
        self.assertEqual(actual_stage["chain"], self.chain.id)
        self.assertEqual(actual_stage["campaign"], self.campaign.id)
        self.assertEqual(actual_stage["card_json_schema"], second_stage.card_json_schema)
        self.assertEqual(actual_stage["card_ui_schema"], second_stage.card_ui_schema)

        self.assertTrue(actual_stage["displayed_prev_stages"])

        displayed_prev_tasks = actual_stage["displayed_prev_stages"]
        self.assertEqual(len(displayed_prev_tasks), 1)
        self.assertEqual(displayed_prev_tasks[0]["id"], task_1.id)
        self.assertEqual(displayed_prev_tasks[0]["complete"], task_1.complete)
        self.assertEqual(displayed_prev_tasks[0]["force_complete"], task_1.force_complete)
        self.assertEqual(displayed_prev_tasks[0]["reopened"], task_1.reopened)
        self.assertEqual(displayed_prev_tasks[0]["responses"], task_1.responses)

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

        return
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

    def test_task_user_relevant(self):
        individual_chain = Chain.objects.create(
            name="Individual chain",
            campaign=self.campaign,
            is_individual=True
        )
        new_stage = TaskStage.objects.create(
            name="Individual",
            x_pos=1,
            y_pos=1,
            chain=individual_chain,
            is_creatable=True
        )

        RankLimit.objects.create(
                rank=self.user.ranks.first(),
                stage=new_stage,
                open_limit=0,
                total_limit=0,
                is_listing_allowed=True,
                is_creation_open=True
        )

        tasks = [self.create_task(new_stage) for i in range(3)]
        [self.complete_task(i) for i in tasks]

        self.assertTrue(all(list(Task.objects.values_list("complete", flat=True))))

        response = self.get_objects("task-user-relevant")

        self.assertEqual(response.data['count'], 0)

    def test_task_user_selectable_filter_by_responses(self):
        first_schema = {
            "type": "object",
            "properties": {
                "chain_type": {"type": "string"},
            },
            "required": ["chain_type"]
        }
        self.initial_stage.json_schema = json.dumps(first_schema)
        self.initial_stage.save()

        second_schema = {
            "type": "object",
            "properties": {
                "price": {"type": "number"},
                "year": {"type": "number"},
                "name": {"type": "string"},
            },
            "required": ["price", "year", "name"]
        }
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage,
                json_schema=json.dumps(second_schema)
            )
        )
        third_schema = {
            "type": "object",
            "properties": {
                "grade": {"type": "number"},
            },
            "required": ["last_name", "name"]
        }
        filter_fields_schema = [
                {
                    "type": "string",
                    "field_name": "chain_type",
                    "condition": "==",
                    "stage_id": self.initial_stage.id,
                    "title": "Filter by type"
                },
                {
                    "type": "integer",
                    "field_name": "year",
                    "condition": ">=",
                    "stage_id": second_stage.id,
                    "title": "Filter by year"
                },
                {
                    "type": "integer",
                    "field_name": "price",
                    "condition": "==",
                    "stage_id": second_stage.id,
                    "title": "Filter by price"
                }
        ]

        third_stage = second_stage.add_stage(
            TaskStage(
                assign_user_by=TaskStageConstants.RANK,
                json_schema=json.dumps(third_schema),
                filter_fields_schema=filter_fields_schema
            )
        )

        case_1 = Case.objects.create()
        task_1_1 = Task.objects.create(
            responses={"chain_type": "math"},
            assignee=self.employee,
            case=case_1,
            stage=self.initial_stage,
            complete=True
        )
        task_1_2 = Task.objects.create(
            responses={"price": 32, "year": 2012, "name": "Anton"},
            assignee=self.employee,
            case=case_1,
            stage=second_stage,
            complete=True
        )
        task_1_2.in_tasks.add(task_1_1)

        task_1_3 = Task.objects.create(
            responses={"grade": "2012"},
            case=case_1,
            stage=third_stage,
            complete=False
        )
        task_1_3.in_tasks.add(task_1_2)

        case_2 = Case.objects.create()
        task_2_1 = Task.objects.create(
            responses={"chain_type": "math"},
            assignee=self.employee,
            case=case_2,
            stage=self.initial_stage,
            complete=True
        )
        task_2_2 = Task.objects.create(
            responses={"price": 32, "year": 2013, "name": "Anton"},
            assignee=self.employee,
            case=case_2,
            stage=second_stage,
            complete=True
        )
        task_2_2.in_tasks.add(task_2_1)

        task_2_3 = Task.objects.create(
            responses={"grade": "2012"},
            case=case_2,
            stage=third_stage,
            complete=False
        )
        task_2_3.in_tasks.add(task_2_2)


        case_3 = Case.objects.create()
        task_3_1 = Task.objects.create(
            responses={"chain_type": "botany"},
            assignee=self.employee,
            case=case_3,
            stage=self.initial_stage,
            complete=True
        )
        task_3_2 = Task.objects.create(
            responses={"price": 33, "year": 2012, "name": "Anton"},
            assignee=self.employee,
            case=case_3,
            stage=second_stage,
            complete=True
        )
        task_3_2.in_tasks.add(task_3_1)

        task_3_3 = Task.objects.create(
            responses={"grade": "2012"},
            case=case_3,
            stage=third_stage,
            complete=False
        )
        task_3_3.in_tasks.add(task_3_2)

        self.prepare_client(third_stage, user=self.user)

        response = self.get_objects("task-user-selectable")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(sorted([i["id"] for i in response.data["results"]]),
            [task_1_3.id, task_2_3.id, task_3_3.id])

        data = {
            "chain_type": "math"
        }
        response = self.client.post(reverse("task-user-selectable"), data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(sorted([i["id"] for i in response.data["results"]]),
            [task_1_3.id, task_2_3.id])

        data = {
            "chain_type": "math",
            "year": 2012
        }
        response = self.client.post(reverse("task-user-selectable"), data=data,
            format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(sorted([i["id"] for i in response.data["results"]]),
            [task_1_3.id, task_2_3.id])

        data = {
            "chain_type": "math",
            "year": 2012,
            "price": 33
        }
        response = self.client.post(reverse("task-user-selectable"), data=data,
            format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual([i["id"] for i in response.data["results"]], [])

    def test_task_responses_icontains(self):
        first_schema = {
            "type": "object",
            "properties": {
                "chain_type": {"type": "string"},
            },
            "required": ["chain_type"]
        }
        self.initial_stage.json_schema = json.dumps(first_schema)
        self.initial_stage.save()

        second_schema = {
            "type": "object",
            "properties": {
                "price": {"type": "number"},
                "year": {"type": "number"},
                "name": {"type": "string"},
            },
            "required": ["price", "year", "name"]
        }
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage,
                json_schema=json.dumps(second_schema)
            )
        )
        third_schema = {
            "type": "object",
            "properties": {
                "grade": {"type": "number"},
            },
            "required": ["last_name", "name"]
        }
        third_stage = second_stage.add_stage(
            TaskStage(
                assign_user_by=TaskStageConstants.RANK,
                json_schema=json.dumps(third_schema),
            )
        )

        case_1 = Case.objects.create()
        task_1_1 = Task.objects.create(
            responses={"chain_type": "math"},
            assignee=self.employee,
            case=case_1,
            stage=self.initial_stage,
            complete=True
        )
        task_1_2_data = {
            "price": 32,
            "year": 2012,
            "name": "Anton",
            "description":{
                "workplace": "hotel"
            }
        }
        task_1_2 = Task.objects.create(
            responses=task_1_2_data,
            assignee=self.employee,
            case=case_1,
            stage=second_stage,
            complete=True
        )
        task_1_2.in_tasks.add(task_1_1)

        task_1_3 = Task.objects.create(
            responses={"grade": "2012"},
            case=case_1,
            stage=third_stage,
            complete=False
        )
        task_1_3.in_tasks.add(task_1_2)

        case_2 = Case.objects.create()
        task_2_1 = Task.objects.create(
            responses={"chain_type": "math"},
            assignee=self.employee,
            case=case_2,
            stage=self.initial_stage,
            complete=True
        )
        task_2_2_data = {
            "price": 32,
            "year": 2013,
            "name": "Anton",
            "description":{
                "workplace": "office"
            }
        }
        task_2_2 = Task.objects.create(
            responses=task_2_2_data,
            assignee=self.employee,
            case=case_2,
            stage=second_stage,
            complete=True
        )
        task_2_2.in_tasks.add(task_2_1)

        task_2_3 = Task.objects.create(
            responses={"grade": "2012"},
            case=case_2,
            stage=third_stage,
            complete=False
        )
        task_2_3.in_tasks.add(task_2_2)


        case_3 = Case.objects.create()
        task_3_1 = Task.objects.create(
            responses={"chain_type": "botany"},
            assignee=self.employee,
            case=case_3,
            stage=self.initial_stage,
            complete=True
        )
        task_3_2_data = {
            "price": 32,
            "year": 2012,
            "name": "Anton",
            "description":{
                "workplace": "new office"
            }
        }
        task_3_2 = Task.objects.create(
            responses=task_3_2_data,
            assignee=self.employee,
            case=case_3,
            stage=second_stage,
            complete=True
        )
        task_3_2.in_tasks.add(task_3_1)

        task_3_3 = Task.objects.create(
            responses={"grade": "2012"},
            case=case_3,
            stage=third_stage,
            complete=False
        )
        task_3_3.in_tasks.add(task_3_2)
        self.prepare_client(third_stage, user=self.user)

        response = self.get_objects("task-user-selectable")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(sorted([i["id"] for i in response.data["results"]]), [task_1_3.id, task_2_3.id, task_3_3.id])

        params = {
            "responses__icontains": "math"
        }
        query_dict = QueryDict('', mutable=True)
        query_dict.update(params)
        url = reverse("task-user-selectable")
        response = self.client.post(f"{url}?{query_dict.urlencode()}", {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(sorted([i["id"] for i in response.data["results"]]), [task_1_3.id, task_2_3.id])

        params = {
            "responses__icontains": "office",
        }
        query_dict = QueryDict('', mutable=True)
        query_dict.update(params)
        response = self.client.post(f"{url}?{query_dict.urlencode()}", {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(sorted([i["id"] for i in response.data["results"]]), [task_2_3.id, task_3_3.id])

        params = {
            "responses__icontains": 20,
        }
        query_dict = QueryDict('', mutable=True)
        query_dict.update(params)
        response = self.client.post(f"{url}?{query_dict.urlencode()}", {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(sorted([i["id"] for i in response.data["results"]]), [task_1_3.id, task_2_3.id, task_3_3.id])

    def test_task_no_override_responses(self):
        new_chain = Chain.objects.create(
            name="Profile chain",
            campaign=self.campaign,
        )
        second_stage = TaskStage.objects.create(
            name="User profile",
            chain=new_chain,
            assign_user_by=TaskStageConstants.RANK,
            x_pos=1,
            y_pos=1,
        )
        case = Case.objects.create()
        profile_task = Task.objects.create(
            stage=second_stage,
            assignee=self.user,
            case=case,
            responses={"username": "CJ"},
            complete=True,
        )

        CopyField.objects.create(
            copy_by=CopyFieldConstants.USER,
            task_stage=self.initial_stage,
            copy_from_stage=second_stage,
            copy_all=True
        )

        task_create_url = reverse("taskstage-create-task", kwargs={"pk": self.initial_stage.id})

        data = {
            "responses": {"foo": "field"}
        }
        response = self.client.post(task_create_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["responses"], {"username": "CJ", "foo": "field"})

    def test_superuser_update(self):
        case = Case.objects.create()
        task = Task.objects.create(
            assignee=self.employee,
            stage=self.initial_stage,
            responses={"foo":"boo"},
            case=case,
        )

        responses = {"hello": "world!"}
        self.user.is_superuser = True

        response = self.update_task_responses(task, responses, self.client)
        self.assertIsInstance(response, Task)
