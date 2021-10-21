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
        self.user = CustomUser.objects.create(username="test", email='test@email.com', password='test')
        self.campaign = Campaign.objects.create(name="New Campaign")

    def test_is_user_campaign_manager_fail(self):
        self.assertNotIn(self.user, self.campaign.managers.all())
        self.assertFalse(utils.is_user_campaign_manager(self.user, self.campaign.id))

    def test_is_user_campaign_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)
        self.assertIn(self.user, self.campaign.managers.all())
        self.assertTrue(utils.is_user_campaign_manager(self.user, self.campaign.id))

    def test_filter_for_user_selectable_tasks_fail(self):
        request = self.factory.get(self.url)
        force_authenticate(request=request, user=self.user)
        queryset= Task.objects.all().filter(
            stage__chain__campaign__campaign_managements__user=
                   request.user).distinct()
        self.request, Task.objects.all()


    def test_filter_for_user_selectable_tasks_success(self):
        pass


