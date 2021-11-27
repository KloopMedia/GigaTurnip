import json
from uuid import uuid4

from rest_framework.test import APITestCase, APIClient, RequestsClient
from rest_framework.reverse import reverse

from api.models import CustomUser, TaskStage, Campaign, Chain, ConditionalStage, Stage, Rank, RankRecord, RankLimit, \
    Task, CopyField, Integration


class GigaTurnipTest(APITestCase):

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
        client = APIClient()
        client.force_authenticate(u)
        return client

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

