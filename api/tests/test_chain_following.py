import json
import random
from uuid import uuid4

from django.db import IntegrityError
from django.db.models import Count
from rest_framework import status
from rest_framework.test import APITestCase, APIClient, RequestsClient
from rest_framework.reverse import reverse

from api.models import CustomUser, TaskStage, Campaign, Chain, ConditionalStage, Stage, Rank, RankRecord, RankLimit, \
    Task, CopyField, Integration, Quiz, ResponseFlattener, Log, AdminPreference, Track, TaskAward, Notification, \
    DynamicJson, PreviousManual, Webhook, AutoNotification
from jsonschema import validate

class GigaTurnipTest(APITestCase):

    def create_client(self, u):
        client = APIClient()
        client.force_authenticate(u)
        return client

    def prepare_client(self, stage, user=None, rank_limit=None):
        u = user
        if u is None:
            user_name = str(uuid4())
            u = CustomUser.objects.create_user(
                username=user_name,
                email=user_name + "@email.com",
                password='test')
        rank = Rank.objects.create(name=stage.name)
        RankRecord.objects.create(
            user=u,
            rank=rank)
        rank_l = rank_limit
        if rank_l is None:
            rank_l = RankLimit.objects.create(
                rank=rank,
                stage=stage,
                open_limit=0,
                total_limit=0,
                is_listing_allowed=True,
                is_creation_open=False)
        else:
            rank_l.rank = rank
            rank_l.stage = stage
        rank_l.save()
        return self.create_client(u)

    def setUp(self):
        self.campaign = Campaign.objects.create(name="Campaign")
        self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        self.initial_stage = TaskStage.objects.create(
            name="Initial",
            x_pos=1,
            y_pos=1,
            chain=self.chain,
            is_creatable=True)
        self.user = CustomUser.objects.create_user(username="test",
                                                   email='test@email.com',
                                                   password='test')

        self.employee = CustomUser.objects.create_user(username="employee",
                                                       email='employee@email.com',
                                                       password='employee')
        self.employee_client = self.create_client(self.employee)

        self.client = self.prepare_client(
            self.initial_stage,
            self.user,
            RankLimit(is_creation_open=True))

        # self.client.force_authenticate(user=self.user)
        # self.rank = Rank.objects.create(name="rank")
        # self.rank_record = RankRecord.objects.create(
        #     user=self.user,
        #     rank=self.rank)

    def get_objects(self, endpoint, params=None, client=None, pk=None):
        c = client
        if c is None:
            c = self.client
        if pk:
            url = reverse(endpoint, kwargs={"pk": pk})
        else:
            url = reverse(endpoint)
        if params:
            return c.get(url, data=params)
        else:
            return c.get(url)

    def create_task(self, stage, client=None):
        c = client
        task_create_url = reverse(
            "taskstage-create-task",
            kwargs={"pk": stage.pk})
        if c is None:
            c = self.client
        response = c.get(task_create_url)
        return Task.objects.get(id=response.data["id"])

    def request_assignment(self, task, client=None):
        c = client
        request_assignment_url = reverse(
            "task-request-assignment",
            kwargs={"pk": task.pk})
        if c is None:
            c = self.client
        response = c.get(request_assignment_url)
        task = Task.objects.get(id=response.data["id"])
        self.assertEqual(response.wsgi_request.user, task.assignee)
        return task

    def create_initial_task(self):
        return self.create_task(self.initial_stage)

    def create_initial_tasks(self, count):
        return [self.create_initial_task() for x in range(count)]

    def complete_task(self, task, responses=None, client=None, whole_response=False):
        c = client
        if c is None:
            c = self.client
        task_update_url = reverse("task-detail", kwargs={"pk": task.pk})
        if responses:
            args = {"complete": True, "responses": responses}
        else:
            args = {"complete": True}
        response = c.patch(task_update_url, args, format='json')
        if not whole_response and response.data.get('id'):
            return Task.objects.get(id=response.data["id"])
        elif whole_response:
            return response
        else:
            return response

    def update_task_responses(self, task, responses, client=None):
        c = client
        if c is None:
            c = self.client
        task_update_url = reverse("task-detail", kwargs={"pk": task.pk})
        args = {"responses": responses}
        response = c.patch(task_update_url, args, format='json')
        return Task.objects.get(id=response.data["id"])

    def check_task_manual_creation(self, task, stage):
        self.assertEqual(task.stage, stage)
        self.assertFalse(task.complete)
        self.assertFalse(task.force_complete)
        self.assertFalse(task.reopened)
        self.assertIsNone(task.integrator_group)
        self.assertFalse(task.in_tasks.exists())
        self.assertIsNone(task.responses)
        self.assertEqual(len(Task.objects.filter(stage=task.stage)), 1)

    def check_task_auto_creation(self, task, stage, initial_task):
        self.assertEqual(task.stage, stage)
        self.assertFalse(task.complete)
        self.assertFalse(task.force_complete)
        self.assertFalse(task.reopened)
        self.assertIsNone(task.integrator_group)
        self.assertTrue(task.in_tasks.exists())
        self.assertIn(initial_task.id, task.in_tasks.values_list("id", flat=True))
        self.assertTrue(len(task.in_tasks.values_list("id", flat=True)) == 1)
        self.assertEqual(len(Task.objects.filter(stage=task.stage)), 1)

    def check_task_completion(self, task, stage, responses=None):
        self.assertEqual(task.stage, stage)
        self.assertTrue(task.complete)
        self.assertFalse(task.force_complete)
        self.assertFalse(task.reopened)
        self.assertIsNone(task.integrator_group)
        self.assertFalse(task.in_tasks.exists())
        if responses is not None:
            self.assertEqual(task.responses, responses)
        self.assertEqual(len(Task.objects.filter(stage=task.stage)), 1)

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

    def test_add_stage(self):
        self.initial_stage.add_stage(ConditionalStage()).add_stage(TaskStage())
        stages_queryset = Stage.objects.filter(chain=self.chain)
        self.assertEqual(len(stages_queryset), 3)

    def test_simple_chain(self):
        second_stage = self.initial_stage.add_stage(TaskStage())
        initial_task = self.create_initial_task()
        self.complete_task(initial_task)
        second_task = Task.objects.get(
            stage=second_stage,
            case=initial_task.case)
        self.check_task_auto_creation(second_task, second_stage, initial_task)

    def test_simple_update(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "check": {"type": "string"}
            },
            "required": ["check"]
        })
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(TaskStage())
        initial_task = self.create_initial_task()
        responses = {"check": "cheese"}
        initial_task = self.update_task_responses(initial_task, responses)
        initial_task = self.complete_task(initial_task)
        self.assertEqual(Task.objects.count(), 2)
        self.assertEqual(initial_task.responses, responses)

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

        conditional_stage = ConditionalStage()
        conditional_stage.conditions = [
            {"field": "verified", "value": "yes", "condition": "=="}
        ]
        conditional_stage = self.initial_stage.add_stage(conditional_stage)
        last_task_stage = conditional_stage.add_stage(TaskStage())
        initial_task = self.create_initial_task()
        responses = {"verified": "yes"}
        initial_task = self.update_task_responses(initial_task, responses)
        self.complete_task(initial_task, responses)
        new_task = Task.objects.get(
            stage=last_task_stage,
            case=initial_task.case)
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
            {"field": "verified", "value": "yes", "condition": "=="}
        ]
        conditional_stage = self.initial_stage.add_stage(conditional_stage)
        last_task_stage = conditional_stage.add_stage(TaskStage())
        initial_task = self.create_initial_task()
        responses = {"verified": "no"}
        initial_task = self.update_task_responses(initial_task, responses)
        self.complete_task(initial_task, responses)
        new_task = Task.objects \
            .filter(stage=last_task_stage, case=initial_task.case) \
            .exists()
        self.assertFalse(new_task)

    def test_pingpong(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "answer": { "type": "string" }
            },
            "required": ["answer"]
        })
        self.initial_stage.save()

        conditional_stage = ConditionalStage()
        conditional_stage.conditions = [
            {"field": "verified", "value": "no", "condition": "=="}
        ]
        conditional_stage.pingpong = True
        verification_task_stage = self.initial_stage \
            .add_stage(conditional_stage) \
            .add_stage(TaskStage())
        final_task_stage = verification_task_stage.add_stage(TaskStage())

        verification_client = self.prepare_client(verification_task_stage)

        initial_task = self.create_initial_task()
        responses = {"answer": "something"}
        initial_task = self.update_task_responses(initial_task, responses)
        self.complete_task(initial_task)

        verification_task = Task.objects \
            .get(stage=verification_task_stage, case=initial_task.case)
        self.check_task_auto_creation(
            verification_task,
            verification_task_stage,
            initial_task)
        self.request_assignment(verification_task, verification_client)

        verification_task_responses = {"verified": "no"}
        verification_task = self.update_task_responses(
            verification_task,
            verification_task_responses,
            verification_client)

        verification_task = self.complete_task(
            verification_task,
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

        verification_task_responses = {"verified": "yes"}

        verification_task = self.update_task_responses(
            verification_task,
            verification_task_responses,
            verification_client)
        verification_task = self.complete_task(verification_task,
                                               # verification_task_responses,
                                               client=verification_client)

        self.assertTrue(verification_task.complete)

        initial_task = Task.objects.get(id=initial_task.id)

        self.assertTrue(initial_task.complete)

        self.assertEqual(len(Task.objects.filter()), 3)
        self.assertEqual(len(Task.objects.filter(case=initial_task.case, stage=final_task_stage)), 1)

        final_task = Task.objects.get(case=initial_task.case, stage=final_task_stage)

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

        conditional_stage = ConditionalStage()
        conditional_stage.conditions = [
            {"field": "verified", "value": "no", "condition": "=="}
        ]
        conditional_stage.pingpong = True
        verification_task_stage = self.initial_stage \
            .add_stage(conditional_stage) \
            .add_stage(TaskStage())
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
        responses = {"answer": "something"}
        initial_task = self.update_task_responses(initial_task, responses)
        self.complete_task(initial_task)

        verification_task = Task.objects \
            .get(stage=verification_task_stage, case=initial_task.case)
        self.check_task_auto_creation(
            verification_task,
            verification_task_stage,
            initial_task)
        self.request_assignment(verification_task, verification_client)

        verification_task_responses = {"verified": "yes"}

        verification_task = self.complete_task(
            verification_task,
            verification_task_responses,
            verification_client)

        self.assertTrue(verification_task.complete)
        self.assertEqual(len(Task.objects.filter(case=initial_task.case)), 3)
        self.assertEqual(len(Task.objects.filter()), 3)

        initial_task = Task.objects.get(id=initial_task.id)

        self.assertTrue(initial_task.complete)

        self.assertEqual(len(Task.objects.filter()), 3)
        self.assertEqual(len(Task.objects.filter(case=initial_task.case, stage=final_task_stage)), 1)

        final_task = Task.objects.get(case=initial_task.case, stage=final_task_stage)

        self.check_task_auto_creation(
            final_task,
            final_task_stage,
            verification_task)
        self.assertFalse(final_task.assignee)

    def test_copy_field(self):
        id_chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        id_stage = TaskStage.objects.create(
            name="ID",
            x_pos=1,
            y_pos=1,
            chain=id_chain,
            json_schema='{"type": "object","properties": {"name": {"type": "string"},"phone": {"type": "integer"},"address": {"type": "string"}}}',
            is_creatable=True)
        self.client = self.prepare_client(
            id_stage,
            self.user,
            RankLimit(is_creation_open=True))
        task1 = self.create_task(id_stage)

        correct_responses = {"name": "kloop", "phone": 3, "address": "kkkk"}

        task1 = self.complete_task(
            task1,
            {"name": "rinat", "phone": 2, "address": "ssss"}
        )

        CopyField.objects.create(
            copy_by="US",
            task_stage=self.initial_stage,
            copy_from_stage=id_stage,
            fields_to_copy="name->name phone->phone1 absent->absent")

        task = self.create_initial_task()

        self.assertEqual(len(task.responses), 2)
        self.assertEqual(task.responses["name"], task1.responses["name"])
        self.assertEqual(task.responses["phone1"], task1.responses["phone"])

    def test_copy_field_with_no_source_task(self):
        id_chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        id_stage = TaskStage.objects.create(
            name="ID",
            x_pos=1,
            y_pos=1,
            chain=id_chain,
            is_creatable=True)
        # self.client = self.prepare_client(
        #     id_stage,
        #     self.user,
        #     RankLimit(is_creation_open=True))
        # task1 = self.create_task(id_stage)
        # task2 = self.create_task(id_stage)
        # task3 = self.create_task(id_stage)
        #
        # correct_responses = {"name": "kloop", "phone": 3, "addr": "kkkk"}
        #
        # task1 = self.complete_task(
        #     task1,
        #     {"name": "rinat", "phone": 2, "addr": "ssss"})
        # task3 = self.complete_task(
        #     task3,
        #     {"name": "ri", "phone": 5, "addr": "oooo"})
        # task2 = self.complete_task(task2, correct_responses)

        CopyField.objects.create(
            copy_by="US",
            task_stage=self.initial_stage,
            copy_from_stage=id_stage,
            fields_to_copy="name->name phone->phone1 absent->absent")

        task = self.create_initial_task()

        self.check_task_manual_creation(task, self.initial_stage)

    def test_copy_field_fail_for_different_campaigns(self):
        campaign = Campaign.objects.create(name="Campaign")
        id_chain = Chain.objects.create(name="Chain", campaign=campaign)
        id_stage = TaskStage.objects.create(
            name="ID",
            x_pos=1,
            y_pos=1,
            json_schema='{"type": "object","properties": {"name": {"type": "string"},"phone": {"type": "integer"},"address": {"type": "string"}}}',
            chain=id_chain,
            is_creatable=True)
        self.client = self.prepare_client(
            id_stage,
            self.user,
            RankLimit(is_creation_open=True))
        task1 = self.create_task(id_stage)
        task2 = self.create_task(id_stage)
        task3 = self.create_task(id_stage)

        correct_responses = {"name": "kloop", "phone": 3, "address": "kkkk"}

        task1 = self.complete_task(
            task1,
            {"name": "rinat", "phone": 2, "address": "ssss"})
        task3 = self.complete_task(
            task3,
            {"name": "ri", "phone": 5, "address": "oooo"})
        task2 = self.complete_task(task2, correct_responses)

        CopyField.objects.create(
            copy_by="US",
            task_stage=self.initial_stage,
            copy_from_stage=id_stage,
            fields_to_copy="name->name phone->phone1 absent->absent")

        task = self.create_initial_task()

        self.assertIsNone(task.responses)

    def test_get_tasks_selectable(self):
        second_stage = self.initial_stage.add_stage(TaskStage())
        self.client = self.prepare_client(second_stage, self.user)
        task_1 = self.create_initial_task()
        task_1 = self.complete_task(task_1)
        task_2 = task_1.out_tasks.all()[0]
        response = self.get_objects("task-user-selectable")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], task_2.id)

    def test_open_previous(self):
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                assign_user_from_stage=self.initial_stage,
                allow_go_back=True
            ))
        initial_task = self.create_initial_task()
        self.complete_task(initial_task, responses={})

        second_task = Task.objects.get(
            stage=second_stage,
            case=initial_task.case)
        self.assertEqual(initial_task.assignee, second_task.assignee)
        # self.check_task_auto_creation(second_task, second_stage, initial_task)
        response = self.get_objects("task-open-previous", pk=second_task.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], initial_task.id)

        initial_task = Task.objects.get(id=initial_task.id)
        second_task = Task.objects.get(id=second_task.id)

        self.assertTrue(second_task.complete)
        self.assertTrue(initial_task.reopened)
        self.assertFalse(initial_task.complete)
        self.assertEqual(Task.objects.all().count(), 2)

        initial_task = self.complete_task(initial_task)

        second_task = Task.objects.get(id=second_task.id)

        self.assertTrue(initial_task.complete)
        self.assertEqual(Task.objects.all().count(), 2)
        self.assertFalse(second_task.complete)
        self.assertTrue(second_task.reopened)

    def test_integration(self):
        self.initial_stage.json_schema = '{"type": "object","properties": {"oik": {"type": "integer"},"data": {"type": "string"}}}'
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

    def test_copy_field_by_case(self):
        self.initial_stage.json_schema = '{"type": "object","properties": {"name": {"type": "string"},"phone": {"type": "integer"},"address": {"type": "string"}}}'
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                assign_user_from_stage=self.initial_stage)
        )
        third_stage = second_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                json_schema='{"type": "object","properties": {"name": {"type": "string"},"phone1": {"type": "integer"},"absent": {"type": "string"}}}',
                assign_user_from_stage=self.initial_stage)
        )
        CopyField.objects.create(
            copy_by="CA",
            task_stage=third_stage,
            copy_from_stage=self.initial_stage,
            fields_to_copy="name->name phone->phone1 absent->absent")

        task = self.create_initial_task()
        correct_responses = {"name": "kloop", "phone": 3, "address": "kkkk"}
        task = self.complete_task(task, responses=correct_responses)
        task_2 = task.out_tasks.all()[0]
        self.complete_task(task_2)
        task_3 = task_2.out_tasks.all()[0]

        self.assertEqual(Task.objects.count(), 3)
        self.assertEqual(len(task_3.responses), 2)
        self.assertEqual(task_3.responses["name"], task.responses["name"])
        self.assertEqual(task_3.responses["phone1"], task.responses["phone"])

    def test_copy_field_by_case_copy_all(self):
        self.initial_stage.json_schema = '{"type": "object","properties": {"name": {"type": "string"},"phone": {"type": "integer"},"address": {"type": "string"}}}'
        self.initial_stage.save()
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                assign_user_from_stage=self.initial_stage)
        )
        third_stage = second_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                json_schema='{"type": "object","properties": {"name": {"type": "string"},"phone": {"type": "integer"},"address": {"type": "string"}}}',
                assign_user_from_stage=self.initial_stage)
        )
        CopyField.objects.create(
            copy_by="CA",
            task_stage=third_stage,
            copy_from_stage=self.initial_stage,
            copy_all=True)

        task = self.create_initial_task()
        correct_responses = {"name": "kloop", "phone": 3, "addr": "kkkk"}
        task = self.complete_task(task, responses=correct_responses)
        task_2 = task.out_tasks.all()[0]
        self.complete_task(task_2)
        task_3 = task_2.out_tasks.all()[0]
        self.assertEqual(task_3.responses, task.responses)

    def test_copy_input(self):
        self.initial_stage.json_schema = '{"type": "object","properties": {"name": {"type": "string"},"phone": {"type": "integer"},"address": {"type": "string"}}}'
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                assign_user_from_stage=self.initial_stage,
                copy_input=True)
        )
        task = self.create_initial_task()
        correct_responses = {"name": "kloop", "phone": 3, "address": "kkkk"}
        task = self.complete_task(task, responses=correct_responses)
        task_2 = task.out_tasks.all()[0]

        self.assertEqual(task_2.responses, task.responses)

    def test_conditional_ping_pong_pass(self):
        self.initial_stage.json_schema = '{"type":"object","properties":{"answer":{"type":"string"}}}'
        self.initial_stage.save()

        conditions = [
            {"field": "verified", "value": "no", "condition": "=="}
        ]
        conditional_stage = self.initial_stage.add_stage(
            ConditionalStage(
                conditions=conditions,
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
            assign_user_by="ST"
        ))

        verification_client = self.prepare_client(verification_task_stage)

        initial_task = self.create_initial_task()
        responses = {"answer": "something"}
        initial_task = self.update_task_responses(initial_task, responses)
        initial_task = self.complete_task(initial_task)

        verification_task = Task.objects \
            .get(stage=verification_task_stage, case=initial_task.case)

        verification_task = self.request_assignment(verification_task, verification_client)

        verification_task_responses = {"verified": "yes"}

        verification_task = self.complete_task(
            verification_task,
            verification_task_responses,
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

        conditions = [
            {"field": "verified", "value": "no", "condition": "=="}
        ]
        conditional_stage = self.initial_stage.add_stage(
            ConditionalStage(
                conditions=conditions,
                pingpong=True
            )
        )

        verification_task_stage = conditional_stage.add_stage(TaskStage(
            name="Verification task stage",
            json_schema = '{"type":"object","properties":{"answer":{"type":"string"},"verified":{"type":"string"}}}',
            copy_input=True
        ))

        final_task_stage = verification_task_stage.add_stage(TaskStage(
            name="Final task stage",
            assign_user_from_stage=self.initial_stage,
            assign_user_by="ST"
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

        responses = {"answer": "something new"}
        initial_task = self.complete_task(initial_task, responses=responses)

        verification_task = Task.objects \
            .get(stage=verification_task_stage, case=initial_task.case)

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

        conditions = [
            {"field": "verified", "value": "no", "condition": "=="}
        ]
        conditional_stage = self.initial_stage.add_stage(
            ConditionalStage(
                conditions=conditions,
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
            assign_user_by="ST"
        ))

        verification_client = self.prepare_client(verification_task_stage)

        initial_task = self.create_initial_task()
        responses = {"answer": "something"}
        initial_task = self.complete_task(initial_task, responses=responses)

        verification_task = Task.objects \
            .get(stage=verification_task_stage, case=initial_task.case)

        verification_task = self.request_assignment(verification_task, verification_client)

        verification_task_responses = {"verified": "no"}

        verification_task = self.complete_task(
            verification_task,
            verification_task_responses,
            verification_client)

        initial_task = Task.objects.get(id=initial_task.id)

        self.assertTrue(initial_task.reopened)
        self.assertFalse(initial_task.complete)

        self.assertTrue(verification_task.complete)

        self.assertEqual(Task.objects.count(), 2)

        responses = {"answer": "something new"}
        initial_task = self.complete_task(initial_task, responses=responses)

        verification_task = Task.objects \
            .get(stage=verification_task_stage, case=initial_task.case)

        verification_task_responses = {"verified": "yes"}

        verification_task = self.complete_task(
            verification_task,
            verification_task_responses,
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

        conditions = [
            {"field": "verified", "value": "no", "condition": "=="}
        ]
        conditional_stage = self.initial_stage.add_stage(
            ConditionalStage(
                conditions=conditions,
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
            assign_user_by="ST"
        ))

        CopyField.objects.create(
            copy_by="CA",
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
            go=AutoNotification.BACKWARD
        )

        complete_notification = Notification.objects.create(
            title='You have been complete task successfully!',
            campaign=self.campaign
        )
        auto_notification_2 = AutoNotification.objects.create(
            trigger_stage=verification_task_stage,
            recipient_stage=self.initial_stage,
            notification=complete_notification,
            go=AutoNotification.FORWARD
        )

        verification_client = self.prepare_client(verification_task_stage)

        initial_task = self.create_initial_task()
        responses = {"answer": "something"}
        initial_task = self.complete_task(initial_task, responses=responses)

        verification_task = Task.objects \
            .get(stage=verification_task_stage, case=initial_task.case)

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

        responses = {"answer": "something new"}
        initial_task = self.complete_task(initial_task, responses=responses)

        verification_task = Task.objects \
            .get(stage=verification_task_stage, case=initial_task.case)

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
                                                          trigger_go=AutoNotification.BACKWARD)
        fw_notifications = self.user.notifications.filter(sender_task=verification_task,
                                                          receiver_task=initial_task,
                                                          trigger_go=AutoNotification.FORWARD)
        self.assertEqual(self.user.notifications.count(), 2)
        self.assertEqual(bw_notifications.count(), 1)
        self.assertEqual(fw_notifications.count(), 1)
        self.assertEqual(bw_notifications[0].title, auto_notification_1.notification.title)
        self.assertEqual(fw_notifications[0].title, auto_notification_2.notification.title)

    def test_quiz(self):
        task_correct_responses = self.create_initial_task()
        correct_responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "d"}
        self.initial_stage.json_schema = {
            "type": "object",
            "properties": {
                "1": {
                    "enum": [ "a", "b", "c", "d"], "title": "Question 1", "type": "string"
                },
                "2": {
                    "enum": [ "a", "b", "c", "d"], "title": "Question 2", "type": "string"
                },
                "3": {
                    "enum": [ "a", "b", "c", "d"], "title": "Question 3", "type": "string"
                },
                "4": {
                    "enum": [ "a", "b", "c", "d"], "title": "Question 4", "type": "string"
                },
                "5": {
                    "enum": [ "a", "b", "c", "d"], "title": "Question 5", "type": "string"
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
        task = self.create_initial_task()
        responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "b"}
        task = self.complete_task(task, responses=responses)

        self.assertEqual(task.responses["meta_quiz_score"], 80)
        self.assertEqual(Task.objects.count(), 2)
        self.assertTrue(task.complete)

    def test_quiz_correctly_answers(self):
        task_correct_responses = self.create_initial_task()

        self.initial_stage.json_schema = {
            "type": "object",
            "properties": {
                "q_1": {
                    "enum": [ "a", "b", "c" ],
                    "title": "Question 1",
                    "type": "string"
                },
                "q_2": {
                    "enum": [ "a", "b", "c" ],
                    "title": "Question 2",
                    "type": "string"
                },
                "q_3": {
                    "enum": [ "a", "b", "c" ],
                    "title": "Question 3",
                    "type": "string"
                }
            },
            "dependencies": {},
            "required": [
                "q_1",
                "q_2",
                "q_3"
            ]
        }
        self.initial_stage.json_schema = json.dumps(self.initial_stage.json_schema)
        self.initial_stage.save()

        correct_responses = {"q_1": "a", "q_2": "b", "q_3": "a"}
        task_correct_responses = self.complete_task(
            task_correct_responses,
            responses=correct_responses)
        Quiz.objects.create(
            task_stage=self.initial_stage,
            correct_responses_task=task_correct_responses
        )
        task = self.create_initial_task()
        responses = {"q_1": "a", "q_2": "c", "q_3": "c"}
        task = self.complete_task(task, responses=responses)

        self.assertEqual(task.responses["meta_quiz_score"], 33)
        self.assertEqual(task.responses["meta_quiz_incorrect_questions"], "Question 2\nQuestion 3")
        self.assertEqual(Task.objects.count(), 2)
        self.assertTrue(task.complete)

    def test_quiz_above_threshold(self):
        task_correct_responses = self.create_initial_task()
        correct_responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "d"}
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
            correct_responses_task=task_correct_responses,
            threshold=70
        )
        self.initial_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                assign_user_from_stage=self.initial_stage
            )
        )
        task = self.create_initial_task()
        responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "b"}
        task = self.complete_task(task, responses=responses)

        self.assertEqual(task.responses["meta_quiz_score"], 80)
        self.assertEqual(Task.objects.count(), 3)
        self.assertTrue(task.complete)

    def test_quiz_below_threshold(self):
        task_correct_responses = self.create_initial_task()
        correct_responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "d"}
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
            correct_responses_task=task_correct_responses,
            threshold=90
        )
        self.initial_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                assign_user_from_stage=self.initial_stage
            )
        )
        task = self.create_initial_task()
        responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "b"}
        task = self.complete_task(task, responses=responses)

        self.assertEqual(task.responses["meta_quiz_score"], 80)
        self.assertEqual(Task.objects.count(), 2)
        self.assertFalse(task.complete)

    def test_delete_stage_assign_by_ST(self):
        second_stage = self.initial_stage.add_stage(TaskStage(
            name="second_stage",
            assign_user_by="ST",
            assign_user_from_stage=self.initial_stage
        ))
        third_stage = second_stage.add_stage(TaskStage(
            name="third stage",
            assign_user_by="ST",
            assign_user_from_stage=second_stage
        ))

        self.assertEqual(TaskStage.objects.count(), 3)

        self.initial_stage.delete()

        self.assertEqual(TaskStage.objects.count(), 2)

    def test_response_flattener_new(self):
        response_falttener = ResponseFlattener(task_stage=self.initial_stage)
        self.assertEqual(response_falttener.task_stage, self.initial_stage)
        self.assertTrue(response_falttener.copy_first_level)
        self.assertFalse(response_falttener.flatten_all)
        self.assertFalse(response_falttener.copy_system_fields)
        self.assertEqual(response_falttener.exclude_list, [])
        self.assertEqual(response_falttener.columns, [])

    def test_response_flattener_list_wrong_not_manager(self):
        response = self.get_objects('responseflattener-list', client=self.client)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_response_flattener_list_happy(self):
        self.user.managed_campaigns.add(self.campaign)
        AdminPreference.objects.create(user=self.user, campaign=self.campaign)

        response_flattener = ResponseFlattener.objects.create(
            task_stage=self.initial_stage
        )

        response = self.get_objects('responseflattener-list', client=self.client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_flattener_retrieve_wrong_not_manager(self):
        response_flattener = ResponseFlattener.objects.create(
            task_stage=self.initial_stage
        )

        response = self.get_objects('responseflattener-detail', pk=response_flattener.id, client=self.client)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_response_flattener_retrieve_wrong_not_my_flattener(self):
        self.employee.managed_campaigns.add(self.campaign)
        AdminPreference.objects.create(user=self.employee, campaign=self.campaign)

        new_campaign = Campaign.objects.create(name="Another")

        self.user.managed_campaigns.add(new_campaign)
        AdminPreference.objects.create(user=self.user, campaign=self.campaign)

        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage)

        response = self.get_objects('responseflattener-detail', pk=response_flattener.id, client=self.client)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_response_flattener_retrieve_happy_my_flattener(self):
        self.user.managed_campaigns.add(self.campaign)
        AdminPreference.objects.create(user=self.user, campaign=self.campaign)

        response_flattener = ResponseFlattener.objects.create(
            task_stage=self.initial_stage
        )

        response = self.get_objects('responseflattener-detail', pk=response_flattener.id, client=self.client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_flattener_create_wrong(self):
        resp_flattener = {
            'task_stage': self.initial_stage.id,
        }

        response = self.client.post(reverse('responseflattener-list'), data=resp_flattener)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_response_flattener_create_happy(self):
        self.user.managed_campaigns.add(self.campaign)
        AdminPreference.objects.create(user=self.user, campaign=self.campaign)

        resp_flattener = {
            'task_stage': self.initial_stage.id,
        }

        response = self.client.post(reverse('responseflattener-list'), data=resp_flattener)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_response_flattener_update_wrong(self):
        resp_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True)
        self.assertTrue(resp_flattener.copy_first_level)

        response = self.client.patch(reverse('responseflattener-detail', kwargs={"pk": resp_flattener.id}),
                                     data={"copy_first_level": False})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp_flattener.copy_first_level)

    def test_response_flattener_update_happy(self):
        self.user.managed_campaigns.add(self.campaign)
        AdminPreference.objects.create(user=self.user, campaign=self.campaign)

        resp_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True)

        response = self.client.patch(reverse('responseflattener-detail', kwargs={"pk": resp_flattener.id}),
                                     {"copy_first_level": False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resp_flattener = ResponseFlattener.objects.get(id=resp_flattener.id)
        self.assertFalse(resp_flattener.copy_first_level)

    def test_response_flattener_create_row(self):
        task = self.create_initial_task()

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        responses = {"column1": "First", "column2": "SecondColumnt", "oik": {"uik1": "SecondLayer"}}
        row = {'id': task.id, 'column1': 'First', 'column2': 'SecondColumnt', 'oik__(i)uik': 'SecondLayer'}
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(i)uik"])

        task = self.complete_task(task, responses, self.client)

        flattener_row = response_flattener.flatten_response(task)
        self.assertEqual(row, flattener_row)

    def test_response_flattener_flatten_all(self):
        task = self.create_initial_task()

        self.initial_stage.json_schema = '{"properties":{"opening":{"15_c":{}, "16_c":{}, "17_c":{}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["opening"]}'
        self.initial_stage.save()

        answers = {"opening": {"15_c": "secured", "16_c": "no", "17_c": "no"}}
        task.responses = answers
        task.save()
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage,
                                                              flatten_all=True)

        result = response_flattener.flatten_response(task)
        self.assertEqual({"id":task.id, "opening__15_c": "secured", "opening__16_c": "no", "opening__17_c": "no"}, result)

    def test_response_flattener_regex_happy(self):
        task = self.create_initial_task()

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        responses = {"column1": "First", "column2": "SecondColumnt", "oik": {"uik1": "SecondLayer"}}
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(r)uik[\d]{1,2}"])

        task = self.complete_task(task, responses, self.client)

        result = response_flattener.flatten_response(task)
        self.employee.managed_campaigns.add(self.campaign)
        answer = {"id": task.id, "column1": "First", "column2": "SecondColumnt", "oik__(r)uik[\d]{1,2}": "SecondLayer"}

        self.assertEqual(answer, result)

    def test_response_flattener_regex_wrong(self):
        task = self.create_initial_task()

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        responses = {"column1": "First", "column2": "SecondColumnt", "oik": {"uik1": "SecondLayer"}}
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(r)ui[\d]{1,2}"])

        task = self.complete_task(task, responses, self.client)

        result = response_flattener.flatten_response(task)
        self.employee.managed_campaigns.add(self.campaign)
        answer = {"id":task.id, "column1": "First", "column2": "SecondColumnt"}

        self.assertEqual(answer, result)

    def test_get_response_flattener_success(self):
        task = self.create_initial_task()

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik__uik"]}'
        self.initial_stage.save()

        responses = {"column1": "First", "column2": "SecondColumnt", "oik": {"uik1": "SecondLayer"}}
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(i)uik", "dfasdf", "dfasdfasd"])

        task = self.complete_task(task, responses, self.client)

        self.employee.managed_campaigns.add(self.campaign)
        new_client = self.create_client(self.employee)

        params = {"response_flattener": response_flattener.id, "stage": self.initial_stage.id}
        response = self.get_objects("task-csv", params=params, client=new_client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_response_flattener_unique_success(self):
        task = self.create_initial_task()

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        responses = {"column1": "First", "column2": "SecondColumnt", "oik": {"uik1": "SecondLayer"}}
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(i)uik"])
        response_flattener_second = ResponseFlattener.objects.get_or_create(task_stage=self.initial_stage)

        self.assertEqual(ResponseFlattener.objects.count(), 1)

        task = self.complete_task(task, responses, self.client)

        self.employee.managed_campaigns.add(self.campaign)
        new_client = self.create_client(self.employee)

        params = {"response_flattener": response_flattener.id, "stage": self.initial_stage.id}
        response = self.get_objects("task-csv", params=params, client=new_client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_flattener_get_tasks_success(self):
        tasks = self.create_initial_tasks(5)

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        responses = {"column2": "SecondColumnt", "oik": {"uik1": "SecondLayer"}}
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, flatten_all=True)

        for i,t in enumerate(tasks):
            task = self.complete_task(t, responses, self.client)
            tasks[i] = task

        self.employee.managed_campaigns.add(self.campaign)
        new_client = self.create_client(self.employee)

        params = {"response_flattener": response_flattener.id}
        response = self.get_objects("task-csv", params=params, client=new_client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        r = {"column2": "SecondColumnt", "oik__uik1": "SecondLayer"}
        for t in tasks:
            r["id"] = t.id
            self.assertEqual(r, response_flattener.flatten_response(t))

    def test_get_response_flattener_copy_whole_response_success(self):
        task = self.create_task(self.initial_stage)

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        responses = {"column1": "First", "column2": "SecondColumnt", "oik": {"uik1": {"uik1": [322, 123, 23]}}}
        task.responses = responses
        task.save()
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, flatten_all=True)

        result = {'id': task.id, 'column1': 'First', 'column2': 'SecondColumnt', 'oik__uik1__uik1': [322, 123, 23]}
        self.assertEqual(response_flattener.flatten_response(task), result)

    def test_get_response_flattener_generate_file_url(self):

        task = self.create_task(self.initial_stage)
        self.initial_stage.ui_schema = '{"AAA":{"ui:widget":"customfile"},"ui:order": ["AAA"]}'
        self.initial_stage.json_schema = '{"properties":{"AAA": {"AAA":{}}}}'
        self.initial_stage.save()

        responses = {"AAA": '{"i":"public/img.jpg"}'}
        task.responses = responses
        task.save()
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, flatten_all=True)
        flattened_task = response_flattener.flatten_response(task)
        self.assertEqual(flattened_task, {"id":task.id, "AAA": "https://storage.cloud.google.com/gigaturnip-b6b5b.appspot.com/public/img.jpg?authuser=1"})


    def test_get_response_flattener_order_columns(self):

        task = self.create_task(self.initial_stage)
        self.initial_stage.ui_schema = '{"ui:order": ["BBB", "DDD", "AAA"]}'
        self.initial_stage.json_schema = '{"properties":{"AAA": {"AAA":{}}, "BBB": {"AAA":{}}, "DDD": {"properties": {"d": {"properties": {"d": {}}}}}}}'
        self.initial_stage.save()

        responses = {"BBB": "First", "AAA": "SecondColumnt", "DDD": {"d": {"d": 122}}}
        task.responses = responses
        task.save()
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, flatten_all=True)

        ordered_columns = response_flattener.ordered_columns()
        self.assertEqual(ordered_columns, ["id", "BBB", "DDD__d__d", "AAA"])

        # Testing system fields
        response_flattener.copy_system_fields = True
        response_flattener.save()
        ordered_columns = response_flattener.ordered_columns()
        system_columns = ["id", 'created_at', 'updated_at', 'assignee_id', 'stage_id', 'case_id',
                          'integrator_group', 'complete', 'force_complete', 'reopened', 'internal_metadata']
        responses_fields = ["BBB", "DDD__d__d", "AAA"]

        all_columns = system_columns + responses_fields
        self.assertEqual(ordered_columns, all_columns)
        flattened_task = response_flattener.flatten_response(task)
        for i in system_columns:
            self.assertEqual(task.__getattribute__(i), flattened_task[i])

    def test_response_flattener_with_previous_names(self):
        tasks = self.create_initial_tasks(5)
        self.employee.managed_campaigns.add(self.campaign)
        new_client = self.create_client(self.employee)

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        responses = {"column2": "SecondColumnt", "oik": {"uik1": "SecondLayer"}}
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, flatten_all=True)

        for i,t in enumerate(tasks[:3]):
            task = self.complete_task(t, responses, self.client)
            tasks[i] = task

        for i, t in enumerate(tasks[3:]):
            responses['another'] = "field not in schema"
            task = self.complete_task(t, responses, self.client)
            tasks[i+3] = task

        params = {"response_flattener": response_flattener.id}
        response = self.get_objects("task-csv", params=params, client=new_client)
        columns = response.content.decode().split("\r\n", 1)[0].split(',')
        self.assertEqual(columns, ['id', 'column2', 'column1', 'oik__uik1', 'description'])

        response_flattener.columns = ['another']
        response_flattener.save()

        response = self.get_objects("task-csv", params=params, client=new_client)
        columns = response.content.decode().split("\r\n", 1)[0].split(',')
        self.assertEqual(columns, ['id', 'another','column2', 'column1', 'oik__uik1'])

    def test_get_response_flattener_fail(self):
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(i)uik"])

        new_client = self.create_client(self.employee)
        params = {"response_flattener": response_flattener.id, "stage": self.initial_stage.id}
        response = self.get_objects("task-csv", params=params, client=new_client)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_response_flattener_not_found(self):

        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(i)uik"])

        params = {"response_flattener": response_flattener.id+111, "stage": 234}
        response = self.get_objects("task-csv", params=params)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_user_activity_csv_fail(self):
        self.create_initial_tasks(5)
        response = self.client.get(reverse('task-user-activity-csv')+"?csv=22")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logs_for_task_stages(self):
        old_count = Log.objects.count()
        self.user.managed_campaigns.add(self.campaign)

        update_js = {"name": "Rename stage"}
        url = reverse("taskstage-detail", kwargs={"pk": self.initial_stage.id})
        response = self.client.patch(url, update_js)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(old_count, 0)
        self.assertEqual(Log.objects.count(), 1)

    def test_task_awards_count_is_equal(self):
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
        verification_task_stage = self.initial_stage.add_stage(TaskStage(
            name='verification',
            assign_user_by="RA"
        ))
        verification_task_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "decision": {
                    "enum": ["reject", "pass"],
                    "title": "Question 1",
                    "type": "string"
                }
            },
            "required": [
                "decision"
            ]
        })
        verification_task_stage.save()

        verifier_rank = Rank.objects.create(name="verifier")
        RankRecord.objects.create(
            user=self.employee,
            rank=Rank.objects.get(name="Initial"))
        RankRecord.objects.create(
            user=self.user,
            rank=verifier_rank)

        prize_rank = Rank.objects.create(name="SUPERMAN")
        notification = Notification.objects.create(
            title="You achieve new rank",
            text="Congratulations! You achieve new rank!",
            campaign=self.campaign
        )
        task_awards = TaskAward.objects.create(
            task_stage_completion=self.initial_stage,
            task_stage_verified=verification_task_stage,
            rank=prize_rank,
            count=3,
            notification=notification
        )

        rank_l = RankLimit.objects.create(
            rank=verifier_rank,
            stage=verification_task_stage,
            open_limit=5,
            total_limit=0,
            is_creation_open=False,
            is_listing_allowed=True,
            is_selection_open=True,
            is_submission_open=True)

        for i in range(3):
            task = self.create_task(self.initial_stage, self.employee_client)
            task = self.complete_task(task, {"answer": "norm"}, self.employee_client)

            response_assign = self.get_objects("task-request-assignment", pk=task.out_tasks.all()[0].id)
            self.assertEqual(response_assign.status_code, status.HTTP_200_OK)
            task_to_check = Task.objects.get(assignee=self.user, case=task.case)
            task_to_check = self.complete_task(task_to_check, {"decision": "pass"}, client=self.client)

        employee_ranks = [i.rank for i in RankRecord.objects.filter(user=self.employee)]
        self.assertEqual(len(employee_ranks), 2)
        self.assertIn(prize_rank, employee_ranks)

        user_notifications = Notification.objects.filter(target_user=self.employee, title=task_awards.notification.title)
        self.assertEqual(user_notifications.count(), 1)

    def test_task_awards_count_is_lower(self):
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

        verification_task_stage = self.initial_stage.add_stage(TaskStage(
            name='verification',
            assign_user_by="RA"
        ))
        verification_task_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "decision": {
                    "enum": ["reject", "pass"],
                    "title": "Question 1",
                    "type": "string"
                }
            },
            "required": [
                "decision"
            ]
        })
        verification_task_stage.save()

        verifier_rank = Rank.objects.create(name="verifier")
        RankRecord.objects.create(
            user=self.employee,
            rank=Rank.objects.get(name="Initial"))
        RankRecord.objects.create(
            user=self.user,
            rank=verifier_rank)

        prize_rank = Rank.objects.create(name="SUPERMAN")
        notification = Notification.objects.create(
            title="You achieve new rank",
            text="Congratulations! You achieve new rank!",
            campaign=self.campaign
        )
        task_awards = TaskAward.objects.create(
            task_stage_completion=self.initial_stage,
            task_stage_verified=verification_task_stage,
            rank=prize_rank,
            count=3,
            notification=notification
        )

        rank_l = RankLimit.objects.create(
            rank=verifier_rank,
            stage=verification_task_stage,
            open_limit=5,
            total_limit=0,
            is_creation_open=False,
            is_listing_allowed=True,
            is_selection_open=True,
            is_submission_open=True)

        for i in range(2):
            task = self.create_task(self.initial_stage, self.employee_client)
            task = self.complete_task(task, {"answer": "norm"}, client=self.employee_client)

            response_assign = self.get_objects("task-request-assignment", {"decision": "pass"},
                                               pk=task.out_tasks.all()[0].id)
            self.assertEqual(response_assign.status_code, status.HTTP_200_OK)
            task_to_check = Task.objects.get(assignee=self.user, case=task.case)
            task_to_check = self.complete_task(task_to_check, {"decision": "pass"}, client=self.client)

        employee_ranks = [i.rank for i in RankRecord.objects.filter(user=self.employee)]
        self.assertEqual(len(employee_ranks), 1)
        self.assertNotIn(prize_rank, employee_ranks)

        user_notifications = Notification.objects.filter(target_user=self.employee, title=task_awards.notification.title)
        self.assertEqual(user_notifications.count(), 0)

    def test_task_awards_count_many_task_stages(self):
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

        second_task_stage = self.initial_stage.add_stage(TaskStage(
            name='Second stage',
            json_schema=self.initial_stage.json_schema,
            assign_user_by="ST",
            assign_user_from_stage=self.initial_stage))
        verification_task_stage = second_task_stage.add_stage(TaskStage(
            name='verification',
            assign_user_by="RA"
        ))
        verification_task_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "decision": {
                    "enum": ["reject", "pass"],
                    "title": "Question 1",
                    "type": "string"
                }
            },
            "required": [
                "decision"
            ]
        })
        verification_task_stage.save()

        verifier_rank = Rank.objects.create(name="verifier")
        RankRecord.objects.create(
            user=self.employee,
            rank=Rank.objects.get(name="Initial"))
        RankRecord.objects.create(
            user=self.user,
            rank=verifier_rank)

        prize_rank = Rank.objects.create(name="SUPERMAN")
        notification = Notification.objects.create(
            campaign=self.campaign,
            title="You achieve new rank",
            text="Congratulations! You achieve new rank!"
        )
        task_awards = TaskAward.objects.create(
            task_stage_completion=self.initial_stage,
            task_stage_verified=verification_task_stage,
            rank=prize_rank,
            count=3,
            notification=notification
        )

        rank_l = RankLimit.objects.create(
            rank=verifier_rank,
            stage=verification_task_stage,
            open_limit=5,
            total_limit=0,
            is_creation_open=False,
            is_listing_allowed=True,
            is_selection_open=True,
            is_submission_open=True)

        for i in range(3):
            task = self.create_task(self.initial_stage, self.employee_client)
            task = self.complete_task(task, {"answer": "norm"}, client=self.employee_client)
            task_2 = task.out_tasks.all()[0]
            task_2 = self.complete_task(task_2, {"answer": "norm2"}, client=self.employee_client)

            response_assign = self.get_objects("task-request-assignment", {"decision": "pass"},
                                               pk=task_2.out_tasks.all()[0].id)
            self.assertEqual(response_assign.status_code, status.HTTP_200_OK)
            task_to_check = Task.objects.get(assignee=self.user, case=task.case)
            task_to_check = self.complete_task(task_to_check, {"decision": "pass"}, client=self.client)

        employee_ranks = [i.rank for i in RankRecord.objects.filter(user=self.employee)]
        self.assertEqual(len(employee_ranks), 2)
        self.assertIn(prize_rank, employee_ranks)

        user_notifications = Notification.objects.filter(target_user=self.employee, title=task_awards.notification.title)
        self.assertEqual(user_notifications.count(), 1)

    def test_task_awards_for_giving_ranks(self):
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
        conditional_stage = ConditionalStage()
        conditional_stage.conditions = [
            {"field": "answer", "value": "norm", "condition": "=="}
        ]
        conditional_stage = self.initial_stage.add_stage(conditional_stage)
        verification_task_stage = conditional_stage.add_stage(TaskStage(
            name='verification',
            assign_user_by="AU"
        ))
        verification_task_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "decision": {
                    "enum": ["reject", "pass"],
                    "title": "Question 1",
                    "type": "string"
                }
            },
            "required": [
                "decision"
            ]
        })
        verification_task_stage.save()

        verifier_rank = Rank.objects.create(name="verifier")
        RankRecord.objects.create(
            user=self.employee,
            rank=Rank.objects.get(name="Initial"))
        RankRecord.objects.create(
            user=self.user,
            rank=verifier_rank)

        prize_rank = Rank.objects.create(name="SUPERMAN")
        notification = Notification.objects.create(
            title="You achieve new rank",
            text="Congratulations! You achieve new rank!",
            campaign=self.campaign
        )
        task_awards = TaskAward.objects.create(
            task_stage_completion=self.initial_stage,
            task_stage_verified=verification_task_stage,
            rank=prize_rank,
            count=3,
            notification=notification
        )

        rank_l = RankLimit.objects.create(
            rank=verifier_rank,
            stage=verification_task_stage,
            open_limit=5,
            total_limit=0,
            is_creation_open=False,
            is_listing_allowed=True,
            is_selection_open=True,
            is_submission_open=True)

        for i in range(3):
            task = self.create_task(self.initial_stage, self.employee_client)
            task = self.complete_task(task, {"answer": "norm"}, self.employee_client)

            # response_assign = self.get_objects("task-request-assignment", pk=task.out_tasks.all()[0].id)
            # self.assertEqual(response_assign.status_code, status.HTTP_200_OK)
            # task_to_check = Task.objects.get(assignee=self.user, case=task.case)
            # task_to_check = self.complete_task(task_to_check, {"decision": "pass"}, client=self.client)

        employee_ranks = [i.rank for i in RankRecord.objects.filter(user=self.employee)]
        self.assertEqual(len(employee_ranks), 2)
        self.assertIn(prize_rank, employee_ranks)

        user_notifications = Notification.objects.filter(target_user=self.employee, title=task_awards.notification.title)
        self.assertEqual(user_notifications.count(), 1)

    def test_task_stage_get_schema_fields(self):
        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        response = self.get_objects('taskstage-schema-fields', pk=self.initial_stage.id)
        self.assertEqual(response.data['fields'], ['column2', 'column1', 'oik__uik1'])

    def test_search_by_responses_by_previous_stage(self):
        self.user.managed_campaigns.add(self.campaign)

        js_schema =  '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        ui_schema =  '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(TaskStage())
        second_stage.json_schema = js_schema
        second_stage.ui_schema = ui_schema
        second_stage.save()


        task = self.create_initial_task()
        responses = {"column1": "2022-04-03T03:20:00.974Z", "column2": "SecondColumnt", "oik": {"uik1": "SecondLayer"}}
        task = self.complete_task(task, responses)

        second_task = self.create_initial_task()
        new_resp = responses
        new_resp['column2'] = 'Hello world!'
        second_task = self.complete_task(second_task, new_resp)

        conditions = {
            "all_conditions":
                [
                    {
                        "conditions": [
                            {
                                "operator": "==",
                                "value": "SecondColumnt"
                            }
                        ],
                        "field": "column2"
                    }
                ],
            "stage": self.initial_stage.id,
            "search_stage": second_stage.id
        }

        responses_conditions = {'task_responses': json.dumps(conditions)}
        response = self.get_objects('task-list', params=responses_conditions)
        response_data = json.loads(response.content)

        self.assertEqual(len(response_data['results']), 1)
        expected_task = Task.objects.filter(in_tasks__in=[task.id], stage=second_stage)[0]
        self.assertEqual(response_data['results'][0]['id'], expected_task.id)

    def test_user_activity_on_stages(self):
        tasks = self.create_initial_tasks(5)

        expected_activity = {
            'stage': self.initial_stage.id,
            'stage__name': self.initial_stage.name,
            'ranks': [i['id'] for i in self.initial_stage.ranks.all().values('id')],
            'in_stages': [i['id'] for i in self.initial_stage.in_stages.all().values('id')],
            'out_stages': [i['id'] for i in self.initial_stage.out_stages.all().values('id')],
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
        # todo: it will fail if your database isn't postgres. because of dj.func ArrayAgg
        self.assertEqual(list(response.data), [expected_activity])

    def test_search_by_responses_gte_lte(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "column1": {
                    "title": "Question 1",
                    "type": "string"
                },
                "column2": {
                    "title": "Question 2",
                    "type": "string"
                },
                "oik": {
                    "type": "object",
                    "title": "Question 3",
                    "properties": {
                        "uik1": {
                            "type": "string"
                        }
                    }
                }
            },
            "required": [
                "column1",
                "column2",
                "oik"
            ]
        })
        self.initial_stage.save()
        self.user.managed_campaigns.add(self.campaign)

        responses = {
            "column1": "3000",
            "column2": "SecondColumnt",
            "oik": {"uik1": "SecondLayer"}
        }

        task = self.create_initial_task()
        task = self.complete_task(task, responses)

        task1 = self.create_initial_task()
        responses_1 = responses
        responses_1['column1'] = '2990'
        task1 = self.complete_task(task1, responses_1)

        task2 = self.create_initial_task()
        responses_2 = responses
        responses_2['column1'] = '3001'
        task2 = self.complete_task(task2, responses_2)

        conditions = {
            "all_conditions":
                [
                    {
                        "conditions": [
                            {
                                "operator": "<=",
                                "value": "3000"
                            }
                        ],
                        "field": "column1"
                    }
                ],
            "stage": self.initial_stage.id
        }

        responses_conditions = {'task_responses': json.dumps(conditions)}
        response = self.get_objects('task-list', params=responses_conditions)
        response_data = json.loads(response.content)

        self.assertEqual(len(response_data['results']), 2)
        for i in response_data['results']:
            self.assertIn(i['id'], [task.id, task1.id])

    def test_answers_validation(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "price": {"type": "number"},
                "year": {"type": "number"},
                "name": {"type": "string"},
            },
            "required":['price', 'name']
        })
        self.initial_stage.save()

        task = self.create_initial_task()
        response = self.complete_task(task, {'price': 'there must be digit',
                                             'year': 'there must be digit',
                                             'name': 'Kloop'}
                                      )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(json.loads(response.content)['pass'], ["properties", "price", "type"])

    def test_dynamic_json_schema_related_fields(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        time_slots = ['10:00', '11:00', '12:00', '13:00', '14:00']
        doctors = ['Rinat', 'Aizirek', 'Aigerim', 'Beka']
        alphabet = ['a', 'b', 'c', 'd']
        js_schema = json.dumps({
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                },
                "time": {
                    "type": "string",
                    "title": "What time",
                    "enum": time_slots
                }
            }
        })
        ui_schema = json.dumps({"ui:order": ["time"]})
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_json = {
            "main": "weekday",
            "foreign": ['time'],
            "count": 2
        }
        dynamic_json = DynamicJson.objects.create(
            task_stage=self.initial_stage,
            dynamic_fields=dynamic_fields_json
        )

        task1 = self.create_initial_task()
        responses1 = {'weekday': weekdays[0], 'time': time_slots[0]}
        task1 = self.complete_task(task1, responses1)

        task2 = self.create_initial_task()
        task2 = self.complete_task(task2, responses1)

        task3 = self.create_initial_task()
        responses3 = {'weekday': weekdays[0]}

        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id, params={'responses': json.dumps(responses3)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_schema = json.loads(js_schema)
        del updated_schema['properties']['time']['enum'][0]
        self.assertEqual(response.data['schema'], updated_schema)

        responses3['weekday'] = weekdays[1]
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id, params={'responses': json.dumps(responses3)})
        updated_schema = json.loads(js_schema)
        self.assertEqual(response.data['schema'], updated_schema)

    def test_dynamic_json_schema_single_field(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        js_schema = json.dumps({
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                }
            }
        })
        ui_schema = json.dumps({"ui:order": ["time"]})
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_json = {
            "main": "weekday",
            "foreign": [],
            "count": 2
        }
        dynamic_json = DynamicJson.objects.create(
            task_stage=self.initial_stage,
            dynamic_fields=dynamic_fields_json
        )

        responses1 = {'weekday': weekdays[0]}

        task1 = self.create_initial_task()
        task1 = self.complete_task(task1, responses1)

        task2 = self.create_initial_task()
        task2 = self.complete_task(task2, responses1)

        task3 = self.create_initial_task()
        responses3 = {'weekday': weekdays[0]}

        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id, params={'responses': json.dumps(responses3)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_schema = json.loads(js_schema)
        del updated_schema['properties']['weekday']['enum'][0]
        self.assertEqual(response.data['schema'], updated_schema)

        responses3['weekday'] = weekdays[1]
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id, params={'responses': json.dumps(responses3)})
        self.assertEqual(response.data['schema'], updated_schema)

    def test_dynamic_json_schema_single_unique_field(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        js_schema = json.dumps({
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                }

            }
        })
        ui_schema = json.dumps({"ui:order": ["weekday"]})
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_weekday = {
            "main": "weekday",
            "foreign": [],
            "count": 2
        }
        dynamic_json_weekday = DynamicJson.objects.create(
            task_stage=self.initial_stage,
            dynamic_fields=dynamic_fields_weekday
        )

        responses1 = {'weekday': weekdays[0]}

        task1 = self.create_initial_task()
        task1 = self.complete_task(task1, responses1)

        task2 = self.create_initial_task()
        task2 = self.complete_task(task2, responses1)

        task3 = self.create_initial_task()
        responses3 = {'weekday': weekdays[0]}

        updated_schema = json.loads(js_schema)
        del updated_schema['properties']['weekday']['enum'][0]
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['schema'], updated_schema)

        response = self.complete_task(task3, responses3)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'][0], 'Your answers are non-compliance with the standard')
        self.assertEqual(response.data['pass'], ['properties', 'weekday', 'enum'])

    def test_dynamic_json_schema_related_unique_fields(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        time_slots = ['10:00', '11:00', '12:00', '13:00', '14:00']
        js_schema = json.dumps({
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                },
                "time": {
                    "type": "string",
                    "title": "What time",
                    "enum": time_slots
                }
            }
        })
        ui_schema = json.dumps({"ui:order": ["time"]})
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_json = {
            "main": "weekday",
            "foreign": ['time'],
            "count": 1
        }
        dynamic_json = DynamicJson.objects.create(
            task_stage=self.initial_stage,
            dynamic_fields=dynamic_fields_json
        )

        for t in time_slots:
            task = self.create_initial_task()
            responses = {'weekday': weekdays[0], 'time': t}
            self.complete_task(task, responses)

        task = self.create_initial_task()

        responses = {'weekday': weekdays[0]}
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id, params={'responses': json.dumps(responses)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_schema = json.loads(js_schema)
        updated_schema['properties']['time']['enum'] = []
        self.assertEqual(response.data['schema'], updated_schema)

        responses = {'weekday': weekdays[1]}
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id, params={'responses': json.dumps(responses)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_schema = json.loads(js_schema)
        self.assertEqual(response.data['schema'], updated_schema)

    def test_dynamic_json_schema_three_foreign(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        time_slots = ['10:00', '11:00', '12:00', '13:00', '14:00']
        doctors = ['Rinat', 'Aizirek', 'Aigerim', 'Beka']
        alphabet = ['a', 'b', 'c', 'd']
        js_schema = json.dumps({
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                },
                "time": {
                    "type": "string",
                    "title": "What time",
                    "enum": time_slots
                },
                "doctor": {
                    "type": "string",
                    "title": "Which doctor",
                    "enum": doctors
                },
                "alphabet": {
                    "type": "string",
                    "title": "Which doctor",
                    "enum": alphabet
                }
            }
        })
        ui_schema = json.dumps({"ui:order": ["time"]})
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_json = {
            "main": "weekday",
            "foreign": ["time", "doctor", "alphabet"],
            "count": 1
        }
        dynamic_json = DynamicJson.objects.create(
            task_stage=self.initial_stage,
            dynamic_fields=dynamic_fields_json
        )

        task = self.create_initial_task()
        responses = {'weekday': weekdays[0], 'time': time_slots[0], 'doctor': doctors[0], 'alphabet': alphabet[0]}
        self.complete_task(task, responses)

        task = self.create_initial_task()
        responses = {'weekday': weekdays[0], 'time': time_slots[0], 'doctor': doctors[0]}
        updated_schema = json.loads(js_schema)
        del updated_schema['properties']['alphabet']['enum'][0]
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses)})

        self.assertEqual(response.data['schema'], updated_schema)

        responses = {'weekday': weekdays[0], 'time': time_slots[0], 'doctor': doctors[1]}
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses)})
        updated_schema = json.loads(js_schema)
        self.assertEqual(response.data['schema'], updated_schema)

        responses = {'weekday': weekdays[1], 'time': time_slots[0], 'doctor': doctors[0]}
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses)})
        updated_schema = json.loads(js_schema)
        self.assertEqual(response.data['schema'], updated_schema)

        responses = {'weekday': weekdays[0], 'time': time_slots[1], 'doctor': doctors[0]}
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses)})
        updated_schema = json.loads(js_schema)
        self.assertEqual(response.data['schema'], updated_schema)


    def test_dynamic_json_schema_many(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        day_parts = ['12:00 - 13:00', '13:00 - 14:00',  '14:00 - 15:00']
        js_schema = json.dumps({
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                },
                "day_part": {
                    "type": "string",
                    "title": "Select part of the day",
                    "enum": day_parts
                },

            }
        })
        ui_schema = json.dumps({"ui:order": ["time"]})
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_weekday = {
            "main": "weekday",
            "foreign": [],
            "count": 2
        }
        dynamic_json_weekday = DynamicJson.objects.create(
            task_stage=self.initial_stage,
            dynamic_fields=dynamic_fields_weekday
        )

        dynamic_fields_day_parts = {
            "main": "day_part",
            "foreign": [],
            "count": 2
        }
        dynamic_json_day_part = DynamicJson.objects.create(
            task_stage=self.initial_stage,
            dynamic_fields=dynamic_fields_day_parts
        )

        responses1 = {'weekday': weekdays[0], 'day_part': day_parts[0]}

        task1 = self.create_initial_task()
        task1 = self.complete_task(task1, responses1)

        task2 = self.create_initial_task()
        task2 = self.complete_task(task2, responses1)

        task3 = self.create_initial_task()
        responses3 = {'weekday': weekdays[0], 'day_part': day_parts[0]}

        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_schema = json.loads(js_schema)
        del updated_schema['properties']['weekday']['enum'][0]
        del updated_schema['properties']['day_part']['enum'][0]
        self.assertEqual(response.data['schema'], updated_schema)

        responses3['weekday'] = weekdays[1]
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id, params={'responses': json.dumps(responses3)})
        self.assertEqual(response.data['schema'], updated_schema)

    def test_update_taskstage(self):
        external_metadata = {"field":"value"}
        self.initial_stage.external_metadata = external_metadata
        self.initial_stage.save()
        response = self.get_objects('taskstage-detail', pk=self.initial_stage.id)
        self.assertEqual(response.data['external_metadata'], external_metadata)

    def test_dynamic_json_schema_webhook(self):
        js_schema = json.dumps({
            "type": "object",
            "title": "My form",
            "properties": {},
            "dependencies": {}}
        )

        ui_schema = json.dumps({"ui:order": ["time"]})
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_json = {
            "foreign": ['oblast', 'rayon', 'aymak', 'villages'],
        }

        webhook = Webhook.objects.create(
            task_stage=self.initial_stage,
            url='https://us-central1-valiant-cycle-353908.cloudfunctions.net/test_function',
            is_triggered=False,
            headers={"link": "https://storage.googleapis.com/media_journal_bucket/regions_data.xls", "sheet": "Sheet1"}
        )

        dynamic_json = DynamicJson.objects.create(
            task_stage=self.initial_stage,
            dynamic_fields=dynamic_fields_json,
            webhook=webhook
        )
        task = self.create_initial_task()

        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id)
        self.assertNotEqual(response.data['schema'], self.initial_stage.json_schema)

    def test_dynamic_json_schema_try_to_complete_occupied_answer(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        time_slots = ['10:00', '11:00', '12:00', '13:00', '14:00']
        js_schema = json.dumps({
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                },
                "time": {
                    "type": "string",
                    "title": "What time",
                    "enum": time_slots
                }
            }
        })
        ui_schema = json.dumps({"ui:order": ["time"]})
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_json = {
            "main": "weekday",
            "foreign": ['time'],
            "count": 1
        }
        dynamic_json = DynamicJson.objects.create(
            task_stage=self.initial_stage,
            dynamic_fields=dynamic_fields_json
        )

        task = self.create_initial_task()
        responses = {'weekday': weekdays[0], 'time': time_slots[0]}
        self.complete_task(task, responses)

        task = self.create_initial_task()

        responses = {'weekday': weekdays[0], 'time': time_slots[0]}
        response = self.complete_task(task, responses)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        responses['time'] = time_slots[1]
        task = self.complete_task(task, responses)
        self.assertEqual(task.responses, responses)
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
             'force_complete': [False], 'id':[task.id]},
            {'stage': second_stage.id, 'stage__name': second_stage.name, 'complete': [False], 'force_complete': [False],
             'id':[task.out_tasks.get().id]}
        ]

        self.assertEqual(status.HTTP_200_OK, response.data['status'])
        for i in maps_info:
            self.assertIn(i, response.data['info'])

    def test_chain_get_graph(self):
        self.user.managed_campaigns.add(self.campaign)
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name='Second Task Stage',
                assign_user_by='ST',
                assign_user_from_stage=self.initial_stage,
            )
        )
        cond_stage = second_stage.add_stage(
            ConditionalStage(
                name="MyCondStage",
                conditions=[{"field": "foo", "value": "boo", "condition": "=="}]
            )
        )

        info_about_graph = [
            {'pk': self.initial_stage.id, 'name': self.initial_stage.name, 'in_stages': [None],
             'out_stages': [second_stage.id]},
            {'pk': second_stage.id, 'name': second_stage.name, 'in_stages': [self.initial_stage.id],
             'out_stages': [cond_stage.id]},
            {'pk': cond_stage.id, 'name': cond_stage.name, 'in_stages': [second_stage.id], 'out_stages': [None]}
        ]

        response = self.get_objects("chain-get-graph", pk=self.chain.id)
        self.assertEqual(len(response.data), 3)
        for i in info_about_graph:
            self.assertIn(i, response.data)

    def test_assign_by_previous_manual_user_without_rank(self):
        js_schema = {
                "type": "object",
                "properties": {
                    "email_field": {
                        "type": "string",
                        "title": "email to assign",
                    }
                }
            }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        second_stage_schema = {
                "type": "object",
                "properties": {
                    "foo": {
                        "type": "string",
                        "title": "what is ur name",
                    }
                }
            }
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name='Second stage',
                assign_user_by=TaskStage.PREVIOUS_MANUAL,
                json_schema=json.dumps(second_stage_schema)
            )
        )

        PreviousManual.objects.create(
            field=["email_field"],
            task_stage_to_assign=second_stage,
            task_stage_email=self.initial_stage,
        )

        responses = {"email_field": "employee@email.com"}
        task = self.create_initial_task()
        bad_response = self.complete_task(task, responses)

        self.assertEqual(bad_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad_response.data['message'], 'User is not in the campaign.')

    def test_assign_by_previous_manual_user_with_rank_of_campaign(self):
        js_schema = {
                "type": "object",
                "properties": {
                    "email_field": {
                        "type": "string",
                        "title": "email to assign",
                    }
                }
            }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        second_stage_schema = {
                "type": "object",
                "properties": {
                    "foo": {
                        "type": "string",
                        "title": "what is ur name",
                    }
                }
            }
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name='Second stage',
                assign_user_by=TaskStage.PREVIOUS_MANUAL,
                json_schema=json.dumps(second_stage_schema)
            )
        )

        PreviousManual.objects.create(
            field=["email_field"],
            task_stage_to_assign=second_stage,
            task_stage_email=self.initial_stage,
        )

        campaign_rank = RankLimit.objects.filter(stage__chain__campaign_id=self.campaign)[0].rank
        self.employee.ranks.add(campaign_rank)

        responses = {"email_field": "employee@email.com"}
        task = self.create_initial_task()
        task = self.complete_task(task, responses)

        new_task = Task.objects.get(stage=second_stage, case=task.case)

        self.assertEqual(new_task.assignee, CustomUser.objects.get(email='employee@email.com'))

    def test_assign_by_previous_manual_conditional_previous_happy(self):
        js_schema = {
                "type": "object",
                "properties": {
                    "email_field": {
                        "type": "string",
                        "title": "email to assign",
                    },
                    'foo':{
                        "type": "string",
                    }
                }
            }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        conditional_stage = self.initial_stage.add_stage(ConditionalStage(
            conditions=[{"field": "foo", "value": "boo", "condition": "=="}]
        ))

        final_stage_schema = {
                "type": "object",
                "properties": {
                    "foo": {
                        "type": "string",
                        "title": "what is ur name",
                    }
                }
            }
        final_stage = conditional_stage.add_stage(
            TaskStage(
                name='Final stage',
                assign_user_by=TaskStage.PREVIOUS_MANUAL,
                json_schema=json.dumps(final_stage_schema)
            )
        )

        PreviousManual.objects.create(
            field=["email_field"],
            task_stage_to_assign=final_stage,
            task_stage_email=self.initial_stage,
        )

        campaign_rank = RankLimit.objects.filter(stage__chain__campaign_id=self.campaign)[0].rank
        self.employee.ranks.add(campaign_rank)

        responses = {"email_field": "employee@email.com", "foo": "boo"}
        task = self.create_initial_task()
        task = self.complete_task(task, responses)
        new_task = Task.objects.get(stage=final_stage, case=task.case)

        self.assertEqual(new_task.assignee, CustomUser.objects.get(email='employee@email.com'))

    def test_assign_by_previous_manual_conditional_previous_wrong_no_rank(self):
        js_schema = {
                "type": "object",
                "properties": {
                    "email_field": {
                        "type": "string",
                        "title": "email to assign",
                    },
                    'foo':{
                        "type": "string",
                    }
                }
            }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        conditional_stage = self.initial_stage.add_stage(ConditionalStage(
            conditions=[{"field": "foo", "value": "boo", "condition": "=="}]
        ))

        final_stage_schema = {
                "type": "object",
                "properties": {
                    "foo": {
                        "type": "string",
                        "title": "what is ur name",
                    }
                }
            }
        final_stage = conditional_stage.add_stage(
            TaskStage(
                name='Final stage',
                assign_user_by=TaskStage.PREVIOUS_MANUAL,
                json_schema=json.dumps(final_stage_schema)
            )
        )

        PreviousManual.objects.create(
            field=["email_field"],
            task_stage_to_assign=final_stage,
            task_stage_email=self.initial_stage,
        )

        responses = {"email_field": "employee@email.com", "foo": "boo"}
        task = self.create_initial_task()
        bad_response = self.complete_task(task, responses)

        task = Task.objects.get(id=task.id)

        self.assertEqual(bad_response.data['message'], 'User is not in the campaign.')
        self.assertTrue(task.reopened)
        self.assertFalse(task.complete)
        self.assertEqual(Task.objects.count(), 1)

    def test_assign_by_previous_manual_conditional_previous_wrong_user_does_not_exist(self):
        js_schema = {
                "type": "object",
                "properties": {
                    "email_field": {
                        "type": "string",
                        "title": "email to assign",
                    },
                    'foo':{
                        "type": "string",
                    }
                }
            }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        conditional_stage = self.initial_stage.add_stage(ConditionalStage(
            conditions=[{"field": "foo", "value": "boo", "condition": "=="}]
        ))

        final_stage_schema = {
                "type": "object",
                "properties": {
                    "foo": {
                        "type": "string",
                        "title": "what is ur name",
                    }
                }
            }
        final_stage = conditional_stage.add_stage(
            TaskStage(
                name='Final stage',
                assign_user_by=TaskStage.PREVIOUS_MANUAL,
                json_schema=json.dumps(final_stage_schema)
            )
        )

        PreviousManual.objects.create(
            field=["email_field"],
            task_stage_to_assign=final_stage,
            task_stage_email=self.initial_stage,
        )

        responses = {"email_field": "employe@email.com", "foo": "boo"}
        task = self.create_initial_task()
        bad_response = self.complete_task(task, responses)

        task = Task.objects.get(id=task.id)

        self.assertEqual(bad_response.data['message'], 'User employe@email.com doesn\'t exist')
        self.assertTrue(task.reopened)
        self.assertFalse(task.complete)
        self.assertEqual(Task.objects.count(), 1)

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
                assign_user_by=TaskStage.STAGE,
                assign_user_from_stage=self.initial_stage
            )
        )

        conditional_stage = second_stage.add_stage(ConditionalStage(
            conditions=[{"field": "foo", "value": "boo", "condition": "=="}]
        ))

        conditional_stage_cyclic = second_stage.add_stage(ConditionalStage(
            conditions=[{"field": "foo", "value": "boo", "condition": "!="}]
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
                assign_user_by=TaskStage.STAGE,
                json_schema=json.dumps(final_stage_schema)
            )
        )

        conditional_stage_cyclic.out_stages.add(second_stage)
        conditional_stage_cyclic.save()

        return second_stage, conditional_stage, conditional_stage_cyclic, final_stage

    def test_cyclic_chain_ST(self):
        second_stage, conditional_stage, conditional_stage_cyclic, final_stage = self.create_cyclic_chain()

        task = self.create_initial_task()
        task = self.complete_task(task, {"name": "Kloop"})

        second_task_1 = task.out_tasks.get()
        second_task_1 = self.complete_task(second_task_1, {"foo": "not right"})
        self.assertEqual(Task.objects.filter(case=task.case).count(), 3)
        self.assertEqual(Task.objects.filter(case=task.case, stage=second_stage).count(), 2)

        second_task_2 = second_task_1.out_tasks.get()

        response = self.get_objects('case-info-by-case',pk=task.case.id)
        info_by_case = [
            {'stage': self.initial_stage.id, 'stage__name': 'Initial', 'complete': [True], 'force_complete': [False], 'id': [task.id]},
            {'stage': second_stage.id, 'stage__name': 'Test pronunciation', 'complete': [False, True], 'force_complete': [False, False],
             'id': [second_task_2.id, second_task_1.id]}
        ]
        self.assertEqual(len(response.data['info']), 2)
        for i in info_by_case:
            self.assertIn(i, response.data['info'])

        second_task_2 = self.complete_task(second_task_2, {"foo": "boo"})
        self.assertEqual(Task.objects.filter(case=task.case).count(), 4)
        self.assertEqual(Task.objects.filter(case=task.case, stage=second_stage).count(), 2)
        self.assertEqual(Task.objects.filter(case=task.case, stage=final_stage).count(), 1)

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
                assign_user_by=TaskStage.RANK,
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
            conditions=[{"field": "foo", "value": "boo", "condition": "=="}]
        ))

        conditional_stage_cyclic = second_stage.add_stage(ConditionalStage(
            conditions=[{"field": "foo", "value": "boo", "condition": "!="}]
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
                assign_user_by=TaskStage.STAGE,
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
                webhook_address='https://us-central1-valiant-cycle-353908.cloudfunctions.net/random_int_between_0_9'
            )
        )
        """
        create_task_webhook = Webhook.objects.create(
            task_stage=task_creation_stage,
            url='https://us-central1-valiant-cycle-353908.cloudfunctions.net/random_int_between_0_9'
        )"""
        # third taks
        completion_stage = task_creation_stage.add_stage(
            TaskStage(
                name='Completion stage',
                json_schema='{"type": "object","properties": {"expression": {"title": "Expression", "type": "string"},"answer": {"type": "integer"}}}',
                assign_user_by=TaskStage.STAGE,
                assign_user_from_stage=self.initial_stage,
                copy_input=True
            )
        )
        # fourth ping pong
        conditional_stage = completion_stage.add_stage(
            ConditionalStage(
                name='Conditional ping-pong stage',
                conditions=[{"field": "is_right", "value": "no", "condition": "=="}],
                pingpong=True
            )
        )
        # fifth webhook verification
        verification_webhook_stage = conditional_stage.add_stage(
            TaskStage(
                name='Verification stage using webhook',
                json_schema='{"type":"object","properties":{"is_right":{"type":"string"}}}',
                webhook_address='https://us-central1-valiant-cycle-353908.cloudfunctions.net/even_checker',
                copy_input=True

            )
        )
        # sixth autocomplete task award
        award_stage = verification_webhook_stage.add_stage(
            TaskStage(
                name='Award stage',
                assign_user_by=TaskStage.AUTO_COMPLETE
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
            if i+1 < task_awards.count:
                test_task = test_task.out_tasks.get().out_tasks.get().out_tasks.get().out_tasks.get()

        self.assertEqual(self.user.ranks.count(), 2)
        self.assertEqual(init_task.case.tasks.filter(stage=completion_stage).count(), 5)
        all_tasks = init_task.case.tasks.all()
        self.assertEqual(all_tasks.count(), 21)
        self.assertEqual(all_tasks[20].stage, award_stage)


    def test_conditional_ping_pong_with_shuffle_sentence_webhook(self):
        # first book
        self.initial_stage.json_schema = '{"type":"object","properties":{"foo":{"type":"string"}}}'
        # second creating task
        task_creation_stage = self.initial_stage.add_stage(
            TaskStage(
                name='Creating task using webhook',
                webhook_address='https://us-central1-journal-bb5e3.cloudfunctions.net/shuffle_sentence',
                webhook_params={"action":"create"}
            )
        )
        """
        create_task_webhook = Webhook.objects.create(
            task_stage=task_creation_stage,
            url='https://us-central1-valiant-cycle-353908.cloudfunctions.net/random_int_between_0_9'
        )"""
        # third taks
        completion_stage = task_creation_stage.add_stage(
            TaskStage(
                name='Completion stage',
                json_schema='{"type": "object","properties": {"exercise": {"title": "Put the words in the correct order", "type": "string"},"answer": {"type": "string"}}}',
                assign_user_by=TaskStage.STAGE,
                assign_user_from_stage=self.initial_stage
            )
        )
        CopyField.objects.create(
            copy_by=CopyField.CASE,
            task_stage=completion_stage,
            copy_from_stage=task_creation_stage,
            fields_to_copy='exercise->exercise'
        )
        # fourth ping pong
        conditional_stage = completion_stage.add_stage(
            ConditionalStage(
                name='Conditional ping-pong stage',
                conditions=[{"field": "is_right", "value": "no", "condition": "=="}],
                pingpong=True
            )
        )
        # fifth webhook verification
        verification_webhook_stage = conditional_stage.add_stage(
            TaskStage(
                name='Verification stage using webhook',
                json_schema='{"type":"object","properties":{"is_right":{"type":"string"}}}',
                webhook_address='https://us-central1-journal-bb5e3.cloudfunctions.net/shuffle_sentence',
                webhook_params={"action": "check"}

            )
        )
        CopyField.objects.create(
            copy_by=CopyField.CASE,
            task_stage=verification_webhook_stage,
            copy_from_stage=task_creation_stage,
            fields_to_copy='sentence->sentence'
        )
        # sixth autocomplete task award
        award_stage = verification_webhook_stage.add_stage(
            TaskStage(
                name='Award stage',
                assign_user_by=TaskStage.AUTO_COMPLETE
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
            responses = test_task.responses
            responses['answer'] = test_task.in_tasks.get().responses['sentence']
            test_task = self.complete_task(test_task, responses)
            if i+1 < task_awards.count:
                test_task = test_task.out_tasks.get().out_tasks.get().out_tasks.get().out_tasks.get()

        self.assertEqual(self.user.ranks.count(), 2)
        self.assertEqual(init_task.case.tasks.filter(stage=completion_stage).count(), 5)
        all_tasks = init_task.case.tasks.all()
        self.assertEqual(all_tasks.count(), 21)
        self.assertEqual(all_tasks[20].stage, award_stage)

    def test_auto_notification_simple(self):
        js_schema = {
            "type": "object",
            "properties": {
                'foo': {
                    "type": "string",
                }
            }
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name='Second stage',
                json_schema=self.initial_stage.json_schema,
                assign_user_by=TaskStage.STAGE
            )
        )

        notification = Notification.objects.create(
            title='Congrats you have completed your first task!',
            campaign=self.campaign
        )

        auto_notification = AutoNotification.objects.create(
            trigger_stage=self.initial_stage,
            recipient_stage=self.initial_stage,
            notification=notification
        )

        task = self.create_initial_task()
        task = self.complete_task(task, {"foo": "hello world!"})

        self.assertEqual(self.user.notifications.count(), 1)
        self.assertEqual(Notification.objects.count(), 2)
        self.assertEqual(self.user.notifications.filter(sender_task=task, receiver_task=task).count(), 1)
        self.assertEqual(self.user.notifications.all()[0].title, notification.title)

    def test_forking_chain_happy(self):
        correct_responses = {"1": "a"}
        self.initial_stage.json_schema = {"type": "object",
                                          "properties": {"1": {"enum": ["a", "b", "c", "d"], "type": "string"}}}
        self.initial_stage.json_schema = json.dumps(self.initial_stage.json_schema)
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(TaskStage(
            name='You have complete task successfully',
            json_schema=self.initial_stage.json_schema,
            assign_user_by=TaskStage.STAGE,
            assign_user_from_stage=self.initial_stage
        ))
        rating_stage = self.initial_stage.add_stage(TaskStage(
            name='Rating stage',
            json_schema=self.initial_stage.json_schema,
            assign_user_by=TaskStage.STAGE,
            assign_user_from_stage=self.initial_stage
        ))

        task = self.create_initial_task()
        responses = {"1": "a"}
        response = self.complete_task(task, responses=responses, whole_response=True)
        task = Task.objects.get(id=response.data['id'])
        self.assertEqual(task.case.tasks.count(), 3)
        self.assertEqual(response.data.get('next_direct_id'), None)

    def test_forking_chain_with_conditional_happy(self):
        self.initial_stage.json_schema = {"type": "object",
                                          "properties": {"1": {"enum": ["a", "b", "c", "d"], "type": "string"}}}
        self.initial_stage.json_schema = json.dumps(self.initial_stage.json_schema)
        self.initial_stage.save()

        first_cond_stage = self.initial_stage.add_stage(
            ConditionalStage(
                name='If a',
                conditions=[{"field": "1", "value": "a", "condition": "=="}]
            )
        )

        second_cond_stage = self.initial_stage.add_stage(
            ConditionalStage(
                name='If b',
                conditions=[{"field": "1", "value": "b", "condition": "=="}]
            )
        )

        second_stage = first_cond_stage.add_stage(TaskStage(
            name='You have complete task successfully',
            json_schema=self.initial_stage.json_schema,
            assign_user_by=TaskStage.STAGE,
            assign_user_from_stage=self.initial_stage
        ))

        rating_stage = second_cond_stage.add_stage(TaskStage(
            name='Rating stage',
            json_schema=self.initial_stage.json_schema,
            assign_user_by=TaskStage.STAGE,
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
                {"field": "meta_quiz_score", "value": "60", "condition": "<="},
                {"field": "meta_quiz_score", "value": "90", "condition": ">="},
            ]
        ))

        final = conditional_one.add_stage(TaskStage(
            name='Final stage',
            assign_user_by=TaskStage.AUTO_COMPLETE,
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
            go=AutoNotification.LAST_ONE
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

    def test_auto_notification_last_one_option_as_go(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "foo": {"type": "string"}
            }
        })
        notification = Notification.objects.create(
            title='Congrats!',
            campaign=self.campaign
        )
        AutoNotification.objects.create(
            trigger_stage=self.initial_stage,
            recipient_stage=self.initial_stage,
            notification=notification,
            go=AutoNotification.LAST_ONE
        )
        task = self.create_initial_task()
        task = self.complete_task(task, {"foo": "boo"})
        self.assertEqual(Notification.objects.count(), 2)
        self.assertEqual(self.user.notifications.filter(sender_task=task,
                                                        receiver_task=task).count(), 1)

    def test_assign_rank_by_parent_rank(self):
        schema = {"type": "object", "properties": {"foo": {"type": "string", "title": "what is ur name"}}}
        self.initial_stage.json_schema = json.dumps(schema)
        prize_rank_1 = Rank.objects.create(name='GOOD RANK')
        notification = Notification.objects.create(
            title="You achieve new rank",
            text="Congratulations! You achieve new rank!",
            campaign=self.campaign
        )
        task_awards = TaskAward.objects.create(
            task_stage_completion=self.initial_stage,
            task_stage_verified=self.initial_stage,
            rank=prize_rank_1,
            count=1,
            notification=notification
        )

        second_stage = self.initial_stage.add_stage(TaskStage(
            name='Second stage',
            assign_user_by=TaskStage.STAGE,
            assign_user_from_stage=self.initial_stage,
            json_schema=self.initial_stage.json_schema
        ))
        prize_rank_2 = Rank.objects.create(name='BEST RANK')
        task_awards = TaskAward.objects.create(
            task_stage_completion=second_stage,
            task_stage_verified=second_stage,
            rank=prize_rank_2,
            count=1,
            notification=notification
        )

        super_rank = Rank.objects.create(name='SUPERMAN RANK')
        super_rank.prerequisite_ranks.add(prize_rank_1)
        super_rank.prerequisite_ranks.add(prize_rank_2)
        super_rank.save()
        resp = {"foo":"hello world"}
        task = self.create_initial_task()
        task = self.complete_task(task, resp)
        second_task = task.out_tasks.get()
        second_task = self.complete_task(second_task, resp)

        self.assertEqual(Notification.objects.count(), 3)
        self.assertEqual(self.user.ranks.count(), 4)

    def test_assignee_new_ranks_based_on_prerequisite(self):
        prize_rank_1 = Rank.objects.create(name='Good', track=self.user.ranks.all()[0].track)
        prize_rank_2 = Rank.objects.create(name='Best', track=self.user.ranks.all()[0].track)
        prize_rank_3 = Rank.objects.create(name='Superman', track=self.user.ranks.all()[0].track)
        prize_rank_3.prerequisite_ranks.add(prize_rank_1)
        prize_rank_3.prerequisite_ranks.add(prize_rank_2)
        notification = Notification.objects.create(
            title="You achieve new rank",
            text="Congratulations! You achieve new rank!",
            campaign=self.campaign
        )
        schema = {"type": "object", "properties": {"foo": {"type": "string", "title": "what is ur name"}}}

        self.initial_stage.json_schema = json.dumps(schema)
        self.initial_stage.save()
        task_award_1 = TaskAward.objects.create(
            task_stage_completion=self.initial_stage,
            task_stage_verified=self.initial_stage,
            rank=prize_rank_1,
            count=5,
            notification=notification
        )

        another_chain = Chain.objects.create(name='Chain for getting best', campaign=self.campaign)
        new_initial = TaskStage.objects.create(
            name="Initial for Good persons",
            x_pos=1,
            y_pos=1,
            json_schema=self.initial_stage.json_schema,
            chain=another_chain,
            is_creatable=True)
        rank_limit = RankLimit.objects.create(
            rank=prize_rank_1,
            stage=new_initial,
            open_limit=0,
            total_limit=0,
            is_listing_allowed=True,
            is_creation_open=True
        )
        task_award_2 = TaskAward.objects.create(
            task_stage_completion=new_initial,
            task_stage_verified=new_initial,
            rank=prize_rank_2,
            count=5,
            notification=notification
        )

        responses = {"foo": "Kloop"}
        task = self.create_initial_task()
        for i in range(task_award_1.count):
            task = self.complete_task(task, responses)
            if task_award_1.count-1 > i:
                task = self.create_initial_task()
                self.assertNotIn(prize_rank_2, self.user.ranks.all())
                self.assertNotIn(prize_rank_3, self.user.ranks.all())
            else:
                self.assertIn(prize_rank_1, self.user.ranks.all())
        self.assertIn(prize_rank_1, self.user.ranks.all())
        self.assertNotIn(prize_rank_2, self.user.ranks.all())
        self.assertNotIn(prize_rank_3, self.user.ranks.all())
        another_rank_1 = Rank.objects.create(name='Barmaley', track=self.user.ranks.all()[0].track)
        another_rank_2 = Rank.objects.create(name='Jeenbekov', track=self.user.ranks.all()[0].track)
        self.user.ranks.add(another_rank_2)
        self.user.ranks.add(another_rank_1)
        self.user.ranks.add(prize_rank_1)

        task = self.create_task(new_initial)
        for i in range(task_award_2.count):
            task = self.complete_task(task, responses)
            print(task.complete)
            if task_award_2.count-1 > i:
                task = self.create_task(new_initial)
                self.assertIn(prize_rank_1, self.user.ranks.all())
                self.assertNotIn(prize_rank_2, self.user.ranks.all())
                self.assertNotIn(prize_rank_3, self.user.ranks.all())
            else:
                self.assertIn(prize_rank_2, self.user.ranks.all())
                self.assertIn(prize_rank_3, self.user.ranks.all())
        self.assertIn(prize_rank_1, self.user.ranks.all())
        self.assertIn(prize_rank_2, self.user.ranks.all())
        self.assertIn(prize_rank_3, self.user.ranks.all())
