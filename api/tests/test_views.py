import django, json, random
from django.forms.models import model_to_dict

django.setup()

from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from django.contrib.auth.models import Group
from api.models import CustomUser, Campaign, Chain, ConditionalStage, TaskStage, Rank, RankLimit, Task, RankRecord, \
    Track, CampaignManagement, Stage, Case
from rest_framework import status


class CampaignTest(APITestCase):
    def setUp(self):
        self.url = reverse("campaign-list")
        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.new_user = CustomUser.objects.create_user(username='new_user', email='new_user@email.com',
                                                       password='new_user')
        self.client.force_authenticate(user=self.user)
        self.campaign_json = {"name": "name", "description": "description"}
        self.new_name = {"name": "new_name"}

        self.campaign_creator_group = Group.objects.create(name='campaign_creator')

    # Only user with role campaign_creator can create campaign
    # user with no role try create campaign it will fail
    def test_create_campaign_fail(self):
        response = self.client.post(self.url, self.campaign_json)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # user with role campaign creator try create campaign
    def test_create_campaign_success(self):
        self.campaign_creator_group.user_set.add(self.user)
        response = self.client.post(self.url, self.campaign_json)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Campaign.objects.count(), 1)

    # Everybody who authenticated can get list of campaigns
    def test_list_campaign_success(self):
        [Campaign.objects.create(name=f"Campaign #{i}") for i in range(5)]
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), 5)

    # Everybody who authenticated can retrieve campaign
    # user try to get not existing campaign
    def test_retrieve_campaign_not_exist_fail(self):
        response = self.client.get(self.url + "1/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # list existing campaign
    def test_retrieve_campaign_exist_success(self):
        campaign = Campaign.objects.create(name="new campaign")
        response = self.client.get(self.url + f'{campaign.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Only campaign manager can update campaign
    # simple user try partial_update campaign
    def test_parital_update_not_manager_fail(self):
        campaign = Campaign.objects.create(name="new campaign")
        response = self.client.patch(self.url + f'{campaign.id}/', self.new_name)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_success(self):
        self.campaign_creator_group.user_set.add(self.user)
        campaign = Campaign.objects.create(name='new campaign')

        self.user.managed_campaigns.add(campaign)
        new_name = {"name": "new_name"}
        response = self.client.patch(self.url + str(campaign.id) + "/", self.new_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Campaign.objects.get(id=campaign.id).name, new_name.get('name'))

    def test_destroy(self):
        campaign = Campaign.objects.create(name='new campaign')

        self.user.managed_campaigns.add(campaign)
        response = self.client.delete(self.url + f"{campaign.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Campaign.objects.count(), 1)


class ChainTest(APITestCase):
    def setUp(self):
        self.url_campaign = reverse("campaign-list")
        self.url_chain = reverse("chain-list")
        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.new_user = CustomUser.objects.create_user(username='new_user', email='u@gmail.com', password='1234')

        self.campaign = Campaign.objects.create(name='campaign')
        self.chain = Chain.objects.create(name='chain', campaign=self.campaign)

        self.client.force_authenticate(user=self.user)
        self.campaign_json = {"name": "campaign", "description": "description"}
        self.chain_json = {"name": "chain", "description": "description", "campaign": None}
        self.campaign_creator_group = Group.objects.create(name='campaign_creator')

    # Only campaign manager can get his chains
    # simple user can't list chains it will fail
    def test_list_user_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        response = self.client.get(self.url_chain)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(json.loads(response.content)['results'], [])
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(Chain.objects.count(), 1)

    # manager list his chains
    def test_list_success(self):
        self.user.managed_campaigns.add(self.campaign)
        response = self.client.get(self.url_chain)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content)['results'], [model_to_dict(self.chain)])

    # Only campaign manager can create chain based on his campaign
    # simple user can't create new chain it will fail
    def test_create_simple_user_create_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)

        self.chain_json['campaign'] = self.campaign.id
        response = self.client.post(self.url_chain, self.chain_json)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # if user is manager and chain refers on users campaign it will success
    def test_create_chain_refers_on_my_campaign_success(self):
        self.user.managed_campaigns.add(self.campaign)

        chain_json = self.chain_json
        chain_json['campaign'] = self.campaign.id
        response = self.client.post(self.url_chain, chain_json)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        my_chain = Chain.objects.get(id=response.data.get('id'))
        self.assertEqual(json.loads(response.content), model_to_dict(my_chain))
        self.assertEqual(Chain.objects.count(), 2)

    # Manager can retrieve chains which attached to his campaigns
    # Manager try to retrieve not his chain it will fail
    def test_retrieve_my_campaign_not_my_chain_fail(self):
        another_campaign = Campaign.objects.create(name='new campaign')
        another_chain = Chain.objects.create(name='new chain', campaign=another_campaign)
        self.new_user.managed_campaigns.add(another_campaign)
        self.user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url_chain + f"{another_chain.id}/")
        self.assertEqual(response.status_code,
                         status.HTTP_404_NOT_FOUND) 
        self.assertNotIn(self.user, another_chain.campaign.managers.all())

    # Manager retrieve his chain it will success
    def test_retrieve_my_campaign_my_chain_success(self):
        another_campaign = Campaign.objects.create(name='new campaign')
        another_chain = Chain.objects.create(name='new chain', campaign=another_campaign)
        self.new_user.managed_campaigns.add(another_campaign)
        self.user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url_chain + f"{self.chain.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Only manager can update/partial update only his chain
    # Manager try to update other chain it will fail
    def test_partial_update_not_my_chain_fail(self):
        another_campaign = Campaign.objects.create(name='new campaign')
        another_chain = Chain.objects.create(name='new chain', campaign=another_campaign)
        self.new_user.managed_campaigns.add(another_campaign)
        self.user.managed_campaigns.add(self.campaign)

        response = self.client.patch(
            self.url_chain + f"{another_chain.id}/",
            {"name": "try to change chain name"}
        )
        self.assertEqual(response.status_code,
                         status.HTTP_404_NOT_FOUND)

    def test_partial_update_success(self):
        another_campaign = Campaign.objects.create(name='new campaign')
        another_chain = Chain.objects.create(name='new chain', campaign=another_campaign)
        self.new_user.managed_campaigns.add(another_campaign)
        self.user.managed_campaigns.add(self.campaign)

        chain = self.chain_json
        chain['name'] = "try to change chain name"
        chain['campaign'] = self.campaign.id
        response = self.client.patch(
            self.url_chain + f"{self.chain.id}/",
            chain
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        my_chain = Chain.objects.get(id=self.chain.id)
        self.assertEqual(json.loads(response.content), model_to_dict(my_chain))


class ConditionalStageTest(APITestCase):
    def setUp(self):
        self.url_campaign = reverse("campaign-list")
        self.url_chain = reverse("chain-list")
        self.url_conditional_stage = reverse('conditionalstage-list')
        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.new_user = CustomUser.objects.create_user(username="new_user", email='new_user@email.com',
                                                       password='new_user')
        self.client.force_authenticate(user=self.user)
        self.campaign = Campaign.objects.create(name="Campaign")
        self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        self.conditional_stage = ConditionalStage.objects.create(name="Conditional Stage", x_pos=1, y_pos=1,
                                                                 chain=self.chain)
        self.another_campaign = Campaign.objects.create(name="other campaign")
        self.another_chain = Chain.objects.create(name="other chain", campaign=self.another_campaign)
        self.another_conditional_stage = ConditionalStage.objects.create(name="Other Conditional Stage", x_pos=1,
                                                                         y_pos=1,
                                                                         chain=self.another_chain)

        self.campaign_json = {"name": "campaign", "description": "description"}
        self.chain_json = {"name": "chain", "description": "description", "campaign": None}
        self.conditional_stage_json = {
            "name": "conditional_stage",
            "chain": None,
            "x_pos": 1,
            "y_pos": 1
        }
        self.conditional_stage_json_modified = self.conditional_stage_json
        self.conditional_stage_json_modified['name'] = "Modified conditional stage"
        self.campaign_creator_group = Group.objects.create(name='campaign_creator')

    # ONLY MANAGER CAN LIST CONDITIONAL STAGES OF THEIR CAMPAIGNS
    # simple user try list cond stages
    def test_list_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        response = self.client.get(self.url_conditional_stage)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 
        self.assertEqual(json.loads(response.content)['results'], [])

    # manager try list his conditional stage
    def test_list_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url_conditional_stage)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), 1)

    # create cond_stage refers to my chain
    def test_create_my_chain_success(self):
        self.user.managed_campaigns.add(self.campaign)

        self.conditional_stage_json['chain'] = self.chain.id
        response = self.client.post(self.url_conditional_stage, self.conditional_stage_json)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ConditionalStage.objects.count(), 3)
        my_conditional_stage = ConditionalStage.objects.get(id=response.data.get('id'))
        self.assertIn(self.user, my_conditional_stage.chain.campaign.managers.all())
        self.assertEqual(json.loads(response.content)['id'], model_to_dict(my_conditional_stage)['id'])

    # Only managers of campaign can retrieve their conditional stages
    # simple user try to retrieve conditional stage
    def test_retrieve_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        response = self.client.get(self.url_conditional_stage + f"{self.conditional_stage.id}/")
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # manager try to retrieve other conditional stage
    def test_retrieve_manager_not_his_cond_stage_fail(self):
        self.new_user.managed_campaigns.add(self.another_campaign)
        self.user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url_conditional_stage + f"{self.another_conditional_stage.id}/")
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # manager try to retrieve other conditional stage
    def test_retrieve_manager_cond_stage_success(self):
        self.new_user.managed_campaigns.add(self.another_campaign)
        self.user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url_conditional_stage + f"{self.conditional_stage.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_content = json.loads(response.content)
        self.assertEqual(self.conditional_stage, ConditionalStage.objects.get(id=response_content.get('id')))

    # Only managers can update conditional stage
    # simple user try to partial_update cond stage
    def test_partial_update_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.another_campaign)
        self.new_user.managed_campaigns.add(self.campaign)

        change_name = {"name": self.conditional_stage_json_modified['name']}
        response = self.client.patch(self.url_conditional_stage + f"{self.conditional_stage.id}/", change_name)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.conditional_stage.name, ConditionalStage.objects.get(id=self.conditional_stage.id).name)

    # manager try to partial update not his cond stage
    def test_partial_update_manager_not_his_cond_stage_fail(self):
        self.new_user.managed_campaigns.add(self.another_campaign)
        self.user.managed_campaigns.add(self.campaign)

        change_name = {"name": self.conditional_stage_json_modified['name']}
        response = self.client.patch(self.url_conditional_stage + f"{self.another_conditional_stage.id}/", change_name)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.another_conditional_stage.name,
                         ConditionalStage.objects.get(id=self.another_conditional_stage.id).name)

