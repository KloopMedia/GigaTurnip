import django, json, random

django.setup()

from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from django.contrib.auth.models import Group
from api.models import CustomUser, Campaign, Chain
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
        self.campaign = {"name": "campaign", "description": "description"}
        self.chain = {"name": "chain", "description": "description", "campaign": None}
        self.campaign_creator_group = Group.objects.create(name='campaign_creator')

    def test_list_no_campaign_fail(self):
        self.assertEqual(Campaign.objects.count(), 0)
        self.assertEqual(Chain.objects.count(), 0)
        response = self.client.get(self.url_chain)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_campaign_success(self):
        self.campaign_creator_group.user_set.add(self.user)
        self.assertEqual(Campaign.objects.count(), 0)
        self.assertEqual(Chain.objects.count(), 0)
        response_create_campaign = self.client.post(self.url_campaign, self.campaign)
        self.assertEqual(response_create_campaign.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Campaign.objects.count(), 1)

        campaign_id = response_create_campaign.data.get('id')
        self.user.managed_campaigns.add(Campaign.objects.get(id=campaign_id))
        response_get_campaign = self.client.get(self.url_campaign + f"{campaign_id}/")
        self.assertEqual(response_get_campaign.status_code, status.HTTP_200_OK)
        response = self.client.get(self.url_chain + f"?campaign={campaign_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
        self.assertEqual(Chain.objects.count(), 0)

    def test_create_no_exist_campaign_fail(self):
        self.assertEqual(Campaign.objects.count(), 0)
        no_exist_id = 21
        response = self.client.post(self.url_chain + f"?campaign={no_exist_id}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_not_my_campaign_fail(self):
        new_user = CustomUser.objects.create_user(username='new user')
        new_campaign = Campaign.objects.create(name='new campaign')
        self.campaign_creator_group.user_set.add(new_user)
        new_user.managed_campaigns.add(new_campaign)

        self.campaign_creator_group.user_set.add(self.user)
        self.assertEqual(CustomUser.objects.count(), 2)
        response_create_campaign = self.client.post(self.url_campaign, self.campaign)
        self.assertEqual(response_create_campaign.status_code, status.HTTP_201_CREATED)
        my_campaign = Campaign.objects.get(id=response_create_campaign.data.get('id'))
        self.user.managed_campaigns.add(my_campaign)

        chain_refers_not_my_campaign = self.chain
        chain_refers_not_my_campaign['campaign'] = new_campaign.id
        response_create_chain_not_my_campaign = self.client.post(
            self.url_chain + f'?campaign={my_campaign.id}',
            chain_refers_not_my_campaign
        )
        self.assertEqual(response_create_chain_not_my_campaign.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_chain_based_on_my_campaign_success(self):
        self.campaign_creator_group.user_set.add(self.user)
        response_create_campaign = self.client.post(self.url_campaign, self.campaign)
        self.assertEqual(response_create_campaign.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Campaign.objects.count(), 1)
        my_campaign = Campaign.objects.get(id=response_create_campaign.data.get('id'))
        self.user.managed_campaigns.add(my_campaign)

        chain = self.chain
        chain['campaign'] = my_campaign.id
        response_create_chain = self.client.post(self.url_chain+f"?campaign={my_campaign.id}", chain)
        self.assertEqual(response_create_chain.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Chain.objects.count(), 1)
        my_chain = Chain.objects.get(id=response_create_chain.data.get('id'))
        self.assertIn(self.user, my_chain.campaign.managers.all())
        self.assertEqual(1, my_chain.campaign.managers.count())

    def test_retrieve_my_campaign_not_my_chain_fail(self):
        new_user = CustomUser.objects.create_user(username='new user')
        new_campaign = Campaign.objects.create(name='new campaign')
        new_chain = Chain.objects.create(name='new chain', campaign=new_campaign)
        self.campaign_creator_group.user_set.add(new_user)
        new_user.managed_campaigns.add(new_campaign)

        self.campaign_creator_group.user_set.add(self.user)
        response_create_campaign = self.client.post(self.url_campaign, self.campaign)
        self.assertEqual(response_create_campaign.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Campaign.objects.count(), 2)
        my_campaign = Campaign.objects.get(id=response_create_campaign.data.get('id'))
        self.user.managed_campaigns.add(my_campaign)
        my_chain = Chain.objects.create(name='my chain', campaign=my_campaign)
        self.assertEqual(Chain.objects.count(), 2)

        response_not_my_chain = self.client.get(self.url_chain+f"{new_chain.id}/")
        self.assertEqual(response_not_my_chain.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotIn(self.user, new_chain.campaign.managers.all())


    def test_retrieve_my_campaign_my_chain_success(self):
        self.campaign_creator_group.user_set.add(self.user)
        response_create_campaign = self.client.post(self.url_campaign, self.campaign)
        self.assertEqual(response_create_campaign.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Campaign.objects.count(), 1)
        my_campaign = Campaign.objects.get(id=response_create_campaign.data.get('id'))
        self.user.managed_campaigns.add(my_campaign)
        my_chain = Chain.objects.create(name='my chain', campaign=my_campaign)
        self.assertEqual(Chain.objects.count(), 1)

        response_not_my_chain = self.client.get(self.url_chain + f"{my_chain.id}/")
        self.assertEqual(response_not_my_chain.status_code, status.HTTP_200_OK)

    def test_partial_update_not_my_chain_fail(self):
        new_user = CustomUser.objects.create_user(username='new user')
        new_campaign = Campaign.objects.create(name='new campaign')
        new_chain = Chain.objects.create(name='new chain', campaign=new_campaign)
        self.campaign_creator_group.user_set.add(new_user)
        new_user.managed_campaigns.add(new_campaign)

        self.campaign_creator_group.user_set.add(self.user)
        self.assertEqual(CustomUser.objects.count(), 2)
        response_create_campaign = self.client.post(self.url_campaign, self.campaign)
        self.assertEqual(response_create_campaign.status_code, status.HTTP_201_CREATED)
        my_campaign = Campaign.objects.get(id=response_create_campaign.data.get('id'))
        self.user.managed_campaigns.add(my_campaign)
        my_chain = Chain.objects.create(name='my chain', campaign=my_campaign)
        self.assertEqual(Chain.objects.count(), 2)

        response_update_not_my_chain = self.client.patch(
            self.url_chain + f"{new_chain.id}/",
            {"name":"try to change chain name"}
            )
        self.assertEqual(response_update_not_my_chain.status_code, status.HTTP_404_NOT_FOUND)

    def test_partial_update_not_my_chain_fail(self):
        new_user = CustomUser.objects.create_user(username='new user')
        new_campaign = Campaign.objects.create(name='new campaign')
        new_chain = Chain.objects.create(name='new chain', campaign=new_campaign)
        self.campaign_creator_group.user_set.add(new_user)
        new_user.managed_campaigns.add(new_campaign)

        self.campaign_creator_group.user_set.add(self.user)
        self.assertEqual(CustomUser.objects.count(), 2)
        response_create_campaign = self.client.post(self.url_campaign, self.campaign)
        self.assertEqual(response_create_campaign.status_code, status.HTTP_201_CREATED)
        my_campaign = Campaign.objects.get(id=response_create_campaign.data.get('id'))
        self.user.managed_campaigns.add(my_campaign)
        my_chain = Chain.objects.create(name='my chain', campaign=my_campaign)
        self.assertEqual(Chain.objects.count(), 2)

        response_update_my_chain = self.client.patch(
            self.url_chain + f"{new_chain.id}/",
            {"name": "try to change chain name"}
        )
        self.assertEqual(response_update_my_chain.status_code, status.HTTP_404_NOT_FOUND)

    def test_partial_update_success(self):
        new_user = CustomUser.objects.create_user(username='new user')
        new_campaign = Campaign.objects.create(name='new campaign')
        new_chain = Chain.objects.create(name='new chain', campaign=new_campaign)
        self.campaign_creator_group.user_set.add(new_user)
        new_user.managed_campaigns.add(new_campaign)

        self.campaign_creator_group.user_set.add(self.user)
        self.assertEqual(CustomUser.objects.count(), 2)
        response_create_campaign = self.client.post(self.url_campaign, self.campaign)
        self.assertEqual(response_create_campaign.status_code, status.HTTP_201_CREATED)
        my_campaign = Campaign.objects.get(id=response_create_campaign.data.get('id'))
        self.user.managed_campaigns.add(my_campaign)
        my_chain = Chain.objects.create(name='my chain', campaign=my_campaign)
        self.assertEqual(Chain.objects.count(), 2)

        response_update_my_chain = self.client.patch(
            self.url_chain + f"{my_chain.id}/",
            {"name": "try to change chain name"}
        )
        self.assertEqual(response_update_my_chain.status_code, status.HTTP_200_OK)
