import json
from uuid import uuid4

from django.db import IntegrityError
from django.db.models import Count
from rest_framework import status
from rest_framework.test import APITestCase, APIClient, RequestsClient
from rest_framework.reverse import reverse

from api.models import CustomUser, TaskStage, Campaign, Chain, ConditionalStage, Stage, Rank, RankRecord, RankLimit, \
    Task, CopyField, Integration, Quiz, ResponseFlattener, Log, AdminPreference


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

        self.user_empl = CustomUser.objects.create_user(username="employee",
                                                        email='employee@email.com',
                                                        password='employee')
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

    def complete_task(self, task, responses=None, client=None):
        c = client
        if c is None:
            c = self.client
        task_update_url = reverse("task-detail", kwargs={"pk": task.pk})
        if responses:
            args = {"complete": True, "responses": responses}
        else:
            args = {"complete": True}
        response = c.patch(task_update_url, args, format='json')
        return Task.objects.get(id=response.data["id"])

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
        task = self.create_initial_task()
        responses = {"answer": "check"}
        task = self.complete_task(task, responses=responses)

        self.check_task_completion(task, self.initial_stage, responses)

    def test_initial_task_update_and_completion(self):
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
        second_stage = self.initial_stage.add_stage(TaskStage())
        initial_task = self.create_initial_task()
        responses = {"check": "cheese"}
        initial_task = self.update_task_responses(initial_task, responses)
        initial_task = self.complete_task(initial_task)
        self.assertEqual(Task.objects.count(), 2)
        self.assertEqual(initial_task.responses, responses)

    def test_passing_conditional(self):
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

        verification_task_responses = {"verified": "yes"}
        # verification_task = self.update_task_responses(
        #     verification_task,
        #     verification_task_responses,
        #     verification_client)
        #
        # verification_task = self.complete_task(
        #     verification_task,
        #     client=verification_client)


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
            is_creatable=True)
        self.client = self.prepare_client(
            id_stage,
            self.user,
            RankLimit(is_creation_open=True))
        task1 = self.create_task(id_stage)
        task2 = self.create_task(id_stage)
        task3 = self.create_task(id_stage)

        correct_responses = {"name": "kloop", "phone": 3, "addr": "kkkk"}

        task1 = self.complete_task(
            task1,
            {"name": "rinat", "phone": 2, "addr": "ssss"})
        task3 = self.complete_task(
            task3,
            {"name": "ri", "phone": 5, "addr": "oooo"})
        task2 = self.complete_task(task2, correct_responses)

        CopyField.objects.create(
            copy_by="US",
            task_stage=self.initial_stage,
            copy_from_stage=id_stage,
            fields_to_copy="name->name phone->phone1 absent->absent")

        task = self.create_initial_task()

        self.assertEqual(len(task.responses), 2)
        self.assertEqual(task.responses["name"], task2.responses["name"])
        self.assertEqual(task.responses["phone1"], task2.responses["phone"])


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
            chain=id_chain,
            is_creatable=True)
        self.client = self.prepare_client(
            id_stage,
            self.user,
            RankLimit(is_creation_open=True))
        task1 = self.create_task(id_stage)
        task2 = self.create_task(id_stage)
        task3 = self.create_task(id_stage)

        correct_responses = {"name": "kloop", "phone": 3, "addr": "kkkk"}

        task1 = self.complete_task(
            task1,
            {"name": "rinat", "phone": 2, "addr": "ssss"})
        task3 = self.complete_task(
            task3,
            {"name": "ri", "phone": 5, "addr": "oooo"})
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

    def test_get_tasks_selectable_responses_filter(self):
        second_stage = self.initial_stage.add_stage(TaskStage())
        self.client = self.prepare_client(second_stage, self.user)

        task_11 = self.create_initial_task()
        task_11 = self.complete_task(task_11, {"check": "ga"})
        task_12 = task_11.out_tasks.all()[0]

        task_21 = self.create_initial_task()
        task_21 = self.complete_task(task_21, {"check": "go"})
        task_22 = task_21.out_tasks.all()[0]

        resp = {"stage": self.initial_stage.id, "responses": {"check": "ga"}}
        resp = json.dumps(resp)
        responses_filter = {"task_responses": resp}
        # responses_filter = "task_responses=check"

        response = self.get_objects("task-user-selectable", params=responses_filter)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], task_12.id)

    def test_open_previous(self):
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                assign_user_from_stage=self.initial_stage,
                allow_go_back=True
            ))
        initial_task = self.create_initial_task()
        self.complete_task(initial_task)
        second_task = Task.objects.get(
            stage=second_stage,
            case=initial_task.case)
        self.assertEqual(initial_task.assignee, second_task.assignee)
        self.check_task_auto_creation(second_task, second_stage, initial_task)
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
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                assign_user_from_stage=self.initial_stage)
        )
        third_stage = second_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                assign_user_from_stage=self.initial_stage)
        )
        CopyField.objects.create(
            copy_by="CA",
            task_stage=third_stage,
            copy_from_stage=self.initial_stage,
            fields_to_copy="name->name phone->phone1 absent->absent")

        task = self.create_initial_task()
        correct_responses = {"name": "kloop", "phone": 3, "addr": "kkkk"}
        task = self.complete_task(task, responses=correct_responses)
        task_2 = task.out_tasks.all()[0]
        self.complete_task(task_2)
        task_3 = task_2.out_tasks.all()[0]

        self.assertEqual(Task.objects.count(), 3)
        self.assertEqual(len(task_3.responses), 2)
        self.assertEqual(task_3.responses["name"], task.responses["name"])
        self.assertEqual(task_3.responses["phone1"], task.responses["phone"])

    def test_copy_field_by_case_copy_all(self):
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                assign_user_from_stage=self.initial_stage)
        )
        third_stage = second_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
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
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                assign_user_by="ST",
                assign_user_from_stage=self.initial_stage,
                copy_input=True)
        )
        task = self.create_initial_task()
        correct_responses = {"name": "kloop", "phone": 3, "addr": "kkkk"}
        task = self.complete_task(task, responses=correct_responses)
        task_2 = task.out_tasks.all()[0]

        self.assertEqual(task_2.responses, task.responses)

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
        self.initial_stage.save()
        task_correct_responses = self.complete_task(
            task_correct_responses,
            responses=correct_responses)
        Quiz.objects.create(
            task_stage=self.initial_stage,
            correct_responses_task=task_correct_responses
        )
        task = self.create_initial_task()
        responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "e"}
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
        responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "e"}
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
        responses = {"1": "a", "2": "b", "3": "a", "4": "c", "5": "e"}
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

    def test_response_flattener_list_wrong_preference(self):
        self.user.managed_campaigns.add(self.campaign)

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
        self.user_empl.managed_campaigns.add(self.campaign)
        AdminPreference.objects.create(user=self.user_empl, campaign=self.campaign)

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
        self.user_empl.managed_campaigns.add(self.campaign)
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
        self.user_empl.managed_campaigns.add(self.campaign)
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

        self.user_empl.managed_campaigns.add(self.campaign)
        new_client = self.create_client(self.user_empl)

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

        self.user_empl.managed_campaigns.add(self.campaign)
        new_client = self.create_client(self.user_empl)

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

        self.user_empl.managed_campaigns.add(self.campaign)
        new_client = self.create_client(self.user_empl)

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
                          'integrator_group', 'complete', 'force_complete', 'reopened']
        responses_fields = ["BBB", "DDD__d__d", "AAA"]

        all_columns = system_columns + responses_fields
        self.assertEqual(ordered_columns, all_columns)
        flattened_task = response_flattener.flatten_response(task)
        for i in system_columns:
            self.assertEqual(task.__getattribute__(i), flattened_task[i])


    def test_response_flattener_with_previous_names(self):
        tasks = self.create_initial_tasks(5)
        self.user_empl.managed_campaigns.add(self.campaign)
        new_client = self.create_client(self.user_empl)

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

        new_client = self.create_client(self.user_empl)
        params = {"response_flattener": response_flattener.id, "stage": self.initial_stage.id}
        response = self.get_objects("task-csv", params=params, client=new_client)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_response_flattener_not_found(self):

        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(i)uik"])

        params = {"response_flattener": response_flattener.id+111, "stage": 234}
        response = self.get_objects("task-csv", params=params)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_user_activity_csv_success(self):
        self.user.managed_campaigns.add(self.campaign)
        tasks = self.create_initial_tasks(5)
        response = self.client.get(reverse('task-user-activity-csv')+"?csv=22")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_annotation = Task.objects.filter(pk__in=[x.pk for x in tasks])\
            .values('stage__name', 'assignee').annotate(Count('pk'))
        # b'assignee,stage__name,pk__count\r\n31,Initial,5\r\n'
        cols = 'assignee,stage__name,pk__count\r\n'
        cont = "".join([f"{x['assignee']},{x['stage__name']},{x['pk__count']}\r\n" for x in expected_annotation])
        self.assertEqual(response.content, str.encode(cols+cont))

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
