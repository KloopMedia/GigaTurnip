import json
from uuid import uuid4
from rest_framework.test import APITestCase, APIClient, RequestsClient
from rest_framework.reverse import reverse
from rest_framework import status

from api.models import CustomUser, Campaign, CampaignManagement, Chain, TaskStage, Integration, Webhook, Task, Track, \
    RankRecord, Notification, Rank, RankLimit


class GigaTurnip(APITestCase):

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


class ModelsTest(GigaTurnip):
    def setUp(self):
        self.campaign = Campaign.objects.create(name="Coca cola Campaign")
        self.chain = Chain.objects.create(
            name="Monday Chain",
            campaign=self.campaign)
        self.initial_stage = TaskStage.objects.create(
            name="Initial task stage",
            x_pos=1,
            y_pos=1,
            chain=self.chain,
            is_creatable=True
        )
        self.user = CustomUser.objects.create_user(
            username="Test User",
            email="test@email.com",
            password="test"
        )

        self.client = self.prepare_client(
            stage=self.initial_stage,
            user=self.user,
            rank_limit=RankLimit(is_creation_open=True)
        )

    def test_campaign_management_on_delete_user_instance(self):
        old_count_managers = CampaignManagement.objects.count()
        self.user.managed_campaigns.add(self.campaign)

        self.assertNotEqual(old_count_managers, CampaignManagement.objects.count())

        self.user.delete()

        self.assertEqual(old_count_managers, CampaignManagement.objects.count())
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(Chain.objects.count(), 1)
        self.assertEqual(TaskStage.objects.count(), 1)

    def test_campaign_management_on_delete_campaign_instance(self):
        old_count_managers = CampaignManagement.objects.count()
        self.user.managed_campaigns.add(self.campaign)

        self.assertNotEqual(old_count_managers, CampaignManagement.objects.count())

        self.campaign.delete()

        self.assertEqual(old_count_managers, CampaignManagement.objects.count())
        self.assertEqual(CustomUser.objects.count(), 1)
        self.assertEqual(Chain.objects.count(), 0)
        self.assertEqual(TaskStage.objects.count(), 0)

    def test_campaign_management_relations(self):
        campaign2 = Campaign.objects.create(name="New Campaign")
        campaign3 = Campaign.objects.create(name="New Campaign")

        self.user.managed_campaigns.add(self.campaign)
        self.user.managed_campaigns.add(campaign2)
        self.user.managed_campaigns.add(campaign3)

        self.assertEqual(3, CampaignManagement.objects.count())

        self.assertEqual([self.user], list(self.campaign.managers.all()))
        self.assertEqual([self.user], list(campaign2.managers.all()))
        self.assertEqual([self.user], list(campaign3.managers.all()))

    def test_chain_on_delete_campaign(self):
        old_count = Chain.objects.count()
        self.campaign.delete()
        self.assertLess(Chain.objects.count(), old_count)
        self.assertFalse(Chain.objects.filter(id=self.chain.id).exists())



