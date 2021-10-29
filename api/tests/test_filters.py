import unittest
from django.test import TestCase
import django
from django.db import connection

django.setup()
from api.models import CustomUser, BaseModel, SchemaProvider, Campaign, \
    CampaignManagement, Chain, Stage, TaskStage, \
    ConditionalStage, Case, Task, \
    Rank, Track, RankRecord, RankLimit
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api import utils
import requests


class MyTestCase(APITestCase):
    def setUp(self):
        self.url = ""
        self.factory = APIRequestFactory()
        self.user = CustomUser.objects.create(username="admin", email='admin@email.com', password='admin')
        self.employee = CustomUser.objects.create(username="employee", email='employee@email.com', password='employee')

        self.campaign = Campaign.objects.create(name="New Campaign")
        self.chain = Chain.objects.create(name="New Campaign", campaign=self.campaign)
        self.task_stage = TaskStage.objects.create(name="New Task stage", x_pos=1, y_pos=1,
                                                   chain=self.chain)
        self.rank = Rank.objects.create(name="New Rank")

    def test_is_user_campaign_manager_fail(self):
        self.assertNotIn(self.user, self.campaign.managers.all())
        self.assertFalse(utils.is_user_campaign_manager(self.user, self.campaign.id))

    def test_is_user_campaign_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)
        self.assertIn(self.user, self.campaign.managers.all())
        self.assertTrue(utils.is_user_campaign_manager(self.user, self.campaign.id))

    # todo: we have to check completed tasks
    def test_filter_for_user_selectable_tasks(self):
        self.user.managed_campaigns.add(self.campaign)
        self.rank_limit = RankLimit.objects.create(rank=self.rank, stage=self.task_stage, open_limit=3, total_limit=5,
                                                   is_selection_open=True, is_listing_allowed=True)
        tasks_assigned = [Task.objects.create(assignee=self.employee, stage=self.task_stage) for i in range(5)]
        tasks_not_assigned = [Task.objects.create(stage=self.task_stage) for i in range(5)]
        rank_record = RankRecord.objects.create(user=self.employee, rank=self.rank)
        request = self.factory.get(self.url)
        request.user = self.employee
        queryset = Task.objects.all()
        filtered_queryset = utils.filter_for_user_selectable_tasks(queryset, request)

        # employee can see only tasks_not_assigned
        self.assertEqual(list(filtered_queryset), tasks_not_assigned)

        request.user = self.user
        filtered_queryset = utils.filter_for_user_selectable_tasks(queryset, request)
        # i think taht manager of campaign can see his user_selectable tasks
        self.assertEqual(list(filtered_queryset), tasks_not_assigned + tasks_assigned)

    def test_filter_for_user_creatable_stages(self):
        # campaign, chain, task_stage, rank,
        # connect rank to user, create rank limit for user(is_creation_open = True)
        # create track(name and campaign)
        # test function
        another_campaign = Campaign.objects.create(name="Another Campaign")
        another_chain = Chain.objects.create(name="Another Chain", campaign=another_campaign)
        another_task_stage = TaskStage.objects.create(name=f"Another Task stage #1", x_pos=1, y_pos=1,
                                                   chain=another_chain, is_creatable=True)
        another_rank = Rank.objects.create(name="Another rank")
        RankRecord.objects.create(user=self.employee, rank=another_rank)
        another_rank_limit = RankLimit.objects.create(rank=another_rank, stage=another_task_stage,
                                              open_limit=2, total_limit=3,
                                              is_creation_open=True)
        another_track = Track.objects.create(name="Another track", campaign=self.campaign)
        another_task = Task.objects.create(assignee=self.employee, stage=another_task_stage)

        request = self.factory.get(self.url)
        request.user = self.employee

        filtered_queryset = utils.filter_for_user_creatable_stages(TaskStage.objects.all(), request)
        self.assertEqual(list(filtered_queryset), [another_task_stage])

        another_task_stages = [TaskStage.objects.create(name=f"Another Task stage #{i+1}", x_pos=1, y_pos=1,
                                                   chain=another_chain, is_creatable=True) for i in range(5) ]
        another_rank_limit = [RankLimit.objects.create(rank=another_rank, stage=stage,
                                                      open_limit=2, total_limit=3,
                                                      is_creation_open=True) for stage in another_task_stages]
        another_task = [Task.objects.create(assignee=self.employee, stage=stage) for stage in another_task_stages]

        filtered_queryset = utils.filter_for_user_creatable_stages(TaskStage.objects.all(), request)
        self.assertEqual(list(filtered_queryset), [another_task_stage] + another_task_stages)
