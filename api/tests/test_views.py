import django, json, random
django.setup()

from api.models import Stage
from api.views import RankLimitViewSet, RankRecordViewSet
from api.models import Track
from django.http import request, response

from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from django.contrib.auth.models import Group
from api.models import CustomUser, Campaign, TaskStage, Task, Chain, Rank, RankLimit, RankRecord, ConditionalStage
from django.db.models import Q
from rest_framework import status
from api.views import CampaignViewSet, TaskStageViewSet, TaskViewSet, ChainViewSet, ConditionalStageViewSet, RankViewSet
from api.serializer import TaskStageSerializer, TaskStageReadSerializer, ChainSerializer, \
	TaskRequestAssignmentSerializer, TaskDefaultSerializer, ConditionalStageSerializer
from api import utils


def create_campaign(name='Testing campaign views', description=''):
	campaign = Campaign.objects.create(name=name, description=description)
	return campaign


def create_chain(campaign, name='Testing chain views'):
	chain = Chain.objects.create(name=name, campaign=campaign)
	return chain


def create_rank(name='Rank for test request assign', description=''):
	rank = Rank.objects.create(name=name, description=description)
	return rank


def create_rank_record(user, rank):
	return RankRecord.objects.create(user=user, rank=rank)


def create_task_stage(chain):
	return TaskStage.objects.create(
		name=f'Task stage testing ', chain=chain,
		x_pos=1, y_pos=1, is_creatable=True)


def create_task(task_stage,
				assignee=None,
				case=None,
				responses=None,
				in_tasks=None,
				complete=False):
	task = Task.objects.create(stage=task_stage,
							   assignee=assignee,
							   case=case,
							   responses=responses,
							   complete=complete,
							   )
	if in_tasks:
		for in_task in in_tasks:
			task.in_tasks.add(in_task)
	return task


def create_rank_limit(
	rank, task_stage, open_limit=3, total_limit=3,
	is_listing_allowed=False, is_submission_open=True,
	is_selection_open=True, is_creation_open=True):
	rank_limit = RankLimit.objects.create(
		rank=rank, stage=task_stage,
		open_limit=open_limit, total_limit=total_limit,
		is_listing_allowed=is_listing_allowed,
		is_submission_open=is_submission_open,
		is_selection_open=is_selection_open,
		is_creation_open=is_creation_open
	)
	return rank_limit