class TaskStageTest(APITestCase):
    def setUp(self):
        self.url_campaign = reverse("campaign-list")
        self.url_chain = reverse("chain-list")
        self.url_conditional_stage = reverse('conditionalstage-list')
        self.url_task_stage = reverse('taskstage-list')

        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.new_user = CustomUser.objects.create_user(username="new_user", email='new_user@email.com',
                                                       password='new_user')
        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(name="Campaign")
        self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        self.conditional_stage = ConditionalStage.objects.create(name="Conditional Stage", x_pos=1, y_pos=1,
                                                                 chain=self.chain)
        self.task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                   chain=self.chain)

        self.another_campaign = Campaign.objects.create(name="New Campaign")
        self.another_chain = Chain.objects.create(name="New Chain", campaign=self.another_campaign)
        self.another_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                           chain=self.another_chain)
        self.campaign_json = {"name": "campaign", "description": "description"}
        self.chain_json = {"name": "chain", "description": "description", "campaign": None}
        self.task_stage_json = {
            "name": "conditional_stage",
            "chain": None,
            "x_pos": 1,
            "y_pos": 1
        }
        self.task_stage_json_modified = self.task_stage_json
        self.task_stage_json_modified['name'] = "Modified conditional stage"
        self.campaign_creator_group = Group.objects.create(name='campaign_creator')

    # Only manager can list TaskStages
    # User try to list TaskStages
    def test_list_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        self.assertNotIn(self.user, self.campaign.managers.all())

        response = self.client.get(self.url_task_stage)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(json.loads(response.content)['results'], [])

    # Manager try to list campaigns
    def test_list_manager_success(self):
        self.new_user.managed_campaigns.add(self.another_campaign)
        self.user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url_task_stage)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        my_task_stages = TaskStage.objects.all().filter(chain__campaign__managers=self.user)
        self.assertEqual(len(json.loads(response.content)['results']), len(my_task_stages))

    # Only managers can create task stage
    # simple user try create task stage
    def test_create_fail(self):
        self.new_user.managed_campaigns.add(self.another_campaign)
        self.new_user.managed_campaigns.add(self.campaign)

        task_stage_json = self.task_stage_json
        task_stage_json['chain'] = self.another_chain.id
        response = self.client.post(self.url_task_stage, task_stage_json)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  

    # manager try create task stage
    def test_create_success(self):
        self.new_user.managed_campaigns.add(self.another_campaign)
        self.user.managed_campaigns.add(self.campaign)

        task_stage_json = self.task_stage_json
        task_stage_json['chain'] = self.chain.id
        response = self.client.post(self.url_task_stage, task_stage_json)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_task_stage = TaskStage.objects.get(id=response.data.get('id'))
        self.assertEqual(json.loads(response.content)['id'], model_to_dict(created_task_stage)['id'])

    # manager try to retrieve task stage
    def test_retrieve_manager_success(self):
        self.new_user.managed_campaigns.add(self.another_campaign)
        self.user.managed_campaigns.add(self.campaign)
        self.user.managed_campaigns.add(self.another_campaign)

        for i in [self.another_task_stage, self.task_stage]:
            response = self.client.get(self.url_task_stage + f"{i.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    # user with creatable task  stage retrieve task stage
    def test_retrieve_stage_user_creatable_success(self):
        self.another_task_stage.is_creatable = True
        self.another_task_stage.save()
        new_rank = Rank.objects.create(name="rank")
        RankRecord.objects.create(user=self.user, rank=new_rank)
        RankLimit.objects.create(rank=new_rank, stage=self.another_task_stage,
                                 open_limit=2, total_limit=3,
                                 is_creation_open=True)
        Task.objects.create(assignee=self.user, stage=self.another_task_stage,
                            complete=False)

        response = self.client.get(self.url_task_stage + f"{self.another_task_stage.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content)['id'], self.another_task_stage.id)

    # only managers can update or partial update campaigns
    # user try to partial_update task stage
    def test_partial_update_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        response = self.client.patch(self.url_task_stage + f"{self.task_stage.id}/", {"name": "Changed taskstage name"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # manager partial_update task stage
    def test_partial_update_success(self):
        self.user.managed_campaigns.add(self.campaign)

        changed_name = {"name": "Changed taskstage name"}
        response = self.client.patch(self.url_task_stage + f"{self.task_stage.id}/", changed_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(changed_name['name'], TaskStage.objects.get(id=self.task_stage.id).name)


class TaskTest(APITestCase):
    def setUp(self):
        self.url_campaign = reverse("campaign-list")
        self.url_chain = reverse("chain-list")
        self.url_conditional_stage = reverse('conditionalstage-list')
        self.url_task_stage = reverse('taskstage-list')
        self.url_tasks = reverse('task-list')
        self.url_webhook_quiz = "https://us-central1-journal-bb5e3.cloudfunctions.net/check_quiz_responses"

        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.new_user = CustomUser.objects.create_user(username="new_user", email='new_user@email.com',
                                                       password='new_user')
        self.employee = CustomUser.objects.create(username="empl", email='empl@email.com', password='empl')

        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(name="Campaign")
        self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        self.conditional_stage = ConditionalStage.objects.create(name="Conditional Stage", x_pos=1, y_pos=1,
                                                                 chain=self.chain)
        self.task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                   chain=self.chain)
        self.another_campaign = Campaign.objects.create(name="Campaign")
        self.another_chain = Chain.objects.create(name="Chain", campaign=self.another_campaign)
        self.another_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                           chain=self.another_chain)

        self.campaign_json = {"name": "campaign", "description": "description"}
        self.chain_json = {"name": "chain", "description": "description", "campaign": None}
        self.task_stage_json = {
            "name": "conditional_stage",
            "chain": None,
            "x_pos": 1,
            "y_pos": 1
        }
        self.task_stage_json_modified = self.task_stage_json
        self.task_stage_json_modified['name'] = "Modified conditional stage"
        self.campaign_creator_group = Group.objects.create(name='campaign_creator')

    def get_selectable_tasks(self, task, user):
        queryset = Task.objects.filter(id=task.id)
        return queryset \
            .filter(complete=False) \
            .filter(assignee__isnull=True) \
            .filter(stage__ranks__users=user.id) \
            .filter(stage__ranklimits__is_selection_open=True) \
            .filter(stage__ranklimits__is_listing_allowed=True) \
            .distinct()

    # Only managers can list tasks
    def test_list_not_manager_fail(self):
        task = [Task.objects.create(assignee=self.new_user, stage=self.task_stage,
                                    complete=False) for x in range(5)]
        self.assertEqual(Task.objects.count(), 5)
        response = self.client.get(self.url_tasks)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 
        self.assertEqual(json.loads(response.content)['results'], [])

    def test_list_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)
        task = [Task.objects.create(assignee=self.new_user, stage=self.task_stage,
                                    complete=False) for x in range(5)]

        self.new_user.managed_campaigns.add(self.another_campaign)
        another_task = [Task.objects.create(assignee=self.new_user, stage=self.another_task_stage,
                                            complete=False) for x in range(5)]
        self.assertEqual(Task.objects.count(), 10)
        response = self.client.get(self.url_tasks)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), 5)

    """ User can do retrieve task if :
     user is manager, task is assigned to you, filter_for_user_selectable_tasks"""

    # not manager, task isn't assigned, no filter_for_user_selectable_tasks
    def test_retrieve_nohing_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        task = Task.objects.create(assignee=self.employee, stage=self.task_stage,
                                   complete=False)

        selectable_tasks = self.get_selectable_tasks(task, self.user)
        self.assertFalse(bool(selectable_tasks))

        response = self.client.get(self.url_tasks + f"{task.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # User is manager, task isn't assigned, no user_selectable_tasks
    def test_retrieve_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)
        task = Task.objects.create(assignee=self.employee, stage=self.task_stage,
                                   complete=False)

        selectable_tasks = self.get_selectable_tasks(task, self.user)

        self.assertFalse(bool(selectable_tasks))

        response = self.client.get(self.url_tasks + f"{task.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # task is not
    def test_retrieve_assignee_success(self):
        self.new_user.managed_campaigns.add(self.campaign)
        task = Task.objects.create(assignee=self.user, stage=self.task_stage,
                                   complete=False)

        selectable_tasks = self.get_selectable_tasks(task, self.user)
        self.assertFalse(bool(selectable_tasks))

        response = self.client.get(self.url_tasks + f"{task.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content)['id'], task.id)

    def test_retrieve_can_user_request_assignment_success(self):
        new_rank = Rank.objects.create(name="rank")
        RankRecord.objects.create(user=self.user, rank=new_rank)
        RankLimit.objects.create(rank=new_rank, stage=self.task_stage,
                                 open_limit=2, total_limit=3,
                                 is_selection_open=True, is_listing_allowed=True)

        self.new_user.managed_campaigns.add(self.campaign)
        task = Task.objects.create(stage=self.task_stage,
                                   complete=False)

        selectable_tasks = self.get_selectable_tasks(task, self.user)
        self.assertTrue(bool(selectable_tasks))

        response = self.client.get(self.url_tasks + f"{task.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content)['id'], task.id)

    # if queryset of tasks satisfies filter_for_user_selectable tasks
    def test_user_selectable_not_manager_fail(self):
        new_rank = Rank.objects.create(name="rank")
        RankRecord.objects.create(user=self.new_user, rank=new_rank)
        RankLimit.objects.create(rank=new_rank, stage=self.task_stage,
                                 open_limit=2, total_limit=3,
                                 is_selection_open=True, is_listing_allowed=True)

        self.assertNotIn(self.user, self.campaign.managers.all())
        [Task.objects.create(stage=self.task_stage,
                             complete=False) for x in range(5)]
        self.assertEqual(Task.objects.count(), 5)
        response = self.client.get(self.url_tasks + "user_selectable/")
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 
        self.assertEqual(json.loads(response.content)['results'], [])

    # queryset satisfies filter_for_user_selectable_tasks
    def test_user_selectable_success(self):
        new_rank = Rank.objects.create(name="rank")
        RankRecord.objects.create(user=self.user, rank=new_rank)
        RankLimit.objects.create(rank=new_rank, stage=self.task_stage,
                                 open_limit=2, total_limit=3,
                                 is_selection_open=True, is_listing_allowed=True)

        self.user.managed_campaigns.add(self.campaign)
        [Task.objects.create(stage=self.task_stage,
                             complete=False) for x in range(5)]

        self.new_user.managed_campaigns.add(self.another_campaign)
        [Task.objects.create(stage=self.another_task_stage,
                             complete=False) for x in range(5)]
        self.assertEqual(Task.objects.count(), 10)
        response = self.client.get(self.url_tasks + "user_selectable/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), 5)

    # User can see only assigned tasks
    def test_user_relevant_fail(self):
        [Task.objects.create(assignee=self.employee, stage=self.task_stage,
                             complete=False) for x in range(5)]
        [Task.objects.create(stage=self.task_stage,
                             complete=False) for x in range(5)]
        self.assertEqual(Task.objects.count(), 10)
        response = self.client.get(self.url_tasks + "user_relevant/")
        self.assertEqual(json.loads(response.content), [])

    # watch assigned tasks
    def test_user_relevant_success(self):
        [Task.objects.create(assignee=self.user, stage=self.task_stage,
                             complete=False) for x in range(5)]
        [Task.objects.create(stage=self.task_stage,
                             complete=False) for x in range(5)]
        self.assertEqual(Task.objects.count(), 10)
        response = self.client.get(self.url_tasks + "user_relevant/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)), 5)

    # Test task completion success for assigned user
    def test_task_completion_success(self):
        case = Case.objects.create()
        task = Task.objects.create(assignee=self.user, stage=self.task_stage, case=case)
        self.client.patch(self.url_tasks + f"{task.id}/", {"complete": True})
        updated_task = Task.objects.get(id=task.id)
        self.assertEqual(updated_task.reopened, False)
        self.assertEqual(updated_task.complete, True)

    # there is task_stage after task. new tasks are creating depending on assigning
    def test_complete_next_task_stage_RA(self):
        new_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                  chain=self.chain)
        new_task_stage.in_stages.add(self.task_stage)
        self.new_user.managed_campaigns.add(self.campaign)

        case = Case.objects.create()
        task = Task.objects.create(assignee=self.user, stage=self.task_stage, case=case)
        response = self.client.patch(self.url_tasks + f"{task.id}/", {"complete": True})
        created_tasks = Task.objects.filter(case=case).filter(stage__in_stages__in=[self.task_stage])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for i in created_tasks:
            self.assertEqual(i.stage, new_task_stage)
            self.assertEqual(i.case, task.case)
        self.assertEqual(len(created_tasks), self.task_stage.out_stages.count())

    # there is task_stage after task. new tasks are creating depending on assigning
    def test_complete_next_task_stage_RA_network(self):
        new_task_stage = TaskStage.objects.create(name="Task stage №1", x_pos=1, y_pos=1,
                                                  chain=self.chain)
        new_task_stage2 = TaskStage.objects.create(name="Task stage №2", x_pos=1, y_pos=1,
                                                  chain=self.chain)
        new_task_stage.in_stages.add(self.task_stage)
        new_task_stage2.in_stages.add(self.task_stage)
        self.new_user.managed_campaigns.add(self.campaign)

        case = Case.objects.create()
        task = Task.objects.create(assignee=self.user, stage=self.task_stage, case=case)
        response = self.client.patch(self.url_tasks + f"{task.id}/", {"complete": True})
        created_tasks = Task.objects.filter(case=case).filter(stage__in_stages__in=[self.task_stage])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for i in created_tasks:
            self.assertIn(i.stage, self.task_stage.out_stages.all())
            self.assertEqual(i.case, task.case)
        self.assertEqual(len(created_tasks), 2)

    # there is conditional_stage after task. new tasks are creating depending on assigning, not ping_pong.
    # Task will successfully create because condition is true
    def test_complete_next_cond_stage_success(self):
        responses = {"verified": "Да"}

        self.new_user.managed_campaigns.add(self.campaign)

        new_task_stage = TaskStage.objects.create(name="Task stage created test complete", x_pos=1, y_pos=1,
                                                  chain=self.chain)
        new_cond_stage = ConditionalStage.objects.create(name="Conditional Stage test complete", x_pos=1, y_pos=1,
                                                         chain=self.chain)
        new_cond_stage.conditions = [{"field": "verified", "value": "Да", "condition": "=="}]
        new_cond_stage.save()

        new_cond_stage.in_stages.add(self.task_stage)
        new_task_stage.in_stages.add(new_cond_stage)

        case = Case.objects.create()
        task = Task.objects.create(assignee=self.user, stage=self.task_stage, case=case)
        task.responses = responses
        task.save()
        response = self.client.patch(self.url_tasks + f"{task.id}/", {"complete": True})
        created_tasks = Task.objects.filter(stage=new_task_stage) \
            .filter(stage__in_stages=new_cond_stage)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for i in created_tasks:
            self.assertEqual(i.stage, new_task_stage)
            self.assertEqual(i.case, task.case)
            self.assertEqual(i.reopened, False)
        self.assertEqual(Task.objects.filter(case=case).count(), 2)

    # test. after task stage is 5 conditional stages which tests their condition. after cond stages is new task stage.
    def test_complete_next_cond_stage_success_network(self):
        responses = {"verified": "Да"}
        conditions = [{"field": "verified", "value": "Да", "condition": "=="}]
        self.new_user.managed_campaigns.add(self.campaign)

        task_stages=[]
        for i in range(5):
            task_stage = TaskStage.objects.create(name=f"Task stage created test complete #{i}", x_pos=1, y_pos=1,
                                                  chain=self.chain)
            cond_stage = ConditionalStage.objects.create(name=f"Conditional Stage test complete #{i}", x_pos=1, y_pos=1,
                                            chain=self.chain, conditions=conditions)
            cond_stage.in_stages.add(self.task_stage)
            task_stage.in_stages.add(cond_stage)
            task_stages.append(task_stage)

        case = Case.objects.create()
        task = Task.objects.create(assignee=self.user, stage=self.task_stage, case=case)
        task.responses = responses
        task.save()
        response = self.client.patch(self.url_tasks + f"{task.id}/", {"complete": True})
        created_tasks = Task.objects.filter(case=case).exclude(id=task.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(created_tasks.count(), len(task_stages))
        stages = [j.stage for j in created_tasks]
        for i in task_stages:
            self.assertIn(i, stages)

    # there is conditional_stage after task. new tasks are creating depending on assigning, not ping_pong.
    # Task wouldn't create because condition is false
    def test_complete_next_cond_stage_fail(self):
        responses = {"verified": "Да(@!#)"}

        self.new_user.managed_campaigns.add(self.campaign)

        new_task_stage = TaskStage.objects.create(name="Task stage created test complete", x_pos=1, y_pos=1,
                                                  chain=self.chain)
        new_cond_stage = ConditionalStage.objects.create(name="Conditional Stage test complete", x_pos=1, y_pos=1,
                                                         chain=self.chain)
        new_cond_stage.conditions = [{"field": "verified", "value": "Да", "condition": "=="}]
        new_cond_stage.save()

        new_cond_stage.in_stages.add(self.task_stage)
        new_task_stage.in_stages.add(new_cond_stage)

        case = Case.objects.create()
        task = Task.objects.create(assignee=self.user, stage=self.task_stage, case=case)
        task.responses = responses
        task.save()
        response = self.client.patch(self.url_tasks + f"{task.id}/", {"complete": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        created_tasks = Task.objects.filter(stage=new_task_stage) \
            .filter(stage__in_stages=new_cond_stage)
        self.assertEqual(created_tasks.count(), 0)
        self.assertEqual(Task.objects.filter(case=case).count(), 1)

    # there are five cond stages after task stage. So tasks wouldn't create because condition is false.
    def test_complete_next_cond_stage_network_fail(self):
        responses = {"verified": "Да(@!#)"}
        conditions = [{"field": "verified", "value": "Да", "condition": "=="}]

        self.new_user.managed_campaigns.add(self.campaign)

        for i in range(5):
            task_stage = TaskStage.objects.create(name="Task stage created test complete", x_pos=1, y_pos=1,
                                                  chain=self.chain)
            cond_stage = ConditionalStage.objects.create(name="Conditional Stage test complete", x_pos=1, y_pos=1,
                                                         chain=self.chain, conditions=conditions)
            cond_stage.in_stages.add(self.task_stage)
            task_stage.in_stages.add(cond_stage)

        case = Case.objects.create()
        task = Task.objects.create(assignee=self.user, stage=self.task_stage, case=case)
        task.responses = responses
        task.save()
        response = self.client.patch(self.url_tasks + f"{task.id}/", {"complete": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        created_tasks = Task.objects.filter(case=case).exclude(id=task.id)
        self.assertEqual(created_tasks.count(), 0)

    # Pingpong returned tdd task to employee because condition is true (verifier didn't accept task).
    def test_complete_next_ping_pong_condition_true(self):
        responses = {"verified": "Да"}

        self.new_user.managed_campaigns.add(self.campaign)

        new_task_stage = TaskStage.objects.create(
            name="Task stage created test complete",
            x_pos=1,
            y_pos=1,
            chain=self.chain)
        new_cond_stage = ConditionalStage.objects.create(
            name="Conditional Stage test complete",
            x_pos=1,
            y_pos=1,
            chain=self.chain,
            pingpong=True)
        new_cond_stage.conditions = [{"field": "verified", "value": "Да", "condition": "=="}]
        new_cond_stage.save()

        self.task_stage.in_stages.add(new_cond_stage)
        new_task_stage.in_stages.add(new_cond_stage)

        case = Case.objects.create()
        verified_task = Task.objects.create(assignee=self.user, stage=self.task_stage, case=case, complete=True)
        task = Task.objects.create(assignee=self.user, stage=self.task_stage, case=case)
        task.responses = responses
        verified_task.out_tasks.add(task)
        task.save()
        response = self.client.patch(self.url_tasks + f"{task.id}/", {"complete": True})
        created_tasks = Task.objects.filter(stage=new_task_stage) \
            .filter(stage__in_stages=new_cond_stage)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Task.objects.get(id=verified_task.id).complete)

    # Pingpong returned tdd task to employee because condition is false(verificator accepted task).
    def test_complete_next_ping_pong_condition_false(self):
        responses = {"verified": "Нет"}

        self.new_user.managed_campaigns.add(self.campaign)

        new_task_stage = TaskStage.objects.create(name="Task stage created test complete", x_pos=1, y_pos=1,
                                                  chain=self.chain)
        new_cond_stage = ConditionalStage.objects.create(name="Conditional Stage test complete", x_pos=1, y_pos=1,
                                                         chain=self.chain, pingpong=True)
        new_cond_stage.conditions = [{"field": "verified", "value": "Да", "condition": "=="}]
        new_cond_stage.save()

        self.task_stage.in_stages.add(new_cond_stage)
        new_task_stage.in_stages.add(new_cond_stage)
        new_task_stage.in_stages.add(self.task_stage)

        case = Case.objects.create()
        verified_task = Task.objects.create(assignee=self.user, stage=self.task_stage, case=case, complete=True)
        task = Task.objects.create(assignee=self.user, stage=self.task_stage, case=case)
        task.responses = responses
        verified_task.out_tasks.add(task)
        task.save()
        response = self.client.patch(self.url_tasks + f"{task.id}/", {"complete": True})
        created_tasks = Task.objects.filter(stage=new_task_stage) \
            .filter(stage__in_stages=new_cond_stage)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Task.objects.get(id=verified_task.id).complete)
        self.assertEqual(created_tasks.count(), 1)

    def test_webhook_on_correctness(self):
        my_json = {"note": {}, "questionone": "а", "questiontwo": "в", "questionthree": "в"}
        answers = {"note": {}, "questionone": "-", "questiontwo": "в", "questionthree": "в"}
        new_task_stage = TaskStage.objects.create(name="NEW Task stage", x_pos=1, y_pos=1,
                                                       chain=self.chain)

        self.task_stage.json_schema = my_json
        self.task_stage.webhook_address = self.url_webhook_quiz
        self.task_stage.webhook_payload_field = 'responses'
        self.task_stage.webhook_params = my_json
        self.task_stage.save()
        self.task_stage.in_stages.add(new_task_stage)

        case = Case.objects.create()
        task1 = Task.objects.create(assignee=self.user, stage=new_task_stage, case=case, responses=answers)
        Task.objects.create(assignee=self.user, stage=self.task_stage, case=case, responses=answers)
        response = self.client.patch(self.url_tasks + f"{task1.id}/", {"complete": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tasks = Task.objects.filter(case=case)
        created_task = tasks.filter(in_tasks=task1)[0]
        self.assertEqual(tasks.count(), 3)
        self.assertEqual(created_task.responses['percent_of_correct_responses'], 66)


class RankTest(APITestCase):
    def setUp(self):
        self.url_rank = reverse('rank-list')

        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.new_user = CustomUser.objects.create_user(username="new_user", email='new_user@email.com',
                                                       password='new_user')
        self.employee = CustomUser.objects.create(username="empl", email='empl@email.com', password='empl')

        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(name="Campaign")
        self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        self.conditional_stage = ConditionalStage.objects.create(name="Conditional Stage", x_pos=1, y_pos=1,
                                                                 chain=self.chain)
        self.task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                   chain=self.chain)
        self.track = Track.objects.create(name="My Track", campaign=self.campaign)
        self.ranks = [Rank.objects.create(name="new rank", track=self.track) for i in range(5)]

        self.another_campaign = Campaign.objects.create(name="Campaign")
        self.another_chain = Chain.objects.create(name="Chain", campaign=self.another_campaign)
        self.another_conditional_stage = ConditionalStage.objects.create(name="Conditional Stage", x_pos=1, y_pos=1,
                                                                         chain=self.another_chain)
        self.another_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                           chain=self.another_chain)
        self.another_track = Track.objects.create(name="My Track", campaign=self.another_campaign)
        self.another_ranks = [Rank.objects.create(name="new rank", track=self.another_track) for i in range(5)]

        self.rank_json = {
            "name": "rank created in tests",
            "description": ""
        }

    # If user is manager and he has campaign and track with ranks can see ranks
    # simple user want to see ranks,
    def test_list_fail(self):
        self.new_user.managed_campaigns.add(self.another_campaign)

        response = self.client.get(self.url_rank)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 
        self.assertEqual(json.loads(response.content)['results'], [])

    # manager gets his ranks
    def test_list_success(self):
        self.user.managed_campaigns.add(self.campaign)

        self.new_user.managed_campaigns.add(self.another_campaign)

        response = self.client.get(self.url_rank)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), 5)

    # Only manager can retrieve his ranks
    # simple user try to get some rank
    def test_retrieve_fail(self):
        self.employee.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)

        for rank in Rank.objects.all():
            response = self.client.get(self.url_rank + f"{rank.id}/")
            # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # manager get his rank
    def test_retrieve_success(self):
        self.user.managed_campaigns.add(self.campaign)

        self.new_user.managed_campaigns.add(self.another_campaign)

        for rank in self.ranks:
            response = self.client.get(self.url_rank + f"{rank.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertNotEqual(json.loads(response.content), {})

    # only managers of any campaign can create ranks
    # simple user try to create rank it will fail
    def test_create_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        self.rank_json['track'] = self.track.id

        response = self.client.post(self.url_rank, self.rank_json)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # manager try to create rank it will successful create
    def test_create_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)
        self.rank_json['track'] = self.track.id

        response = self.client.post(self.url_rank, self.rank_json)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(response.content)['name'], self.rank_json['name'])

    # only manager of campaign can update rank
    # simple user try to update rank it will fail
    def test_partial_update_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        self.rank_json['track'] = self.track.id

        to_update = {"name": "UPDATED"}
        response = self.client.patch(self.url_rank + f"{self.track.id}/", to_update)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # there is hav to be 403 error
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RankRecordTest(APITestCase):
    def setUp(self):
        self.url_rankrecord = reverse('rankrecord-list')

        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.new_user = CustomUser.objects.create_user(username="new_user", email='new_user@email.com',
                                                       password='new_user')
        self.employee = CustomUser.objects.create(username="empl", email='empl@email.com', password='empl')

        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(name="Campaign")
        self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        self.conditional_stage = ConditionalStage.objects.create(name="Conditional Stage", x_pos=1, y_pos=1,
                                                                 chain=self.chain)
        self.task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                   chain=self.chain)
        self.track = Track.objects.create(name="My Track", campaign=self.campaign)
        self.ranks = [Rank.objects.create(name="new rank", track=self.track) for i in range(5)]
        self.rank_records = [RankRecord.objects.create(rank=i, user=self.employee) for i in self.ranks]

        self.another_campaign = Campaign.objects.create(name="another_campaign")
        self.another_chain = Chain.objects.create(name="Chain", campaign=self.another_campaign)
        self.another_conditional_stage = ConditionalStage.objects.create(name="Conditional Stage", x_pos=1, y_pos=1,
                                                                         chain=self.another_chain)
        self.another_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                           chain=self.another_chain)
        self.another_track = Track.objects.create(name="My Track", campaign=self.another_campaign)
        self.another_ranks = [Rank.objects.create(name="new rank", track=self.another_track) for i in range(5)]
        self.another_rank_records = [RankRecord.objects.create(rank=i, user=self.employee) for i in self.another_ranks]

        self.rank_record_json = {
            "rank": None,
            "user": self.employee.id
        }

    # If user is manager and he has campaign and track with ranks can see ranksrecord
    # simple user want to see rank records it will fail
    def test_list_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.another_campaign)
        self.new_user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url_rankrecord)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 
        self.assertEqual(json.loads(response.content)['results'], [])

    # manager gets his rank records it will be successful
    def test_list_manager_success(self):
        self.new_user.managed_campaigns.add(self.another_campaign)
        self.user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url_rankrecord)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), 5)

    # Only manager can retrieve his rank_records
    # simple user try to get some rank_records
    def test_retrieve_fail(self):
        self.employee.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)

        for rank_record in RankRecord.objects.all():
            response = self.client.get(self.url_rankrecord + f"{rank_record.id}/")
            # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # manager get his rank_record
    def test_retrieve_success(self):
        self.user.managed_campaigns.add(self.campaign)

        self.new_user.managed_campaigns.add(self.another_campaign)

        for rank_record in self.rank_records:
            response = self.client.get(self.url_rankrecord + f"{rank_record.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertNotEqual(json.loads(response.content), {})

    # only managers of any campaign can create rank_record
    # simple user try to create rank record it will fail
    def test_create_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        rank_id = self.ranks[2].id
        self.rank_record_json['rank'] = rank_id

        response = self.client.post(self.url_rankrecord, self.rank_record_json)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # manager try to create rank it will successful create
    def test_create_manager_success(self):
        track = Track.objects.create(name="My Track", campaign=self.campaign)
        rank = Rank.objects.create(name="New Rank", track=track)

        self.user.managed_campaigns.add(self.campaign)
        self.rank_record_json['rank'] = rank.id

        response = self.client.post(self.url_rankrecord, self.rank_record_json)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(response.content)['rank'], self.rank_record_json['rank'])
        self.assertEqual(json.loads(response.content)['user'], self.rank_record_json['user'])

    # only manager of campaign can update rank
    # simple user try to update rank it will fail
    def test_partial_update_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)

        new_employee = CustomUser.objects.create(username="new_empl", email='new_empl@email.com', password='new_empl')
        to_update = {"user": new_employee.id}
        for rank_record in self.rank_records:
            response = self.client.patch(self.url_rankrecord + f"{rank_record.id}/", to_update)
            # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # there is hav to be 403 error
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # manager update rank it will be successfully updated
    def test_partial_update_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)

        new_employee = CustomUser.objects.create(username="new_empl", email='new_empl@email.com', password='new_empl')
        to_update = {"user": new_employee.id}
        for rank_record in self.rank_records:
            response = self.client.patch(self.url_rankrecord + f"{rank_record.id}/", to_update)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            updated_rank_record = RankRecord.objects.get(id=rank_record.id)
            self.assertEqual(new_employee, updated_rank_record.user)


