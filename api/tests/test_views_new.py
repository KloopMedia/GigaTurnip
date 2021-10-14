import django, json, random
from django.forms.models import model_to_dict

django.setup()

from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from django.contrib.auth.models import Group
from api.models import CustomUser, Campaign, Chain, ConditionalStage
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
        self.assertEqual(response_not_my_chain.status_code, status.HTTP_404_NOT_FOUND) # todo: is there have to be 403 error
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
        self.assertEqual(response_update_not_my_chain.status_code, status.HTTP_404_NOT_FOUND) # todo: ask about 403 status code

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
        chain['name'] ="try to change chain name"
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
        self.client.force_authenticate(user=self.user)
        self.campaign = {"name": "campaign", "description": "description"}
        self.chain = {"name": "chain", "description": "description", "campaign": None}
        self.conditional_stage = {
            "name": "conditional_stage",
            "chain": None,
            "x_pos": 1,
            "y_pos": 1
        }
        self.campaign_creator_group = Group.objects.create(name='campaign_creator')

    def test_list_fail(self):
        response = self.client.get(self.url_conditional_stage)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(json.loads(response.content), [])

    def test_list_with_filter_not_my_chain_fail(self):
        new_campaign = Campaign.objects.create(name="new campaign")
        new_chain = Chain.objects.create(name="new campaign", campaign=new_campaign)
        new_user = CustomUser.objects.create_user(username='new', email='new@email.com', password='new')
        new_user.managed_campaigns.add(new_campaign)

        my_campaign = Campaign.objects.create(name='my campaign')
        my_chain = Chain.objects.create(name='my chain', campaign=my_campaign)
        self.campaign_creator_group.user_set.add(self.user)
        self.user.managed_campaigns.add(my_campaign)

        response = self.client.get(self.url_conditional_stage)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(json.loads(response.content), [])

    def test_list_campaign_chain_success(self):
        campaign = Campaign.objects.create(name="campaign")
        chain = Chain.objects.create(name="chain", campaign=campaign)
        self.user.managed_campaigns.add(campaign)

        response = self.client.get(self.url_conditional_stage + f"?chain={chain.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_campaign_not_my_chain_fail(self):
        new_user = CustomUser.objects.create_user(username='new user')
        new_campaign = Campaign.objects.create(name='new campaign')
        new_chain = Chain.objects.create(name='new chain', campaign=new_campaign)
        self.campaign_creator_group.user_set.add(new_user)
        new_user.managed_campaigns.add(new_campaign)

        campaign = Campaign.objects.create(name="campaign")
        chain = Chain.objects.create(name="chain", campaign=campaign)
        self.user.managed_campaigns.add(campaign)

        self.assertEqual(ConditionalStage.objects.count(), 0)

        cond_stage = self.conditional_stage
        cond_stage['chain'] = new_chain.id
        response = self.client.post(self.url_conditional_stage + f"?chain={new_chain.id}", cond_stage)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ConditionalStage.objects.count(), 0)

    def test_create_campaign_chain_success(self):
        campaign = Campaign.objects.create(name="campaign")
        chain = Chain.objects.create(name="chain", campaign=campaign)
        self.user.managed_campaigns.add(campaign)

        self.assertEqual(ConditionalStage.objects.count(), 0)

        cond_stage = self.conditional_stage
        cond_stage['chain'] = chain.id
        response = self.client.post(self.url_conditional_stage + f"?chain={chain.id}", cond_stage)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ConditionalStage.objects.count(), 1)
        my_conditional_stage = ConditionalStage.objects.get(id=response.data.get('id'))
        self.assertIn(self.user, my_conditional_stage.chain.campaign_json.managers.all())
