import django, json

django.setup()
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from django.contrib.auth.models import Group
from api.models import CustomUser, Campaign, TaskStage, Task, Chain, Rank, RankLimit, RankRecord
from django.db.models import Q
from rest_framework import status
from api.views import CampaignViewSet, TaskStageViewSet, TaskViewSet
from api.serializer import TaskStageSerializer, TaskStageReadSerializer


class CampaignViewSetTest(APITestCase):
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
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_get_list_of_campaigns_if_user_not_managers_of_any_campaign(self):
		self.user.managed_campaigns.add(self.campaign)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_create_new_campaign_if_not_campaign_creator(self):
		request = self.factory.post(self.url, {"name": "created in test"})
		force_authenticate(request=request, user=self.user)
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_retrieve_my_campaign(self):
		self.user.managed_campaigns.add(self.campaign)
		my_campaign = self.user.managed_campaigns.first()
		response = self.client.get(self.url + str(my_campaign.id) + '/')
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_partial_update_not_my_campaign(self):
		not_my_campaign = Campaign.objects.first()
		url = self.url + str(not_my_campaign.id) + '/'
		request = self.factory.patch(url, {"name": "renamed campaign in test without permissions"})
		force_authenticate(request=request, user=self.user)
		response = self.view(request, pk=str(not_my_campaign.id))
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_partial_update_my_campaign(self):
		self.user.managed_campaigns.add(self.campaign)
		my_campaign = self.user.managed_campaigns.first()
		url = self.url + str(my_campaign.id) + '/'
		request = self.factory.patch(url, {"name": "renamed campaign in test had permissions"})
		force_authenticate(request=request, user=self.user)
		response = self.view(request, pk=str(my_campaign.id))
		self.assertEqual(response.status_code, status.HTTP_200_OK)


class TaskStageViewSetTest(APITestCase):
	def setUp(self):
		self.url = reverse('taskstage-list')
		self.factory = APIRequestFactory()
		self.user = CustomUser.objects.create_user(
			username='test',
			email='test@email.com',
			password='test')

		self.client.force_authenticate(user=self.user)

		self.campaign = Campaign.objects.create(name='Testing campaign views')
		self.chain = Chain.objects.create(name='Testing chain views', campaign=self.campaign)

	def test_user_relevant_if_had_task_stage_and_rank(self):
		task_stage = TaskStage.objects.create(
			name='Task stage testing', chain=self.chain,
			x_pos=1, y_pos=1, is_creatable=True)
		rank = Rank.objects.create(name='Testing rank views')
		rank_record = RankRecord.objects.create(user=self.user, rank=rank)
		rank_limit = RankLimit.objects.create(
			rank=rank, stage=task_stage,
			open_limit=3, total_limit=5
		)
		response = self.client.get(self.url + 'user_relevant/')
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertNotEqual(len(json.loads(response.content)), 0)

	def test_many_ranks_and_task_stages(self):
		task_stages = [TaskStage.objects.create(
			name=f'Task stage testing #{i}', chain=self.chain,
			x_pos=1, y_pos=1, is_creatable=True) for i in range(3)]

		ranks = [
			Rank.objects.create(name=f'Testing rank views №{i}') for i in range(3)
				]
		rank_records = [RankRecord.objects.create(user=self.user, rank=rank) for rank in ranks]
		ranks_and_task_stages = zip(ranks, task_stages)
		rank_limits = [RankLimit.objects.create(
			rank=rank_and_stage[0], stage=rank_and_stage[1],
			open_limit=2 + i, total_limit=2 + i
		) for i, rank_and_stage in enumerate(ranks_and_task_stages)]

		for i, rank_limit in enumerate(rank_limits):
			open_limit = rank_limit.open_limit
			total_limit = rank_limit.total_limit

			if total_limit < 4:
				tasks_for_current_task_stage = [
					Task.objects.create(
						assignee=self.user,
						stage=task_stages[i]
					) for j in range(total_limit)
				]

		response = self.client.get(self.url + 'user_relevant/', format='json')
		expected_instance = TaskStageReadSerializer(task_stages[-1]).data
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)
		self.assertIn(expected_instance, json.loads(response.content))

	def test_if_no_task_stages(self):
		self.client.force_authenticate(user=self.user)
		response = self.client.get(self.url + 'user_relevant/', format='json')
		self.assertEqual(len(response.data), 0)