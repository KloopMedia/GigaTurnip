from django.test import SimpleTestCase, TransactionTestCase
from uuid import uuid4

from rest_framework.test import APITestCase, APIClient
from rest_framework.reverse import reverse
import threading
from api.models import CustomUser, TaskStage, Campaign, Chain, ConditionalStage, Stage, Rank, RankRecord, RankLimit, \
    Task, CopyField

def test_concurrently(times):
    """
    Add this decorator to small pieces of code that you want to test
    concurrently to make sure they don't raise exceptions when run at the
    same time.  E.g., some Django views that do a SELECT and then a subsequent
    INSERT might fail when the INSERT assumes that the data has not changed
    since the SELECT.
    """
    def test_concurrently_decorator(test_func):
        def wrapper(*args, **kwargs):
            exceptions = []
            def call_test_func():
                try:
                    test_func(*args, **kwargs)
                except Exception as e:
                    exceptions.append(e)
                    raise
            threads = []
            for i in range(times):
                threads.append(threading.Thread(target=call_test_func))
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if exceptions:
                try:
                    raise Exception('test_concurrently intercepted %s exceptions: %s' % (len(exceptions), exceptions))
                except:
                    pass
        return wrapper
    return test_concurrently_decorator


class GigaTurnipTest(TransactionTestCase):

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
        # self.user = CustomUser.objects.all()[0]
        self.client = self.prepare_client(
            self.initial_stage,
            self.user,
            RankLimit(is_creation_open=True))

        # self.client.force_authenticate(user=self.user)
        # self.rank = Rank.objects.create(name="rank")
        # self.rank_record = RankRecord.objects.create(
        #     user=self.user,
        #     rank=self.rank)

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

    def test_task_completion_race_condition(self):
        task = self.create_initial_task()

        new_task_stage = TaskStage.objects.create(name="Task stage cola second", x_pos=1, y_pos=1,
                                                  chain=self.chain)
        new_task_stage.in_stages.add(self.initial_stage)

        responses = {"answer": "check"}
        # task = self.complete_task(task, responses=responses)
        task_update_url = reverse("task-detail", kwargs={"pk": task.pk})
        args = {"complete": True, "responses": responses}

        # self.check_task_completion(task, self.initial_stage, responses)
        @test_concurrently(20)
        def toggle_registration():
            response = self.client.patch(task_update_url, args, format='json')
            # response = self.client.get(reverse("campaign-list"))
            if response.status_code == 200:
                print(response)
            # response = self.client.patch(task_update_url, args, format='json')
        toggle_registration()
        self.assertEqual(Task.objects.filter(stage=new_task_stage).count(),1)

    def test_task_integrator_race_condition(self):
        # task = self.create_initial_task()
        # self.initial_stage =
        pass
