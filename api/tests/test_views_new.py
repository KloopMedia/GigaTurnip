import django, json, random
from django.forms.models import model_to_dict

django.setup()

from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from django.contrib.auth.models import Group
from api.models import CustomUser, Campaign, Chain, ConditionalStage, TaskStage, Rank, RankLimit, Task, RankRecord, \
    Track
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

        new_name = {"name": "new_name"}
        response = self.client.patch(self.url + str(campaign_id) + "/", new_name)
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


class ChainTest(APITestCase):
    # todo: ask about can_create condition
    # todo: ask about scope_queryset
    def setUp(self):
        self.url_campaign = reverse("campaign-list")
        self.url_chain = reverse("chain-list")
        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.client.force_authenticate(user=self.user)
        self.campaign_json = {"name": "campaign", "description": "description"}
        self.chain = {"name": "chain", "description": "description", "campaign": None}
        self.campaign_creator_group = Group.objects.create(name='campaign_creator')

    # because simple user can't make list of chains
    def test_list_user_fail(self):
        self.assertEqual(Campaign.objects.count(), 0)
        self.assertEqual(Chain.objects.count(), 0)
        new_user = CustomUser.objects.create_user(username='new_user', email='u@gmail.com', password='1234')
        campaign = Campaign.objects.create(name='campaign')
        chain = Chain.objects.create(name='chain', campaign=campaign)
        new_user.managed_campaigns.add(campaign)
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(Chain.objects.count(), 1)
        response = self.client.get(self.url_chain)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) #todo: uncomment it after fixing permissions
        self.assertEqual(json.loads(response.content), [])

    # because manager
    def test_list_success(self):
        self.campaign_creator_group.user_set.add(self.user)
        campaign = Campaign.objects.create(name='campaign')
        chain = Chain.objects.create(name='chain', campaign=campaign)
        self.user.managed_campaigns.add(campaign)
        response = self.client.get(self.url_chain)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), [model_to_dict(chain)])

    # simple user can't create new chain
    def test_create_simple_user_create_fail(self):
        campaign = Campaign.objects.create(name="campaign")
        chain = Chain.objects.create(name="NewChain", campaign=campaign)
        new_user = CustomUser.objects.create_user(username="new_test", email='new_test@email.com', password='new_test')
        new_user.managed_campaigns.add(campaign)

        self.chain['campaign'] = campaign.id
        response = self.client.post(self.url_chain, self.chain)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # test create if user isn't manager of campaign
    def test_create_not_my_campaign_fail(self):
        new_user = CustomUser.objects.create_user(username='new user')
        new_campaign = Campaign.objects.create(name='new campaign')
        self.campaign_creator_group.user_set.add(new_user)
        new_user.managed_campaigns.add(new_campaign)

        self.campaign_creator_group.user_set.add(self.user)
        self.assertEqual(CustomUser.objects.count(), 2)
        my_campaign = Campaign.objects.create(name='my campaign')
        self.user.managed_campaigns.add(my_campaign)

        chain_refers_not_my_campaign = self.chain
        chain_refers_not_my_campaign['campaign'] = new_campaign.id
        response_create_chain_not_my_campaign = self.client.post(
            self.url_chain,
            chain_refers_not_my_campaign
        )
        self.assertEqual(response_create_chain_not_my_campaign.status_code, status.HTTP_400_BAD_REQUEST)

    # if user is manager and chain refers on users campaign
    def test_create_chain_refers_on_my_campaign_success(self):
        self.campaign_creator_group.user_set.add(self.user)
        my_campaign = Campaign.objects.create(name='My campaign')
        self.assertEqual(Campaign.objects.count(), 1)
        self.user.managed_campaigns.add(my_campaign)

        chain = self.chain
        chain['campaign'] = my_campaign.id
        response_create_chain = self.client.post(self.url_chain, chain)
        self.assertEqual(response_create_chain.status_code, status.HTTP_201_CREATED)
        my_chain = Chain.objects.get(id=response_create_chain.data.get('id'))
        self.assertEqual(json.loads(response_create_chain.content), model_to_dict(my_chain))
        self.assertEqual(Chain.objects.count(), 1)
        self.assertIn(self.user, my_chain.campaign.managers.all())
        self.assertEqual(1, len(my_chain.campaign.managers.all()))

    # manager can retrieve chains which attached to his campaigns
    # manager try to retrieve not his chain
    def test_retrieve_my_campaign_not_my_chain_fail(self):
        new_user = CustomUser.objects.create_user(username='new user')
        new_campaign = Campaign.objects.create(name='new campaign')
        new_chain = Chain.objects.create(name='new chain', campaign=new_campaign)
        self.campaign_creator_group.user_set.add(new_user)
        new_user.managed_campaigns.add(new_campaign)

        self.campaign_creator_group.user_set.add(self.user)
        my_campaign = Campaign.objects.create(name="My Campaign")
        self.assertEqual(Campaign.objects.count(), 2)
        my_chain = Chain.objects.create(name='my chain', campaign=my_campaign)
        self.assertEqual(Chain.objects.count(), 2)
        self.user.managed_campaigns.add(my_campaign)

        response_not_my_chain = self.client.get(self.url_chain + f"{new_chain.id}/")
        self.assertEqual(response_not_my_chain.status_code,
                         status.HTTP_404_NOT_FOUND)  # todo: is there have to be 403 error
        self.assertNotIn(self.user, new_chain.campaign.managers.all())

    # manager retrieve his chain
    def test_retrieve_my_campaign_my_chain_success(self):
        new_user = CustomUser.objects.create_user(username='new user')
        new_campaign = Campaign.objects.create(name='new campaign')
        new_chain = Chain.objects.create(name='new chain', campaign=new_campaign)
        self.campaign_creator_group.user_set.add(new_user)
        new_user.managed_campaigns.add(new_campaign)

        self.campaign_creator_group.user_set.add(self.user)
        my_campaign = Campaign.objects.create(name="My Campaign")
        self.assertEqual(Campaign.objects.count(), 2)
        self.user.managed_campaigns.add(my_campaign)
        my_chain = Chain.objects.create(name='my chain', campaign=my_campaign)
        self.assertEqual(Chain.objects.count(), 2)

        response_not_my_chain = self.client.get(self.url_chain + f"{my_chain.id}/")
        self.assertEqual(response_not_my_chain.status_code, status.HTTP_200_OK)

    # manager can update/partial update only his chain
    # try to update other chain
    def test_partial_update_not_my_chain_fail(self):
        new_user = CustomUser.objects.create_user(username='new user')
        new_campaign = Campaign.objects.create(name='new campaign')
        new_chain = Chain.objects.create(name='new chain', campaign=new_campaign)
        self.campaign_creator_group.user_set.add(new_user)
        new_user.managed_campaigns.add(new_campaign)

        self.campaign_creator_group.user_set.add(self.user)
        self.assertEqual(CustomUser.objects.count(), 2)
        my_campaign = Campaign.objects.create(name="My campaign")
        self.user.managed_campaigns.add(my_campaign)
        my_chain = Chain.objects.create(name='my chain', campaign=my_campaign)
        self.assertEqual(Chain.objects.count(), 2)

        response_update_not_my_chain = self.client.patch(
            self.url_chain + f"{new_chain.id}/",
            {"name": "try to change chain name"}
        )
        self.assertEqual(response_update_not_my_chain.status_code,
                         status.HTTP_404_NOT_FOUND)  # todo: ask about 403 status code

    # manager try to update/partial update his chain
    def test_partial_update_success(self):
        new_user = CustomUser.objects.create_user(username='new user')
        new_campaign = Campaign.objects.create(name='new campaign')
        new_chain = Chain.objects.create(name='new chain', campaign=new_campaign)
        self.campaign_creator_group.user_set.add(new_user)
        new_user.managed_campaigns.add(new_campaign)

        self.campaign_creator_group.user_set.add(self.user)
        self.assertEqual(CustomUser.objects.count(), 2)
        my_campaign = Campaign.objects.create(name="My campaign")
        self.user.managed_campaigns.add(my_campaign)
        my_chain = Chain.objects.create(name='my chain', campaign=my_campaign)
        self.assertEqual(Chain.objects.count(), 2)

        chain = self.chain
        chain['name'] = "try to change chain name"
        chain['campaign'] = my_campaign.id
        response_update_my_chain = self.client.patch(
            self.url_chain + f"{my_chain.id}/",
            chain
        )
        self.assertEqual(response_update_my_chain.status_code, status.HTTP_200_OK)
        self.assertEqual(Chain.objects.count(), 2)
        my_chain = Chain.objects.get(id=my_chain.id)
        self.assertEqual(json.loads(response_update_my_chain.content), model_to_dict(my_chain))


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
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(ConditionalStage.objects.count(), 1)
        self.assertEqual(Chain.objects.count(), 1)
        response = self.client.get(self.url_conditional_stage)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # todo: there is must be 403 status_code
        self.assertEqual(json.loads(response.content), [])

    # manager try list his conditional stage
    def test_list_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(ConditionalStage.objects.count(), 1)
        self.assertEqual(Chain.objects.count(), 1)

        response = self.client.get(self.url_conditional_stage)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        my_conditional_stages = ConditionalStage.objects.all().filter(
            chain__campaign__campaign_managements__user=self.user)
        self.assertEqual(len(json.loads(response.content)), len(my_conditional_stages))

    # Manager can create chain refers on his campaigns
    # user try create conditional stage refers on other chain
    def test_create_campaign_not_my_chain_fail(self):
        new_campaign = Campaign.objects.create(name='new campaign')
        new_chain = Chain.objects.create(name='new chain', campaign=new_campaign)
        self.campaign_creator_group.user_set.add(self.new_user)
        self.new_user.managed_campaigns.add(new_campaign)

        self.user.managed_campaigns.add(self.campaign)

        self.assertEqual(ConditionalStage.objects.count(), 1)

        cond_stage = self.conditional_stage_json
        cond_stage['chain'] = new_chain.id
        response = self.client.post(self.url_conditional_stage, cond_stage)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ConditionalStage.objects.count(), 1)
        self.assertEqual(Campaign.objects.count(), 2)
        self.assertEqual(Chain.objects.count(), 2)
        self.assertNotIn(self.user, new_chain.campaign.managers.all())

    # create cond_stage refers to my chain
    def test_create_my_chain_success(self):
        self.user.managed_campaigns.add(self.campaign)
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(Chain.objects.count(), 1)
        self.assertEqual(ConditionalStage.objects.count(), 1)

        self.conditional_stage_json['chain'] = self.chain.id
        response = self.client.post(self.url_conditional_stage, self.conditional_stage_json)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ConditionalStage.objects.count(), 2)
        my_conditional_stage = ConditionalStage.objects.get(id=response.data.get('id'))
        self.assertIn(self.user, my_conditional_stage.chain.campaign.managers.all())
        self.assertEqual(json.loads(response.content)['id'], model_to_dict(my_conditional_stage)['id'])

    # Only managers of campaign can retrieve their conditional stages
    # simple user try to retrieve conditional stage
    def test_retrieve_simple_user_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(Chain.objects.count(), 1)
        self.assertEqual(ConditionalStage.objects.count(), 1)
        self.assertEqual(self.user.managed_campaigns.count(), 0)
        response = self.client.get(self.url_conditional_stage + f"{self.conditional_stage.id}/")
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # todo: is there have to be 403 error
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # manager try to retrieve other conditional stage
    def test_retrieve_manager_not_his_cond_stage_fail(self):
        new_campaign = Campaign.objects.create(name="other campaign")
        new_chain = Chain.objects.create(name="other chain", campaign=new_campaign)
        new_conditional_stage = ConditionalStage.objects.create(name="Other Conditional Stage", x_pos=1, y_pos=1,
                                                                chain=new_chain)
        self.new_user.managed_campaigns.add(new_campaign)
        self.user.managed_campaigns.add(self.campaign)

        self.assertEqual(Campaign.objects.count(), 2)
        self.assertEqual(Chain.objects.count(), 2)
        self.assertEqual(ConditionalStage.objects.count(), 2)
        self.assertNotIn(self.user, new_conditional_stage.chain.campaign.managers.all())

        response = self.client.get(self.url_conditional_stage + f"{new_conditional_stage.id}/")
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)# todo: is there have to be 403 error
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # manager try to retrieve other conditional stage
    def test_retrieve_manager_cond_stage_success(self):
        new_campaign = Campaign.objects.create(name="other campaign")
        new_chain = Chain.objects.create(name="other chain", campaign=new_campaign)
        new_conditional_stage = ConditionalStage.objects.create(name="Other Conditional Stage", x_pos=1, y_pos=1,
                                                                chain=new_chain)
        self.new_user.managed_campaigns.add(new_campaign)
        self.user.managed_campaigns.add(self.campaign)

        self.assertEqual(Campaign.objects.count(), 2)
        self.assertEqual(Chain.objects.count(), 2)
        self.assertEqual(ConditionalStage.objects.count(), 2)
        self.assertNotIn(self.user, new_conditional_stage.chain.campaign.managers.all())

        response = self.client.get(self.url_conditional_stage + f"{self.conditional_stage.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_content = json.loads(response.content)

        self.assertEqual(self.conditional_stage, ConditionalStage.objects.get(id=response_content.get('id')))

    # Only managers can update conditional stage
    # simple user try to partial_update cond stage
    def test_partial_update_simple_user_fail(self):
        new_campaign = Campaign.objects.create(name="other campaign")
        new_chain = Chain.objects.create(name="other chain", campaign=new_campaign)
        new_conditional_stage = ConditionalStage.objects.create(name="Other Conditional Stage", x_pos=1, y_pos=1,
                                                                chain=new_chain)
        self.new_user.managed_campaigns.add(new_campaign)
        self.new_user.managed_campaigns.add(self.campaign)

        self.assertEqual(Campaign.objects.count(), 2)
        self.assertEqual(Chain.objects.count(), 2)
        self.assertEqual(ConditionalStage.objects.count(), 2)
        self.assertNotIn(self.user, new_campaign.managers.all())
        self.assertNotIn(self.user, self.campaign.managers.all())

        change_name = {"name": self.conditional_stage_json_modified['name']}
        response = self.client.patch(self.url_conditional_stage + f"{self.conditional_stage.id}/", change_name)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # todo: is there have to be 403 status code
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.conditional_stage.name, ConditionalStage.objects.get(id=self.conditional_stage.id).name)

    # manager try to partial update not his cond stage
    def test_partial_update_manager_not_his_cond_stage_fail(self):
        new_campaign = Campaign.objects.create(name="other campaign")
        new_chain = Chain.objects.create(name="other chain", campaign=new_campaign)
        new_conditional_stage = ConditionalStage.objects.create(name="Other Conditional Stage", x_pos=1, y_pos=1,
                                                                chain=new_chain)
        self.new_user.managed_campaigns.add(new_campaign)
        self.user.managed_campaigns.add(self.campaign)

        self.assertEqual(Campaign.objects.count(), 2)
        self.assertEqual(Chain.objects.count(), 2)
        self.assertEqual(ConditionalStage.objects.count(), 2)
        self.assertNotIn(self.user, new_campaign.managers.all())
        self.assertIn(self.user, self.campaign.managers.all())

        change_name = {"name": self.conditional_stage_json_modified['name']}
        response = self.client.patch(self.url_conditional_stage + f"{new_conditional_stage.id}/", change_name)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # todo: is there have to be 403 status code
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(new_conditional_stage.name, ConditionalStage.objects.get(id=new_conditional_stage.id).name)

    # manager try update his conditional stage
    def test_partial_update_manager_success(self):
        new_campaign = Campaign.objects.create(name="other campaign")
        new_chain = Chain.objects.create(name="other chain", campaign=new_campaign)
        new_conditional_stage = ConditionalStage.objects.create(name="Other Conditional Stage", x_pos=1, y_pos=1,
                                                                chain=new_chain)
        self.new_user.managed_campaigns.add(new_campaign)
        self.user.managed_campaigns.add(self.campaign)

        self.assertEqual(Campaign.objects.count(), 2)
        self.assertEqual(Chain.objects.count(), 2)
        self.assertEqual(ConditionalStage.objects.count(), 2)
        self.assertNotIn(self.user, new_campaign.managers.all())
        self.assertIn(self.user, self.campaign.managers.all())

        change_name = {"name": self.conditional_stage_json_modified['name']}
        response = self.client.patch(self.url_conditional_stage + f"{self.campaign.id}/", change_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content)['name'], ConditionalStage.objects.get(id=self.campaign.id).name)


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
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(Chain.objects.count(), 1)
        self.assertEqual(ConditionalStage.objects.count(), 1)
        campaign_managers = self.campaign.managers.all()
        self.assertIn(self.new_user, campaign_managers)
        self.assertNotIn(self.user, campaign_managers)

        response = self.client.get(self.url_task_stage)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # todo: ask about error. there is habe to be 403 status code
        self.assertEqual(json.loads(response.content), [])

    # Manager try to list campaigns
    def test_list_manager_success(self):
        new_campaign = Campaign.objects.create(name="New Campaign")
        new_chain = Chain.objects.create(name="New Chain", campaign=new_campaign)
        new_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                  chain=new_chain)
        self.new_user.managed_campaigns.add(new_campaign)
        self.user.managed_campaigns.add(self.campaign)

        self.assertEqual(Campaign.objects.count(), 2)
        self.assertEqual(Chain.objects.count(), 2)
        self.assertEqual(TaskStage.objects.count(), 2)

        response = self.client.get(self.url_task_stage)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        my_task_stages = TaskStage.objects.all().filter(chain__campaign__managers=self.user)
        self.assertEqual(len(json.loads(response.content)), len(my_task_stages))
        self.assertNotEqual(json.loads(response.content), [])

    # Only managers can create task stage
    # simple user try create task stage
    def test_create_fail(self):
        new_campaign = Campaign.objects.create(name="New Campaign")
        new_chain = Chain.objects.create(name="New Chain", campaign=new_campaign)
        new_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                  chain=new_chain)
        self.new_user.managed_campaigns.add(new_campaign)
        self.new_user.managed_campaigns.add(self.campaign)

        self.assertEqual(Campaign.objects.count(), 2)
        self.assertEqual(Chain.objects.count(), 2)
        self.assertEqual(TaskStage.objects.count(), 2)
        self.assertNotIn(self.user, new_campaign.managers.all())
        self.assertNotIn(self.user, self.campaign.managers.all())

        task_stage_json = self.task_stage_json
        task_stage_json['chain'] = new_chain.id
        response = self.client.post(self.url_task_stage, task_stage_json)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  # todo: is there have to be 403 status code

    # manager try create task stage
    def test_create_success(self):
        new_campaign = Campaign.objects.create(name="New Campaign")
        new_chain = Chain.objects.create(name="New Chain", campaign=new_campaign)
        new_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                  chain=new_chain)
        self.new_user.managed_campaigns.add(new_campaign)
        self.user.managed_campaigns.add(self.campaign)

        self.assertEqual(Campaign.objects.count(), 2)
        self.assertEqual(Chain.objects.count(), 2)
        self.assertEqual(TaskStage.objects.count(), 2)
        self.assertNotIn(self.user, new_campaign.managers.all())
        self.assertIn(self.user, self.campaign.managers.all())

        task_stage_json = self.task_stage_json
        task_stage_json['chain'] = self.chain.id
        response = self.client.post(self.url_task_stage, task_stage_json)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_task_stage = TaskStage.objects.get(id=response.data.get('id'))
        self.assertEqual(json.loads(response.content)['id'], model_to_dict(created_task_stage)['id'])
        self.assertEqual(TaskStage.objects.count(), 3)

    # Only managers and stage user creatable users can retrieve task stage
    # simple user try to retrieve task stage
    def test_retrieve_simple_user_fail(self):
        new_campaign = Campaign.objects.create(name="New Campaign")
        new_chain = Chain.objects.create(name="New Chain", campaign=new_campaign)
        new_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                  chain=new_chain)
        self.new_user.managed_campaigns.add(new_campaign)
        self.new_user.managed_campaigns.add(self.campaign)
        self.assertNotIn(self.user, new_campaign.managers.all())
        self.assertNotIn(self.user, self.campaign.managers.all())

        for i in [new_task_stage, self.task_stage]:
            response = self.client.get(self.url_task_stage + f"{i.id}/")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # manager try to retrieve task stage
    def test_retrieve_manager_success(self):
        new_campaign = Campaign.objects.create(name="New Campaign")
        new_chain = Chain.objects.create(name="New Chain", campaign=new_campaign)
        new_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                  chain=new_chain)
        self.new_user.managed_campaigns.add(new_campaign)
        self.user.managed_campaigns.add(self.campaign)
        self.user.managed_campaigns.add(new_campaign)
        self.assertIn(self.user, new_campaign.managers.all())
        self.assertIn(self.user, self.campaign.managers.all())

        for i in [new_task_stage, self.task_stage]:
            response = self.client.get(self.url_task_stage + f"{i.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    # user with creatable task  stage retrieve task stage
    def test_retrieve_stage_user_creatable_success(self):
        new_task_stage = TaskStage.objects.create(name="new Task stage is creatable True", x_pos=1, y_pos=1,
                                                  chain=self.chain, is_creatable=True)
        new_rank = Rank.objects.create(name="rank")
        rank_record = RankRecord.objects.create(user=self.user, rank=new_rank)
        rank_limit = RankLimit.objects.create(rank=new_rank, stage=new_task_stage,
                                              open_limit=2, total_limit=3,
                                              is_creation_open=True)
        task = Task.objects.create(assignee=self.user, stage=new_task_stage,
                                   complete=False)

        response = self.client.get(self.url_task_stage + f"{new_task_stage.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content)['id'], new_task_stage.id)

    # only managers can update or partial update campaigns
    # user try to partial_update task stage
    def test_partial_update_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        self.assertNotIn(self.user, self.campaign.managers.all())
        response = self.client.patch(self.url_task_stage + f"{self.task_stage.id}/", {"name": "Changed taskstage name"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.task_stage.name, TaskStage.objects.get(id=self.task_stage.id).name)
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(Chain.objects.count(), 1)
        self.assertEqual(TaskStage.objects.count(), 1)

    # manager partial_update task stage
    def test_partial_update_success(self):
        self.user.managed_campaigns.add(self.campaign)
        self.assertIn(self.user, self.campaign.managers.all())

        changed_name = {"name": "Changed taskstage name"}
        response = self.client.patch(self.url_task_stage + f"{self.task_stage.id}/", changed_name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(changed_name['name'], TaskStage.objects.get(id=self.task_stage.id).name)


class TaskTest(APITestCase):
    # todo: test release_assignment, request_assignment, list_displayed_previous
    def setUp(self):
        self.url_campaign = reverse("campaign-list")
        self.url_chain = reverse("chain-list")
        self.url_conditional_stage = reverse('conditionalstage-list')
        self.url_task_stage = reverse('taskstage-list')
        self.url_tasks = reverse('task-list')

        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.new_user = CustomUser.objects.create_user(username="new_user", email='new_user@email.com',
                                                       password='new_user')
        self.employer = CustomUser.objects.create(username="empl", email='empl@email.com', password='empl')

        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(name="Campaign")
        self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        self.conditional_stage = ConditionalStage.objects.create(name="Conditional Stage", x_pos=1, y_pos=1,
                                                                 chain=self.chain)
        self.task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                   chain=self.chain)

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

    # Only managers can list tasks
    def test_list_not_manager_fail(self):
        task = [Task.objects.create(assignee=self.new_user, stage=self.task_stage,
                                    complete=False) for x in range(5)]
        self.assertEqual(Task.objects.count(), 5)
        response = self.client.get(self.url_tasks)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) #todo: there is have to be 403 error
        self.assertEqual(json.loads(response.content), [])

    def test_list_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)
        task = [Task.objects.create(assignee=self.new_user, stage=self.task_stage,
                                    complete=False) for x in range(5)]
        another_manager = CustomUser.objects.create(username="another_manager", email='an@email.com',
                                                    password='another')
        another_campaign = Campaign.objects.create(name="Campaign")
        another_chain = Chain.objects.create(name="Chain", campaign=another_campaign)
        another_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                      chain=another_chain)
        another_task = [Task.objects.create(assignee=self.new_user, stage=another_task_stage,
                                            complete=False) for x in range(5)]
        self.assertEqual(Task.objects.count(), 10)
        response = self.client.get(self.url_tasks)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)), 5)

    """ User can do retrieve task if :
     user is manager, task is assigned to you, filter_for_user_selectable_tasks"""

    # not manager, task isn't assigned, no filter_for_user_selectable_tasks
    def test_retrieve_nohing_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        task = Task.objects.create(assignee=self.employer, stage=self.task_stage,
                                   complete=False)
        self.assertNotIn(self.user, self.campaign.managers.all())
        self.assertNotEqual(self.user, task.assignee)
        queryset = Task.objects.filter(id=task.id)
        selectable_tasks = queryset \
            .filter(complete=False) \
            .filter(assignee__isnull=True) \
            .filter(stage__ranks__users=self.user.id) \
            .filter(stage__ranklimits__is_selection_open=True) \
            .filter(stage__ranklimits__is_listing_allowed=True) \
            .distinct()
        self.assertFalse(bool(selectable_tasks))

        response = self.client.get(self.url_tasks + f"{task.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # User is manager, task isn't assigned, no user_selectable_tasks
    def test_retrieve_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)
        task = Task.objects.create(assignee=self.employer, stage=self.task_stage,
                                   complete=False)
        self.assertIn(self.user, self.campaign.managers.all())
        self.assertNotEqual(self.user, task.assignee)
        queryset = Task.objects.filter(id=task.id)
        selectable_tasks = queryset \
            .filter(complete=False) \
            .filter(assignee__isnull=True) \
            .filter(stage__ranks__users=self.user.id) \
            .filter(stage__ranklimits__is_selection_open=True) \
            .filter(stage__ranklimits__is_listing_allowed=True) \
            .distinct()
        self.assertFalse(bool(selectable_tasks))

        response = self.client.get(self.url_tasks + f"{task.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # task is not
    def test_retrieve_assignee_success(self):
        self.new_user.managed_campaigns.add(self.campaign)
        task = Task.objects.create(assignee=self.user, stage=self.task_stage,
                                   complete=False)
        self.assertNotIn(self.user, self.campaign.managers.all())
        self.assertEqual(self.user, task.assignee)
        queryset = Task.objects.filter(id=task.id)
        selectable_tasks = queryset \
            .filter(complete=False) \
            .filter(assignee__isnull=True) \
            .filter(stage__ranks__users=self.user.id) \
            .filter(stage__ranklimits__is_selection_open=True) \
            .filter(stage__ranklimits__is_listing_allowed=True) \
            .distinct()
        self.assertFalse(bool(selectable_tasks))

        response = self.client.get(self.url_tasks + f"{task.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content)['id'], task.id)

    def test_retrieve_can_user_request_assignment_success(self):
        new_rank = Rank.objects.create(name="rank")
        rank_record = RankRecord.objects.create(user=self.user, rank=new_rank)
        rank_limit = RankLimit.objects.create(rank=new_rank, stage=self.task_stage,
                                              open_limit=2, total_limit=3,
                                              is_selection_open=True, is_listing_allowed=True)

        self.new_user.managed_campaigns.add(self.campaign)
        task = Task.objects.create(stage=self.task_stage,
                                   complete=False)
        self.assertNotIn(self.user, self.campaign.managers.all())
        self.assertNotEqual(self.user, task.assignee)

        queryset = Task.objects.filter(id=task.id)
        selectable_tasks = queryset \
            .filter(complete=False) \
            .filter(assignee__isnull=True) \
            .filter(stage__ranks__users=self.user.id) \
            .filter(stage__ranklimits__is_selection_open=True) \
            .filter(stage__ranklimits__is_listing_allowed=True) \
            .distinct()
        self.assertTrue(bool(selectable_tasks))

        response = self.client.get(self.url_tasks + f"{task.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content)['id'], task.id)

    # if queryset of tasks satisfies filter_for_user_selectable tasks
    def test_user_selectable_not_manager_fail(self):
        new_rank = Rank.objects.create(name="rank")
        rank_record = RankRecord.objects.create(user=self.new_user, rank=new_rank)
        rank_limit = RankLimit.objects.create(rank=new_rank, stage=self.task_stage,
                                              open_limit=2, total_limit=3,
                                              is_selection_open=True, is_listing_allowed=True)

        self.assertNotIn(self.user, self.campaign.managers.all())
        task = [Task.objects.create(stage=self.task_stage,
                                    complete=False) for x in range(5)]
        self.assertEqual(Task.objects.count(), 5)
        response = self.client.get(self.url_tasks + "user_selectable/")
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) #todo: there is have to be 403 error
        self.assertEqual(json.loads(response.content), [])

    # queryset satisfies filter_for_user_selectable_tasks
    def test_user_selectable_success(self):
        new_rank = Rank.objects.create(name="rank")
        rank_record = RankRecord.objects.create(user=self.user, rank=new_rank)
        rank_limit = RankLimit.objects.create(rank=new_rank, stage=self.task_stage,
                                              open_limit=2, total_limit=3,
                                              is_selection_open=True, is_listing_allowed=True)

        self.user.managed_campaigns.add(self.campaign)
        task = [Task.objects.create(stage=self.task_stage,
                                    complete=False) for x in range(5)]
        another_manager = CustomUser.objects.create(username="another_manager", email='an@email.com',
                                                    password='another')
        another_campaign = Campaign.objects.create(name="Campaign")
        another_chain = Chain.objects.create(name="Chain", campaign=another_campaign)
        another_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                      chain=another_chain)
        another_task = [Task.objects.create( stage=another_task_stage,
                                            complete=False) for x in range(5)]
        self.assertEqual(Task.objects.count(), 10)
        response = self.client.get(self.url_tasks + "user_selectable/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)), 5)

    # User can see only assigned tasks
    def test_user_relevant_fail(self):
        [Task.objects.create(assignee=self.employer, stage=self.task_stage,
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


class RankTest(APITestCase):
    def setUp(self):
        self.url_rank = reverse('rank-list')

        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.new_user = CustomUser.objects.create_user(username="new_user", email='new_user@email.com',
                                                       password='new_user')
        self.employer = CustomUser.objects.create(username="empl", email='empl@email.com', password='empl')

        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(name="Campaign")
        self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        self.conditional_stage = ConditionalStage.objects.create(name="Conditional Stage", x_pos=1, y_pos=1,
                                                                 chain=self.chain)
        self.task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                   chain=self.chain)
        self.rank_json = {
            "name": "rank created in tests",
            "description": ""
        }

    # If user is manager and he has campaign and track with ranks can see ranks
    # simple user want to see ranks,
    def test_list_fail(self):
        track = Track.objects.create(name="My Track", campaign=self.campaign)
        new_ranks = [Rank.objects.create(name="new rank", track=track) for i in range(5)]
        another_campaign = Campaign.objects.create(name="another_campaign")
        another_track = Track.objects.create(name="My Track", campaign=another_campaign)
        another_ranks = [Rank.objects.create(name="new rank", track=another_track) for i in range(5)]
        self.new_user.managed_campaigns.add(another_campaign)
        self.assertEqual(Rank.objects.count(), 10)

        response = self.client.get(self.url_rank)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # todo: there is have to be 403 error
        self.assertEqual(json.loads(response.content), [])

    # manager gets his ranks
    def test_list_success(self):
        track = Track.objects.create(name="My Track", campaign=self.campaign)
        new_ranks = [Rank.objects.create(name="new rank", track=track) for i in range(5)]
        self.user.managed_campaigns.add(self.campaign)

        another_campaign = Campaign.objects.create(name="another_campaign")
        another_track = Track.objects.create(name="My Track", campaign=another_campaign)
        another_ranks = [Rank.objects.create(name="new rank", track=another_track) for i in range(5)]
        self.new_user.managed_campaigns.add(another_campaign)
        self.assertEqual(Rank.objects.count(), 10)

        response = self.client.get(self.url_rank)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(json.loads(response.content), [])
        self.assertEqual(len(json.loads(response.content)), 5)

    # Only manager can retrieve his ranks
    # simple user try to get some rank
    def test_retrieve_fail(self):
        track = Track.objects.create(name="My Track", campaign=self.campaign)
        new_ranks = [Rank.objects.create(name="new rank", track=track) for i in range(5)]
        another_campaign = Campaign.objects.create(name="another_campaign")
        another_track = Track.objects.create(name="My Track", campaign=another_campaign)
        another_ranks = [Rank.objects.create(name="new rank", track=another_track) for i in range(5)]
        self.employer.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(another_campaign)
        self.assertEqual(Rank.objects.count(), 10)

        for rank in Rank.objects.all():
            response = self.client.get(self.url_rank + f"{rank.id}/")
            # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # todo: there is have to be 403 error
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # manager get his rank
    def test_retrieve_success(self):
        track = Track.objects.create(name="My Track", campaign=self.campaign)
        my_ranks = [Rank.objects.create(name="new rank", track=track) for i in range(5)]
        self.user.managed_campaigns.add(self.campaign)

        another_campaign = Campaign.objects.create(name="another_campaign")
        another_track = Track.objects.create(name="My Track", campaign=another_campaign)
        another_ranks = [Rank.objects.create(name="new rank", track=another_track) for i in range(5)]
        self.new_user.managed_campaigns.add(another_campaign)
        self.assertEqual(Rank.objects.count(), 10)

        for rank in my_ranks:
            response = self.client.get(self.url_rank + f"{rank.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertNotEqual(json.loads(response.content), {})

    # only managers of any campaign can create ranks
    # simple user try to create rank it will fail
    def test_create_simple_user_fail(self):
        track = Track.objects.create(name="My Track", campaign=self.campaign)
        self.assertEqual(Rank.objects.count(), 0)
        self.new_user.managed_campaigns.add(self.campaign)
        self.assertNotIn(self.user, self.campaign.managers.all())
        self.rank_json['track'] = track.id

        response = self.client.post(self.url_rank, self.rank_json)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Rank.objects.count(), 0)

    # manager try to create rank it will successful create
    def test_create_manager_success(self):
        track = Track.objects.create(name="My Track", campaign=self.campaign)
        self.assertEqual(Rank.objects.count(), 0)
        self.user.managed_campaigns.add(self.campaign)
        self.assertIn(self.user, self.campaign.managers.all())
        self.rank_json['track'] = track.id

        response = self.client.post(self.url_rank, self.rank_json)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(response.content)['name'], self.rank_json['name'])

    # only manager of campaign can update rank
    # simple user try to update rank it will fail
    def test_partial_update_simple_user_fail(self):
        track = Track.objects.create(name="My Track", campaign=self.campaign)
        self.assertEqual(Rank.objects.count(), 0)
        self.new_user.managed_campaigns.add(self.campaign)
        new_rank = Rank.objects.create(name="new rank", track=track)
        self.assertNotIn(self.user, self.campaign.managers.all())
        self.rank_json['track'] = track.id

        to_update = {"name":"UPDATED"}
        response = self.client.patch(self.url_rank+f"{track.id}/", to_update)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # there is hav to be 403 error
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Rank.objects.count(), 1)
        self.assertEqual(new_rank, Rank.objects.get(id=new_rank.id))
        self.assertEqual(new_rank.name, Rank.objects.get(id=new_rank.id).name)
        self.assertNotEqual(new_rank.name, to_update['name'])

    # only manager of campaign can update rank
    # simple user try to update rank it will be successfully updated
    def test_partial_update_manager_success(self):
        track = Track.objects.create(name="My Track", campaign=self.campaign)
        self.assertEqual(Rank.objects.count(), 0)
        self.user.managed_campaigns.add(self.campaign)
        new_rank = Rank.objects.create(name="new rank", track=track)
        self.assertIn(self.user, self.campaign.managers.all())
        self.rank_json['track'] = track.id

        to_update = {"name": "UPDATED"}
        response = self.client.patch(self.url_rank + f"{track.id}/", to_update)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Rank.objects.count(), 1)
        self.assertNotEqual(new_rank.name, Rank.objects.get(id=new_rank.id).name)
        self.assertEqual(to_update['name'], Rank.objects.get(id=new_rank.id).name)
