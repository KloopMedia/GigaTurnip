import django, json, random
from django.forms.models import model_to_dict

django.setup()

from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from django.contrib.auth.models import Group
from api.models import CustomUser, Campaign, Chain, ConditionalStage, TaskStage, Rank, RankLimit, Task, RankRecord, \
    Track, CampaignManagement, Stage, Case, Notification, NotificationStatus
from rest_framework import status


class NotificationTest(APITestCase):
    def setUp(self):
        self.url = reverse("notification-list")
        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.new_user = CustomUser.objects.create_user(username="new_user", email='new_user@email.com',
                                                       password='new_user')
        self.employee = CustomUser.objects.create_user(username="employee", email='employee@email.com', password='employee')
        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(name="Campaign")
        self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        self.conditional_stage = ConditionalStage.objects.create(name="Conditional Stage", x_pos=1, y_pos=1,
                                                                 chain=self.chain)
        self.task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                   chain=self.chain)
        self.rank = Rank.objects.create(name="new rank for new user" )
        self.rank_limit = RankLimit.objects.create(rank=self.rank, stage=self.task_stage,
                                                   open_limit=3, total_limit=4)
        self.notification = [Notification.objects.create(title=f"HI!{i}",text=f'Hello world!#{i}', rank=self.rank, campaign=self.campaign) for i in range(5)]

        self.another_campaign = Campaign.objects.create(name="Another Campaign")
        self.another_chain = Chain.objects.create(name="Another Chain", campaign=self.another_campaign)
        self.another_conditional_stage = ConditionalStage.objects.create(name="Another Conditional Stage", x_pos=1, y_pos=1,
                                                                 chain=self.another_chain)
        self.another_task_stage = TaskStage.objects.create(name="Another Task stage", x_pos=1, y_pos=1,
                                                   chain=self.another_chain)
        self.another_rank = Rank.objects.create(name="new rank for new another chain")
        self.rank_limit = RankLimit.objects.create(rank=self.another_rank, stage=self.another_task_stage,
                                                   open_limit=3, total_limit=4)
        self.another_notification = [Notification.objects.create(title=f"HI another!{i}", text=f'Another Hello world!#{i}', rank=self.another_rank,
                                                         campaign=self.another_campaign) for i in range(5)]

    # only managers and users with some ranks can see notification with same rank
    # Manager list his notification
    def test_list_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), len(self.notification))

    # user with the same rank list notification
    def test_list_same_rank_success(self):
        self.new_user.managed_campaigns.add(self.campaign)
        RankRecord.objects.create(user=self.user, rank=self.rank)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), len(self.notification))

    # Manager see only his notification
    def test_list_many_notification_and_campaign_success(self):
        self.user.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), len(self.notification))
        self.assertEqual(Notification.objects.count(), len(self.notification+self.another_notification))

    # Simple user can't see any notification
    def test_list_user_no_rank_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # todo: there is have to be 403 error
        self.assertEqual(json.loads(response.content)['results'], [])

    # Only user with the same rank can retrieve notification, this request must create notification status instance with viewed True
    # Mnager retrieve his notification, notification status won't be created
    def test_retrieve_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)

        for notification in self.notification:
            response = self.client.get(self.url+f"{notification.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertNotEqual(json.loads(response.content), {})

        self.assertEqual(NotificationStatus.objects.filter(user=self.user).filter(viewed=True).count(), 0)

    # user with the same rank retrieve his notification
    def test_retrieve_user_with_same_rank_success(self):
        self.new_user.managed_campaigns.add(self.campaign)
        RankRecord.objects.create(user=self.user, rank=self.rank)
        self.assertEqual(NotificationStatus.objects.count(), 0)

        for notification in self.notification:
            response = self.client.get(self.url+f"{notification.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertNotEqual(json.loads(response.content), {})

        self.assertEqual(NotificationStatus.objects.filter(user=self.user).filter(viewed=True).count(), 5)

    # user with another rank can't retrieve another notification
    def test_retrieve_user_with_another_rank_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        RankRecord.objects.create(user=self.user, rank=self.another_rank)

        for notification in self.notification:
            response = self.client.get(self.url+f"{notification.id}/")
            # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # todo: there is have to be 403 error
            self.assertEqual(json.loads(response.content), {})

    # list_user_notifications
    def test_list_user_notifications_success(self):
        self.new_user.managed_campaigns.add(self.campaign)
        RankRecord.objects.create(user=self.user, rank=self.rank)

        response = self.client.get(self.url+f"list_user_notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), len(self.notification))

    def test_list_user_notifications_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url+f"list_user_notifications/")
        self.assertEqual(json.loads(response.content)['results'], [])
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # todo: there is have to be 403 error
