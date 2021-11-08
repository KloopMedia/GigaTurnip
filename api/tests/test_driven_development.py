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
        self.employee = CustomUser.objects.create_user(username="employee", email='employee@email.com',
                                                       password='employee')
        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(name="Campaign")
        self.rank = Rank.objects.create(name="new rank for new user")
        self.notification = [Notification.objects.create(title=f"HI!{i}", text=f'Hello world!#{i}', rank=self.rank,
                                                         campaign=self.campaign) for i in range(5)]

        # self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        # self.conditional_stage = ConditionalStage.objects.create(name="Conditional Stage", x_pos=1, y_pos=1,
        #                                                          chain=self.chain)
        # self.task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
        #                                            chain=self.chain)
        # self.rank_limit = RankLimit.objects.create(rank=self.rank, stage=self.task_stage,
        #                                            open_limit=3, total_limit=4)

        self.another_campaign = Campaign.objects.create(name="Another Campaign")
        self.another_rank = Rank.objects.create(name="new rank for new another chain")
        self.another_notification = [
            Notification.objects.create(title=f"HI another!{i}", text=f'Another Hello world!#{i}',
                                        rank=self.another_rank, campaign=self.another_campaign) for i in range(5)]

        # self.another_chain = Chain.objects.create(name="Another Chain", campaign=self.another_campaign)
        # self.another_conditional_stage = ConditionalStage.objects.create(name="Another Conditional Stage", x_pos=1, y_pos=1,
        #                                                          chain=self.another_chain)
        # self.another_task_stage = TaskStage.objects.create(name="Another Task stage", x_pos=1, y_pos=1,
        #                                            chain=self.another_chain)
        # self.another_rank_limit = RankLimit.objects.create(rank=self.another_rank, stage=self.another_task_stage,
        #                                            open_limit=3, total_limit=4)

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

    # Only user with the same rank can retrieve notification, this request must create notification status instance
    # Mnager retrieve his notification, notification status won't be created
    def test_retrieve_manager_success(self):
        self.user.managed_campaigns.add(self.campaign)

        for notification in self.notification:
            response = self.client.get(self.url+f"{notification.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertNotEqual(json.loads(response.content), {})

        self.assertEqual(NotificationStatus.objects.filter(user=self.user).count(), 5)

    # Mnager retrieve not his notification, notification status won't be created. Response status code must be 403
    def test_retrieve_manager_another_notification_fail(self):
        self.user.managed_campaigns.add(self.campaign)

        for notification in self.another_notification:
            response = self.client.get(self.url+f"{notification.id}/")
            # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # todo: there have to be 403 status code
            self.assertEqual(json.loads(response.content), {})

        self.assertEqual(NotificationStatus.objects.filter(user=self.user).count(), 0)

    # user with the same rank retrieve his notification. response status code must be 200 and this request must create notification
    def test_retrieve_user_with_same_rank_success(self):
        self.new_user.managed_campaigns.add(self.campaign)
        RankRecord.objects.create(user=self.user, rank=self.rank)
        self.assertEqual(NotificationStatus.objects.count(), 0)

        for notification in self.notification:
            response = self.client.get(self.url+f"{notification.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertNotEqual(json.loads(response.content), {})

        self.assertEqual(NotificationStatus.objects.filter(user=self.user).count(), 5)

    # user with another rank can't retrieve another notification. Response status code must be 403
    def test_retrieve_user_with_another_rank_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)
        RankRecord.objects.create(user=self.user, rank=self.another_rank)

        for notification in self.notification:
            response = self.client.get(self.url+f"{notification.id}/")
            # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # todo: there is have to be 403 error
            self.assertEqual(json.loads(response.content), {})

    # only managers and users with some ranks can see notification with same rank
    # Manager list his notification
    def test_list_notif_manager_success(self):  # ?importance=&campaign=1&rank=2
        self.user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url + f"list_user_notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), len(self.notification))

    # user with the same rank list notification
    def test_list_notif_same_rank_success(self):
        self.new_user.managed_campaigns.add(self.campaign)
        RankRecord.objects.create(user=self.user, rank=self.rank)

        response = self.client.get(self.url + f"list_user_notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), len(self.notification))

    # Manager see only his notification
    def test_list_notif_many_notification_and_campaign_success(self):
        self.user.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)

        response = self.client.get(self.url + f"list_user_notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), len(self.notification))

    # user isn't manager with no rank try to list notification. Response status code must be 403
    def test_list_notif_no_rank_fail(self):
        self.new_user.managed_campaigns.add(self.campaign)

        response = self.client.get(self.url + f"list_user_notifications/")
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # todo: there is have to be 403 error
        self.assertEqual(json.loads(response.content)['results'], [])

    # Filter list user notification by viewed field (there is must be only read notification)
    def test_list_notif_readTrue_success(self):
        self.employee.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)
        RankRecord.objects.create(user=self.user, rank=self.rank)

        [NotificationStatus.objects.create(user=self.user, notification=n) for n in
         self.notification[:3]]

        response = self.client.get(self.url + f"list_user_notifications/?viewed=true")
        content = json.loads(response.content)['results']
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content), 3)

    # Filter list user notification by viewed field (there is must be only unread notification)
    def test_list_notif_readFalse_success(self):
        self.employee.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)
        RankRecord.objects.create(user=self.user, rank=self.rank)

        [NotificationStatus.objects.create(user=self.user, notification=n) for n in
         self.notification[:2]]

        response = self.client.get(self.url + f"list_user_notifications/?viewed=false")
        content = json.loads(response.content)['results']
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content), 3)

    # Filter list user notification by campaign field
    def test_list_notif_campaign_success(self):
        new_campaign = Campaign.objects.create(name="New campaign to test notifications")
        new_rank = Rank.objects.create(name="New rank to test notifications")
        new_notifications = [Notification.objects.create(title=f"HI!{i}", text=f'Hello world!#{i}', rank=new_rank,
                                                         campaign=new_campaign) for i in range(2)]

        self.employee.managed_campaigns.add(new_campaign)
        self.employee.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)
        RankRecord.objects.create(user=self.user, rank=self.rank)
        RankRecord.objects.create(user=self.user, rank=new_rank)

        response = self.client.get(self.url + f"list_user_notifications/?campaign={new_campaign.id}")
        content = json.loads(response.content)['results']
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content), len(new_notifications))

    def test_list_notif_campaign_fail(self):
        new_campaign = Campaign.objects.create(name="New campaign to test notifications")
        new_rank = Rank.objects.create(name="New rank to test notifications")
        [Notification.objects.create(title=f"HI!{i}", text=f'Hello world!#{i}', rank=new_rank,
                                                         campaign=new_campaign) for i in range(2)]

        self.employee.managed_campaigns.add(new_campaign)
        self.employee.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)
        RankRecord.objects.create(user=self.user, rank=self.rank)

        response = self.client.get(self.url + f"list_user_notifications/?campaign={new_campaign.id}")
        content = json.loads(response.content)['results']
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # todo: there is have to be 403 status code
        self.assertEqual(len(content), 0)

    # Filter list user notification by importance field
    def test_list_notif_importance_success(self):
        self.employee.managed_campaigns.add(self.campaign)
        self.new_user.managed_campaigns.add(self.another_campaign)
        RankRecord.objects.create(user=self.user, rank=self.rank)

        for i in self.notification[:3]:
            i.importance = 1
            i.save()

        response = self.client.get(self.url + f"list_user_notifications/?importance={1}")
        content = json.loads(response.content)['results']
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content), 3)

    def test_open_notification_success(self):
        RankRecord.objects.create(user=self.user, rank=self.rank)
        notification_id = self.notification[0].id
        notification_status = {"user": self.user.id, "notification": notification_id}
        response = self.client.post(self.url + f"open_notification/{notification_id}/", notification_status)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_open_notification(self):
        notification_id = self.notification[0].id
        notification_status = {"user": self.user.id, "notification": notification_id}
        response = self.client.post(self.url + f"open_notification/{notification_id}/", notification_status)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_with_target_success(self):
        RankRecord.objects.create(user=self.user, rank=self.rank)
        Notification.objects.create(title=f"HI! targeted", text=f'Hello world!#{i}',
                                                               rank=None,
                                                               campaign=self.campaign, target_user=self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), len(self.notification)+1)

    def test_list_with_target_fail(self):
        RankRecord.objects.create(user=self.user, rank=self.rank)
        Notification.objects.create(title=f"HI! targeted", text=f'Hello world!#{i}',
                                                               rank=None,
                                                               campaign=self.campaign, target_user=self.new_user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.content)['results']), self.notification)

    def test_retrieve_with_target_success(self):
        RankRecord.objects.create(user=self.user, rank=self.rank)
        notification_with_target = Notification.objects.create(title=f"HI! targeted", text=f'Hello world!', rank=None,
                                                         campaign=self.campaign, target_user=self.user)

        response = self.client.get(self.url + f"{notification_with_target.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content)['title'], notification_with_target.title)