class CampaignViewSetTest(APITestCase):
	def setUp(self):
		self.url = reverse('campaign-list')
		self.factory = APIRequestFactory()
		self.user = CustomUser.objects.create_user(
			username='test',
			email='test@email.com',
			password='test')
		self.campaign_creator_group, created = Group.objects.get_or_create(name='campaign_creator')
		self.client.force_authenticate(user=self.user)
		self.campaign = Campaign.objects.create(name='My testing campaign')
		self.view = CampaignViewSet.as_view({'get': 'list', 'post': 'create', 'patch': 'partial_update'})
		self.campaign_creator_group.user_set.add(self.user)

	def test_get_list_of_campaigns_if_user_is_not_manager_of_any_campaign(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_get_list_of_campaigns_if_user_not_managers_of_any_campaign(self):
		self.user.managed_campaigns.add(self.campaign)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_create_new_campaign_if_not_campaign_creator(self):
		self.campaign_creator_group.user_set.remove(self.user)
		request = self.factory.post(self.url, {"name": "created in test"})
		force_authenticate(request=request, user=self.user)
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_create_new_campaign_if_campaign_creator(self):
		self.user.groups.add(Group.objects.get(name='campaign_creator'))
		request = self.factory.post(self.url, {"name": "created in test"})
		force_authenticate(request=request, user=self.user)
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_retrieve_not_my_campaign(self):
		not_my_campaign = Campaign.objects.filter(id=self.campaign.id)[0]
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


class ChainViewSetTest(APITestCase):
	def setUp(self):
		self.url = reverse('chain-list')
		self.factory = APIRequestFactory()
		self.user = CustomUser.objects.create_user(
			username='test',
			email='test@email.com',
			password='test')
		campaign_creator_group, created = Group.objects.get_or_create(name='campaign_creator')
		self.campaign_creator = Group.objects.get(name='campaign_creator')
		self.client.force_authenticate(user=self.user)

		self.campaign = Campaign.objects.create(name='My testing campaign')
		self.chain = Chain.objects.create(name='My testing chain ChainViewSet',
										  campaign=self.campaign)
		self.view = ChainViewSet.as_view({'get': 'list', 'post': 'create', 'patch': 'partial_update'})

	def test_get_all_list_not_manager(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_get_all_list_manager(self):
		self.user.managed_campaigns.add(self.campaign)
		response = self.client.get(self.url)
		expected_instance = ChainSerializer(self.chain).data
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn(expected_instance, json.loads(response.content))

	def test_create_new_chain_with_existing_campaign_and_manager(self):
		self.user.managed_campaigns.add(self.campaign)
		data_to_create = {
			"name": "new chain created in test",
			"campaign": self.campaign.id
		}
		request = self.factory.post(self.url, data_to_create)
		force_authenticate(request=request, user=self.user)
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		response_data = response.data
		for key in data_to_create.keys():
			self.assertEqual(data_to_create[key], data_to_create[key])

	def test_create_new_chain_with_existing_campaign_and_not_manager(self):
		data_to_create = {
			"name": "new chain created in test",
			"campaign": self.campaign.id
		}
		request = self.factory.post(self.url, data_to_create)
		force_authenticate(request=request, user=self.user)
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_create_new_chain_with_manager_and_no_existing_campaign(self):
		self.user.managed_campaigns.add(self.campaign)
		existing_ids = [i[0] for i in Campaign.objects.values_list('id') ]
		not_existing_id = existing_ids[0]
		while not_existing_id not in existing_ids:
			not_existing_id = random.randint(1,10000000)
		data_to_create = {
			"name": "new chain created in test with not existing campaign",
			"campaign": not_existing_id
		}
		request = self.factory.post(self.url, data_to_create)
		force_authenticate(request=request, user=self.user)
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)



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
		print("USER RELEVANT: ", response.content)
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

	def test_if_auth_but_no_task_stages(self):
		self.client.force_authenticate(user=self.user)
		self.user.managed_campaigns.add(self.campaign)

		response = self.client.get(self.url + 'user_relevant/', format='json')
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TaskViewSetTest(APITestCase):
	def setUp(self):
		self.url = reverse('task-list')
		self.factory = APIRequestFactory()
		self.user = CustomUser.objects.create_user(
			username='test',
			email='test@email.com',
			password='test')

		self.client.force_authenticate(user=self.user)

		self.rank = create_rank()
		self.campaign = create_campaign()
		self.chain = create_chain(campaign=self.campaign)
		self.view = TaskViewSet.as_view({'get': 'list', 'post': 'create', 'patch': 'partial_update'})

	def test_block_release_and_request_assignment(self):
		task_stages = [TaskStage.objects.create(
			name=f'Task stage testing #{i}', chain=self.chain,
			x_pos=1, y_pos=1, is_creatable=True) for i in range(3)]
		tasks = [Task.objects.create(
			assignee=self.user,
			stage=task_stages[i])
			for i in range(3)]

		for task in tasks:
			response = self.client.get(self.url + f"{task.id}/release_assignment/")
			self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

		tasks = [Task.objects.create(
			stage=task_stages[i])
			for i in range(3)]
		for task in tasks:
			response = self.client.get(self.url + f"{task.id}/request_assignment/")
			self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_list_if_rank_and_not_assignee(self):
		rank_record = create_rank_record(self.user, self.rank)

		task_stage = create_task_stage(self.chain)

		rank_limit = create_rank_limit(self.rank, task_stage, open_limit=4, total_limit=5, is_listing_allowed=True)

		tasks = [create_task(task_stage) for i in range(3)]
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_list_if_rank_and_assignee(self):
		rank_record = create_rank_record(self.user, self.rank)

		task_stage = create_task_stage(self.chain)

		rank_limit = create_rank_limit(self.rank, task_stage, open_limit=4, total_limit=5, is_listing_allowed=True)

		tasks = [create_task(task_stage, assignee=self.user) for i in range(3)]
		response = self.client.get(self.url)
		response.render()
		self.assertEqual(response.status_code, status.HTTP_200_OK)

		expected_tasks = TaskDefaultSerializer(tasks, many=True).data
		self.assertEqual(expected_tasks, json.loads(response.content))
		for expected_task in expected_tasks:
			self.assertIn(expected_task, json.loads(response.content))

	def test_list_if_manager(self):
		self.user.managed_campaigns.add(self.campaign)

		rank_record = create_rank_record(self.user, self.rank)
		task_stage = create_task_stage(self.chain)
		rank_limit = create_rank_limit(self.rank, task_stage, open_limit=4, total_limit=5, is_listing_allowed=True)
		tasks = [create_task(task_stage) for i in range(3)]

		response = self.client.get(self.url)
		response.render()
		self.assertEqual(response.status_code, status.HTTP_200_OK)

		expected_tasks = TaskDefaultSerializer(tasks, many=True).data
		self.assertEqual(expected_tasks, json.loads(response.content))
		for expected_task in expected_tasks:
			self.assertIn(expected_task, json.loads(response.content))

	def test_list_if_not_manager(self):
		rank_record = create_rank_record(self.user, self.rank)
		task_stage = create_task_stage(self.chain)
		rank_limit = create_rank_limit(self.rank, task_stage, open_limit=4, total_limit=5, is_listing_allowed=True)
		tasks = [create_task(task_stage) for i in range(3)]

		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_retrieve_if_assignee_or_not(self):
		rank_record = create_rank_record(user=self.user, rank=self.rank)
		task_stage = create_task_stage(self.chain)
		rank_limit = create_rank_limit(self.rank, task_stage)
		tasks = [create_task(task_stage) for i in range(3)]

		# if not assignee
		for task in tasks:
			response = self.client.get(self.url + f"{task.id}/")
			self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

		# if assignee
		for i, task in enumerate(tasks):
			task.assignee = self.user
			task.save()
			response = self.client.get(self.url + f"{task.id}/")
			response.render()
			self.assertEqual(response.status_code, status.HTTP_200_OK)

			expected_task = TaskDefaultSerializer(task).data
			self.assertEqual(expected_task, json.loads(response.content))

	def test_retrieve_if_manager_of_asked_campaign(self):
		self.user.managed_campaigns.add(self.campaign)
		task_stage = create_task_stage(self.chain)
		tasks = [create_task(task_stage) for i in range(3)]

		for i, task in enumerate(tasks):
			response = self.client.get(self.url + f"{task.id}/")
			response.render()
			self.assertEqual(response.status_code, status.HTTP_200_OK)

			expected_task = TaskDefaultSerializer(task).data
			self.assertEqual(expected_task, json.loads(response.content))

	def test_retrieve_if_manager_not_this_campaign(self):
		another_campaign = create_campaign(name="campaign not for using")
		self.user.managed_campaigns.add(another_campaign)
		task_stage = create_task_stage(self.chain)
		tasks = [create_task(task_stage) for i in range(3)]

		for i, task in enumerate(tasks):
			response = self.client.get(self.url + f"{task.id}/")
			response.render()
			self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_create_relevant_task_stages(self):
		task_stage = create_task_stage(self.chain)
		create_rank_limit(rank=self.rank, task_stage=task_stage)
		create_rank_record(user=self.user, rank=self.rank)
		task = {
			'stage': task_stage.id,
		}
		request = self.factory.post(self.url, data=task)
		force_authenticate(request=request, user=self.user)
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_user_no_relevant_task_stages(self):
		task_stage = create_task_stage(self.chain)
		rank_limit = create_rank_limit(rank=self.rank, task_stage=task_stage)
		rank_record = create_rank_record(user=self.user, rank=self.rank)

		tasks = [create_task(task_stage=task_stage,
							 assignee=self.user)
				 for i in range(rank_limit.total_limit)]

		task = {
			'stage': task_stage.id,
			'assignee': self.user.id
		}
		request = self.factory.post(self.url, data=task)
		force_authenticate(request=request, user=self.user)
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_create_tasks_dua_requests_if_relevant_stages(self):
		task_stage = create_task_stage(self.chain)
		rank_limit = create_rank_limit(rank=self.rank, task_stage=task_stage)
		rank_record = create_rank_record(user=self.user, rank=self.rank)

		for i in range(rank_limit.total_limit):
			task = {
				'stage': task_stage.id,
				'assignee': self.user.id
			}
			request = self.factory.post(self.url, data=task)
			force_authenticate(request=request, user=self.user)
			response = self.view(request)
			self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_update_assigned_task(self):
		task_stage = create_task_stage(self.chain)
		create_rank_limit(rank=self.rank, task_stage=task_stage)
		create_rank_record(user=self.user, rank=self.rank)

		task = create_task(task_stage=task_stage, assignee=self.user)
		updated_task = {
			'complete': True
		}
		response = self.client.patch(self.url + f'{task.id}/', updated_task)
		response.render()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(json.loads(response.content), {"complete": True, "responses": None, "id": task.id})

	def test_update_not_assigned_task(self):
		task_stage = create_task_stage(self.chain)
		create_rank_limit(rank=self.rank, task_stage=task_stage)
		create_rank_record(user=self.user, rank=self.rank)

		task = create_task(task_stage=task_stage)
		updated_task = {
			'complete': True
		}
		response = self.client.patch(self.url + f'{task.id}/', updated_task)
		response.render()
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_user_relevant_tasks(self):
		"""
		According to permissions, returns 200 OK only if the user is manager or
		there are tasks assigned to the user. See is_manager_or_have_assignee_task
		"""
		#response = self.client.get(self.url + "user_relevant/")
		#self.assertEqual(response.status_code, status.HTTP_200_OK)
		pass

	def test_user_selectable_and_relevant_tasks(self):
		task_stage = create_task_stage(self.chain)
		rank_limit = create_rank_limit(
			rank=self.rank,
			task_stage=task_stage,
			is_listing_allowed=True
		)
		rank_record = create_rank_record(user=self.user, rank=self.rank)

		tasks = [create_task(task_stage=task_stage) for i in range(4)]
		response = self.client.get(self.url + "user_selectable/")
		content = json.loads(response.content)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(content), len(tasks))
		for task in tasks:
			expected_task = TaskDefaultSerializer(task).data
			self.assertIn(expected_task, content)

	def test_user_selectable_no_relevant_tasks(self):
		task_stage = create_task_stage(self.chain)
		rank_limit = create_rank_limit(
			rank=self.rank,
			task_stage=task_stage,
			# is_listing_allowed=True #if uncomment would be relevant tasks
		)
		rank_record = create_rank_record(user=self.user, rank=self.rank)

		tasks = [create_task(task_stage=task_stage) for i in range(4)]
		response = self.client.get(self.url + "user_selectable/")

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


	def test_user_selectable_and_relevant_tasks_if_no_rank_record(self):
		task_stage = create_task_stage(self.chain)
		rank_limit = create_rank_limit(
			rank=self.rank,
			task_stage=task_stage,
			is_listing_allowed=True
		)

		tasks = [create_task(task_stage=task_stage) for i in range(4)]
		response = self.client.get(self.url + "user_selectable/")
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_user_selectable_and_relevant_tasks_if_no_tasks(self):
		task_stage = create_task_stage(self.chain)
		rank_limit = create_rank_limit(
			rank=self.rank,
			task_stage=task_stage,
			is_listing_allowed=True
		)
		rank_record = create_rank_record(user=self.user, rank=self.rank)

		response = self.client.get(self.url + "user_selectable/")
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ConditionalStageViewSetTest(APITestCase):
	def setUp(self):
		self.url = reverse('conditionalstage-list')
		self.factory = APIRequestFactory()
		self.user = CustomUser.objects.create_user(
			username='test',
			email='test@mail.ru',
			password='test'
		)

		self.client.force_authenticate(user=self.user)
		self.campaign = Campaign.objects.create(name='Test campaign view')
		self.chain = Chain.objects.create(name='Test chain view', campaign=self.campaign)
		self.view = ConditionalStageViewSet.as_view({'get': 'list', 'post': 'create', 'patch': 'partial_update'})
		self.conditional_stage = {
			"name": "Test",
			"x_pos": "34.20000000000000",
			"y_pos": "21.10000000000000",
			'chain': self.chain.id,
		}

	def test_conditional_stage_page_loads_fail(self):
		response = self.client.get('/conditionalstage-list/api/test/')
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_conditional_stage_page_loads_success(self):
		self.user.managed_campaigns.add(self.campaign)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_conditional_stage_get_all_list(self):
		conditions = {
                "field": "verified",
                "condition": "==",
                "value": "Да"
				}

		conditional_stage = ConditionalStage.objects.create(
			name='conditional stage test',
			chain=self.chain,
			x_pos=1, y_pos=1,
			conditions=conditions
		)
		self.user.managed_campaigns.add(self.campaign)
		response = self.client.get(self.url)
		data = ConditionalStageSerializer(conditional_stage).data
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn(data, json.loads(response.content))
		self.assertNotEqual(len(json.loads(response.content)), 0)

	def test_conditional_stage_created(self):
		data_to_create = {
    	"name": "Test",
    	"x_pos": "34.20000000000000",
    	"y_pos": "21.10000000000000",
		'chain': 1,
		}

		request = self.factory.post(self.url, data_to_create)
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

		force_authenticate(request=request, user=self.user)
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		response_data = response.data
		for key in data_to_create.keys():
			self.assertEqual(data_to_create[key], response_data[key])

	def test_if_no_conditional_stages(self):
		self.client.force_authenticate(user=self.user)
		response = self.client.get(self.url, format='json')
		self.assertEqual(len(response.data), 0)

