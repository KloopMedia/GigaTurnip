import django

django.setup()
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from django.contrib.auth.models import Group
from api.models import CustomUser, Campaign
from django.db.models import Q

from api.views import CampaignViewSet


class CampaignTest(APITestCase):
	def setUp(self):
		self.url = reverse('campaign-list')
		self.factory = APIRequestFactory()
		self.user = CustomUser.objects.create_user(
			username='test',
			email='test@email.com',
			password='test')
		self.campaign_creator = Group.objects.get(name='campaign_creator')
		self.client.force_authenticate(user=self.user)
		self.campaign = Campaign.objects.create(name='My testing campaign')
		self.view = CampaignViewSet.as_view({'get': 'list', 'post': 'create', 'patch': 'partial_update'})

	def test_get_list_of_campaigns_if_user_is_not_manager_of_any_campaign(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 404)

	def test_get_list_of_campaigns_if_user_not_managers_of_any_campaign(self):
		self.user.managed_campaigns.add(self.campaign)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 200)

	def test_create_new_campaign_if_not_campaign_creator(self):
		request = self.factory.post(self.url, {"name": "created in test"})
		force_authenticate(request=request, user=self.user)
		response = self.view(request)
		self.assertEqual(response.status_code, 403)

	def test_create_new_campaign_if_campaign_creator(self):
		self.user.groups.add(self.campaign_creator)
		request = self.factory.post(self.url, {"name": "created in test"})
		force_authenticate(request=request, user=self.user)
		response = self.view(request)
		self.assertEqual(response.status_code, 201)

	def test_retrieve_not_my_campaign(self):
		self.user.managed_campaigns.add(self.campaign)
		not_my_campaign = Campaign.objects.filter(~Q(id=self.campaign.id))[0]
		response = self.client.get(self.url + str(not_my_campaign.id) + '/')
		self.assertEqual(response.status_code, 403)

	def test_retrieve_my_campaign(self):
		self.user.managed_campaigns.add(self.campaign)
		my_campaign = self.user.managed_campaigns.first()
		response = self.client.get(self.url + str(my_campaign.id) + '/')
		self.assertEqual(response.status_code, 200)

	def test_partial_update_not_my_campaign(self):
		not_my_campaign = Campaign.objects.first()
		url = self.url + str(not_my_campaign.id) + '/'
		request = self.factory.patch(url, {"name": "renamed campaign in test without permissions"})
		force_authenticate(request=request, user=self.user)
		response = self.view(request, pk=str(not_my_campaign.id))
		self.assertEqual(response.status_code, 403)

	def test_partial_update_my_campaign(self):
		self.user.managed_campaigns.add(self.campaign)
		my_campaign = self.user.managed_campaigns.first()
		url = self.url + str(my_campaign.id) + '/'
		request = self.factory.patch(url, {"name": "renamed campaign in test had permissions"})
		force_authenticate(request=request, user=self.user)
		response = self.view(request, pk=str(my_campaign.id))
		self.assertEqual(response.status_code, 200)
