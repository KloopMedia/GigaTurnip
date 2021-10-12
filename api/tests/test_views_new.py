import django, json, random

django.setup()

from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from django.contrib.auth.models import Group
from api.models import CustomUser, Campaign
from rest_framework import status



class CampaignTest(APITestCase):
    def setUp(self):
        self.url = reverse("campaign-list")
        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.client.force_authenticate(user=self.user)
        self.campaign = {"name": "name", "description": "description"}
        self.campaign_creator_group = Group.objects.create(name='campaign_creator')

    def test_create_campaign_fail(self):
        response = self.client.post(self.url, self.campaign)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Campaign.objects.count(), 0)

    def test_create_campaign_success(self):
        self.campaign_creator_group.user_set.add(self.user)
        response = self.client.post(self.url, self.campaign)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(Campaign.objects.get(id=response.data.get('id')).name, self.campaign.get('name'))

        self.campaign_creator_group.user_set.remove(self.user)
        self.assertEqual(self.campaign_creator_group.user_set.count(), 0)

    def test_list_campaign_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_campaign_dnot_exist_fail(self):
        self.assertEqual(Campaign.objects.count(), 0)
        response = self.client.get(self.url + "1/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_campaign_exist_success(self):
        self.assertEqual(Campaign.objects.count(), 0)
        self.campaign_creator_group.user_set.add(self.user)
        response = self.client.post(self.url, self.campaign)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Campaign.objects.count(), 1)

        response = self.client.get(self.url + str(response.data.get("id")) + '/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_parital_update_not_manager_fail(self):
        self.campaign_creator_group.user_set.add(self.user)
        response = self.client.post(self.url, self.campaign)
        campaign_id = response.data.get('id')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(Campaign.objects.get(id=campaign_id).name, self.campaign.get('name'))

        new_name = {"name" : "new_name"}
        response = self.client.patch(self.url+str(campaign_id)+"/", new_name)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_success(self):
        self.campaign_creator_group.user_set.add(self.user)
        response = self.client.post(self.url, self.campaign)
        campaign_id = response.data.get('id')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(Campaign.objects.get(id=campaign_id).name, self.campaign.get('name'))
        self.assertEqual(0, Campaign.objects.get(id=campaign_id).managers.count())

        self.assertEqual(0, Campaign.objects.get(id=campaign_id).managers.count())
        self.user.managed_campaigns.add(Campaign.objects.get(id=campaign_id))
        new_name = {"name": "new_name"}
        response = self.client.patch(self.url + str(campaign_id) + "/", new_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Campaign.objects.get(id=campaign_id).name, new_name.get('name'))
        self.assertEqual(Campaign.objects.count(), 1)

    def test_destroy(self):
        self.campaign_creator_group.user_set.add(self.user)
        response = self.client.post(self.url, self.campaign)
        campaign_id = response.data.get('id')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(Campaign.objects.get(id=campaign_id).name, self.campaign.get('name'))
        self.assertEqual(0, Campaign.objects.get(id=campaign_id).managers.count())

        self.assertEqual(0, Campaign.objects.get(id=campaign_id).managers.count())
        self.user.managed_campaigns.add(Campaign.objects.get(id=campaign_id))
        response = self.client.delete(self.url + str(campaign_id) + "/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Campaign.objects.count(), 1)