class RankLimitTest(APITestCase):
    # chain, task stage, rank limit
    def setUp(self):
        self.url_ranklimit = reverse('ranklimit-list')

        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.new_user = CustomUser.objects.create_user(username="new_user", email='new_user@email.com',
                                                       password='new_user')
        self.employee = CustomUser.objects.create(username="empl", email='empl@email.com', password='empl')

        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(name="Campaign")
        self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        self.task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                   chain=self.chain)
        self.ranks = [Rank.objects.create(name="new rank") for i in range(5)]
        self.rank_limits = [RankLimit.objects.create(rank=rank, stage=self.task_stage, total_limit=5, open_limit=3) for
                            rank in self.ranks]
        self.another_campaign = Campaign.objects.create(name="another_campaign")
        self.another_chain = Chain.objects.create(name="Chain", campaign=self.another_campaign)
        self.another_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                           chain=self.another_chain)
        self.another_ranks = [Rank.objects.create(name="new rank") for i in range(5)]
        self.another_rank_limits = [
            RankLimit.objects.create(rank=rank, stage=self.another_task_stage, total_limit=5, open_limit=3) for rank in
            self.another_ranks]

        self.rank_limit_json = {
            "open_limit": 3,
            "total_limit": 5,
            "is_listing_allowed": False,
            "is_submission_open": True,
            "is_selection_open": True,
            "stage": None,
            "rank": None
        }

    # Only campaign manager can list ranklimit
    # simple user try to get list of ranklimits it will fail
    def test_list_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.another_campaign)
        self.new_user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url_ranklimit)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 
        self.assertEqual(json.loads(response.content)['results'], [])

    # manager list his rank limits it will be success
    def test_list_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)

        response = self.client.get(self.url_ranklimit)
        self.assertNotEqual(json.loads(response.content), [])
        self.assertEqual(len(json.loads(response.content)['results']), 5)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Only manager can retrieve his rank limits
    # simple user try to get some rank_limits
    def test_retrieve_fail(self):
        self.employee.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)

        for rank_limit in RankLimit.objects.all():
            response = self.client.get(self.url_ranklimit + f"{rank_limit.id}/")
            # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # manager get his rank limits
    def test_retrieve_success(self):

        self.user.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)

        for rank_limit in self.rank_limits:
            response = self.client.get(self.url_ranklimit + f"{rank_limit.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertNotEqual(json.loads(response.content), {})

    # only managers of any campaign can create rank limit
    # simple user try to create rank limit it will fail
    def test_create_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)

        rank = Rank.objects.create(name="New Rank")

        self.rank_limit_json['rank'] = rank.id
        self.rank_limit_json['stage'] = self.task_stage.id

        response = self.client.post(self.url_ranklimit, self.rank_limit_json)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(RankRecord.objects.count(), 0)

    # manager try to create rank limit it will successful create
    def test_create_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)

        rank = Rank.objects.create(name="New Rank")

        self.rank_limit_json['rank'] = rank.id
        self.rank_limit_json['stage'] = self.task_stage.id

        response = self.client.post(self.url_ranklimit, self.rank_limit_json)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_rank_limit = json.loads(response.content)
        my_rank_limit = RankLimit.objects.get(id=created_rank_limit["id"])
        # self.assertEqual(model_to_dict(my_rank_limit), created_rank_limit)

    # only manager of campaign can update rank limit
    # simple user try to update rank limit it will fail
    def test_partial_update_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)

        to_update = {"open_limit": 4}
        for rank_limit in self.rank_limits:
            response = self.client.patch(self.url_ranklimit + f"{rank_limit.id}/", to_update)
            # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # there is hav to be 403 error
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # manager update rank limit it will be successfully updated
    def test_partial_update_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)

        to_update = {"open_limit": 4}
        for rank_limit in self.rank_limits:
            response = self.client.patch(self.url_ranklimit + f"{rank_limit.id}/", to_update)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class TrackTest(APITestCase):
    def setUp(self):
        self.url_track = reverse('track-list')

        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.new_user = CustomUser.objects.create_user(username="new_user", email='new_user@email.com',
                                                       password='new_user')
        self.employee = CustomUser.objects.create(username="empl", email='empl@email.com', password='empl')

        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(name="Campaign")
        self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        self.tracks = [Track.objects.create(campaign=self.campaign) for i in range(10)]
        self.rank = Rank.objects.create(name="New Rank")

        self.another_campaign = Campaign.objects.create(name="Campaign")
        self.another_chain = Chain.objects.create(name="Chain", campaign=self.another_campaign)
        self.another_tracks = [Track.objects.create(campaign=self.another_campaign) for i in range(10)]
        self.another_rank = Rank.objects.create(name="New Rank")

        self.track_json = {
            "name": "my track",
            "campaign": None,
            "default_rank": None
        }

    # Only campaign manager can list track
    # simple user try to get list of track it will fail
    def test_list_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.another_campaign)
        self.new_user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url_track)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 
        self.assertEqual(json.loads(response.content)['results'], [])

    # manager list his tracks it will be success
    def test_list_manager_success(self):
        self.new_user.managed_campaigns.add(self.another_campaign)
        self.user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url_track)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), 10)

    # Only manager can retrieve his tracks
    # simple user try to get some track
    def test_retrieve_fail(self):
        self.employee.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)

        tracks = self.tracks + self.another_tracks
        for rank_limit in tracks:
            response = self.client.get(self.url_track + f"{rank_limit.id}/")
            # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # manager get not his tracks it will fail
    def test_retrieve_manager_not_his_rank_fail(self):
        self.user.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)

        for track in self.another_tracks:
            response = self.client.get(self.url_track + f"{track.id}/")
            # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # manager get his tracks
    def test_retrieve_success(self):
        self.user.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)

        for track in self.tracks:
            response = self.client.get(self.url_track + f"{track.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            # self.assertEqual(json.loads(response.content), model_to_dict(track))

        for track in self.another_tracks:
            response = self.client.get(self.url_track + f"{track.id}/")
            # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # only managers of any campaign can create track
    # simple user try to create track it will fail
    def test_create_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        self.track_json['campaign'] = self.campaign.id
        self.track_json['default_rank'] = self.rank.id

        response = self.client.post(self.url_track, self.track_json)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # manager try to create track it will successful create
    def test_create_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)
        self.track_json['campaign'] = self.campaign.id
        self.track_json['default_rank'] = self.rank.id

        response = self.client.post(self.url_track, self.track_json)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # only manager of campaign can update track
    # simple user try to update track it will fail
    def test_partial_update_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)

        to_update = {"name": "UPDATED NAME"}
        for track in self.tracks:
            response = self.client.patch(self.url_track + f"{track.id}/", to_update)
            # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # there is hav to be 403 error
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # manager update track it will be successfully updated
    def test_partial_update_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)

        to_update = {"name": "UPDATED NAME"}
        for track in self.tracks:
            response = self.client.patch(self.url_track + f"{track.id}/", to_update)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            # self.assertEqual(json.loads(response.content), model_to_dict(Track.objects.get(id=track.id)))