class RankViewSetTest(APITestCase):
	def setUp(self):
		self.url = reverse('rank-list')
		self.factory = APIRequestFactory()
		self.user = CustomUser.objects.create_user(
			username='test',
			email='test@mail.ru',
			password='test'
		)

		self.client.force_authenticate(user=self.user)
		self.rank = Rank.objects.create(name='test rank')
		self.view = RankViewSet.as_view({'get': 'list', 'post': 'create', 'patch': 'partial_update'})

	def test_get_list_if_not_manager(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_get_list_if_manager(self):
		new_campaign = create_campaign()
		self.user.managed_campaigns.add(new_campaign)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

#нужно ли тут аутентифицировать юзера?
	def test_create_if_not_manager(self):
		data_to_create = {
			'name':'test',
			'description':'test description'
		}

		request = self.factory.post(self.url, data_to_create)
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_create_if_user_manager(self):
		new_campaign = create_campaign()
		self.user.managed_campaigns.add(new_campaign)
		data_to_create = {
			'name':'test',
			'description':'test description'
		}
		request = self.factory.post(self.url, data_to_create)
		force_authenticate(request=request, user=self.user)
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		response_data = response.data
		for key in data_to_create.keys():
			self.assertEqual(data_to_create[key], response_data[key])

	def test_partial_update_if_not_manager(self):
		new_rank = Rank.objects.create(name='test')
		url = self.url + str(new_rank.id) + '/'
		request = self.factory.patch(url, {'name':'test edit forbidden'})
		force_authenticate(request=request, user=self.user)
		response = self.view(request, pk=str(new_rank.id))
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_partial_update_if_manager(self):
		new_campaign = create_campaign()
		self.user.managed_campaigns.add(new_campaign)
		new_track = Track.objects.create(name='test track', campaign=new_campaign, default_rank=self.rank)
		new_track.ranks.add(self.rank)
		url = self.url + str(self.rank.id) + '/'
		response = self.client.patch(url, {'name':'test edit'})
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_retrieve_if_not_manager(self):
		new_rank = Rank.objects.create(name='test')
		url = self.url + str(new_rank.id) + '/'
		request = self.factory.get(url, format='json')
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_retrieve_if_manager(self):
		new_campaign = create_campaign()
		self.user.managed_campaigns.add(new_campaign)
		new_track = Track.objects.create(name='test track', campaign=new_campaign, default_rank=self.rank)
		new_track.ranks.add(self.rank)
		url = self.url + str(self.rank.id) + '/'
		response = self.client.get(url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_destroy(self):
		new_campaign = create_campaign()
		self.user.managed_campaigns.add(new_campaign)
		url = self.url + str(self.rank.id) + '/'
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RankLimitViewSetTest(APITestCase):
	def setUp(self):
		self.url = reverse('ranklimit-list')
		self.factory = APIRequestFactory()
		self.user = CustomUser.objects.create_user(
			username='test',
			email='test@mail.com',
			password='test'
		)

		self.client.force_authenticate(user=self.user)
		self.rank = create_rank()
		self.campaign = create_campaign()
		self.chain = Chain.objects.create(name='chain test', campaign=self.campaign)
		self.task_stage = TaskStage.objects.create(
		name=f'Task stage testing ',
		chain=self.chain,x_pos=1, y_pos=1,
		is_creatable=True)
		self.rank_limit = RankLimit.objects.create(
			rank=self.rank,
			stage=self.task_stage)
		self.view = RankLimitViewSet.as_view({'get': 'list', 'post': 'create', 'patch': 'partial_update'})

	def test_get_list_if_manager_does_not_exist(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_get_list_if_manager_exists(self):
		self.user.managed_campaigns.add(self.campaign)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_create_if_not_manager(self):
		test_rank = create_rank()
		test_chain = Chain.objects.create(name='chain test 2', campaign=self.campaign)
		test_task_stage = TaskStage.objects.create(
		name=f'Task stage test 2',
		chain=test_chain,x_pos=2, y_pos=3,
		is_creatable=True)
		data_to_create = {
			'rank': test_rank.id,
			'stage': test_task_stage.id,
		}
		request = self.factory.post(self.url, data_to_create)
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_create_if_manager(self):
		test_rank = create_rank()
		test_chain = Chain.objects.create(name='chain test 2', campaign=self.campaign)
		test_task_stage = TaskStage.objects.create(
		name=f'Task stage test 2',
		chain=test_chain,x_pos=2, y_pos=3,
		is_creatable=True)
		self.user.managed_campaigns.add(self.campaign)
		data_to_create = {
			'rank': test_rank.id,
			'stage': test_task_stage.id,
		}
		request = self.factory.post(self.url, data_to_create)
		force_authenticate(request=request, user=self.user)
		response = self.view(request)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		response_data = response.data
		for key in data_to_create.keys():
			self.assertEqual(data_to_create[key], response_data[key])

	def test_partial_update_if_not_manager(self):
		new_track = Track.objects.create(name='test track', campaign=self.campaign, default_rank=self.rank)
		new_track.ranks.add(self.rank)
		url = self.url + str(self.rank_limit.id) + '/'
		request = self.factory.patch(url, {'rank':2, 'stage':1})
		force_authenticate(request=request, user=self.user)
		response = self.view(request, pk=str(self.rank_limit.id))
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_partial_update_if_manager(self):
		rank_test = create_rank()
		self.user.managed_campaigns.add(self.campaign)
		new_track = Track.objects.create(name='test track', campaign=self.campaign, default_rank=self.rank)
		new_track.ranks.add(self.rank)
		url = self.url + str(self.rank_limit.id) + '/'
		response = self.client.patch(url, {'rank':rank_test.id})
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_destroy(self):
		self.user.managed_campaigns.add(self.campaign)
		url = self.url + str(self.rank_limit.id) + '/'
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_retrieve_if_not_manager(self):
		url = self.url + str(self.rank_limit.id) + '/'
		response = self.client.get(url)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_retrieve_if_manager(self):
		self.user.managed_campaigns.add(self.campaign)
		new_track = Track.objects.create(name='test track', campaign=self.campaign, default_rank=self.rank)
		new_track.ranks.add(self.rank)
		url = self.url + str(self.rank_limit.id) + '/'
		response = self.client.get(url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)


class RankRecordViewSetTest(APITestCase):
	def setUp(self):
		self.url = reverse('rankrecord-list')
		self.factory = APIRequestFactory()
		self.user = CustomUser.objects.create_user(
			username='test',
			email='test@mail.ru',
			password='test'
		)

		self.client.force_authenticate(user=self.user)
		self.campaign = create_campaign()
		self.rank = Rank.objects.create(name='test rank')
		self.rank_record = RankRecord.objects.create(user=self.user, rank=self.rank)
		self.view = RankRecordViewSet.as_view({'get': 'list', 'post': 'create', 'patch': 'partial_update'})

	def test_get_list_if_not_manager(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_get_list_if_manager(self):
		self.user.managed_campaigns.add(self.campaign)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_retrieve_if_not_manager(self):
		url = self.url + str(self.rank_record.id) + '/'
		response = self.client.get(url)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_retrieve_if_manager(self):
		self.user.managed_campaigns.add(self.campaign)
		new_track = Track.objects.create(name='test track', campaign=self.campaign, default_rank=self.rank)
		new_track.ranks.add(self.rank)
		url = self.url + str(self.rank_record.id) + '/'
		response = self.client.get(url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_create_if_not_manager(self):
		test_user = CustomUser.objects.create(
			username='test2',
			email='test2@mail.com',
			password='test2'
		)
		test_rank = Rank.objects.create(name='test2')
		data_to_create = {
			'user':test_user.id,
			'rank':test_rank.id
		}
		response = self.client.post(self.url, data_to_create)
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_create_if_manager(self):
		test_user = CustomUser.objects.create(
			username='test2',
			email='test2@mail.com',
			password='test2'
		)
		test_rank = Rank.objects.create(name='test2')
		data_to_create = {
			'user':test_user.id,
			'rank':test_rank.id
		}
		self.user.managed_campaigns.add(self.campaign)
		response = self.client.post(self.url, data_to_create)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

	def test_partial_update_if_not_manager(self):
		new_track = Track.objects.create(name='test track', campaign=self.campaign, default_rank=self.rank)
		new_track.ranks.add(self.rank)
		url = self.url + str(self.rank_record.id) + '/'
		response = self.client.patch(url, {'user':1})
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_partial_update_if_manager(self):
		self.user.managed_campaigns.add(self.campaign)
		new_track = Track.objects.create(name='test track', campaign=self.campaign, default_rank=self.rank)
		new_track.ranks.add(self.rank)
		url = self.url + str(self.rank_record.id) + '/'
		reponse = self.client.patch(url, {'user':1})
		self.assertEqual(reponse.status_code, status.HTTP_200_OK)

	def test_destroy(self):
		self.user.managed_campaigns.add(self.campaign)
		url = self.url + str(self.rank_record.id) + '/'
		reponse = self.client.delete(url)
		self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)

class TrackViewSetTest(APITestCase):
	def setUp(self):
		self.url = reverse('track-list')
		self.factory = APIRequestFactory()
		self.user = CustomUser.objects.create_user(
			username='test',
			email='test@mail.com',
			password='test'
		)

		self.client.force_authenticate(user=self.user)
		self.campaign = create_campaign()
		self.rank = Rank.objects.create(name='test rank')
		self.new_track = Track.objects.create(name='test track', campaign=self.campaign)
		self.new_track.ranks.add(self.rank)

	def test_get_list_if_not_manager(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_get_list_if_manager(self):
		self.user.managed_campaigns.add(self.campaign)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_create_if_manager(self):
		data_to_create = {
			'name': 'test track 2',
			'campaign': self.campaign.id,
			'ranks': [
				1,
			]
		}

		self.user.managed_campaigns.add(self.campaign)
		response = self.client.post(self.url, data_to_create)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		response_data = response.data
		for key in data_to_create.keys():
			self.assertEqual(data_to_create[key], response_data[key])

	def test_create_if_not_manager(self):
		data_to_create = {
			'name': 'test track 2',
			'campaign': self.campaign.id,
			'ranks': [
				1,
			]
		}

		response = self.client.post(self.url, data_to_create)
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_partial_update_if_manager(self):
		self.user.managed_campaigns.add(self.campaign)
		test_rank = Rank.objects.create(name='test rank 2.0')
		url = self.url + str(self.new_track.id) + '/'
		response = self.client.patch(url, {'name': 'test Track 2.0', 'ranks':[2]})
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_partial_update_if_not_manager(self):
		test_rank = Rank.objects.create(name='test rank 2.0')
		url = self.url + str(self.new_track.id) + '/'
		response = self.client.patch(url, {'name': 'test Track 2.0', 'ranks':[2]})
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_retrieve_if_not_manager(self):
		url = self.url + str(self.new_track.id) + '/'
		response = self.client.get(url)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_retrieve_if_manager(self):
		self.user.managed_campaigns.add(self.campaign)
		url = self.url + str(self.new_track.id) + '/'
		response = self.client.get(url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_destroy(self):
		self.user.managed_campaigns.add(self.campaign)
		url = self.url + str(self.new_track.id) + '/'
		response = self.client.delete(url)
		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)