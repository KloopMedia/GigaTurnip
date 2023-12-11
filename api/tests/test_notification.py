import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json

from firebase_admin import credentials, messaging

from api.utils.push_notifications import send_push_notification


class NotificationTest(GigaTurnipTestHelper):

    def test_notification_with_target_user(self):
        [Notification.objects.create(
            title=f"Hello world{i}",
            text="There are new chain for you",
            campaign=self.campaign,
            target_user=self.user
        )
            for i in range(5)]
        user_notifications = self.user.notifications.all().order_by(
            '-created_at')

        for i in user_notifications[:2]:
            response = self.get_objects("notification-detail", pk=i.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.notifications.filter(
            notification_statuses__user=self.user).count(), 2)

        for i in user_notifications[:2]:
            response = self.get_objects("notification-detail", pk=i.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(user_notifications.filter(
            notification_statuses__user=self.user).count(), 2)

        for i in user_notifications[:2]:
            response = self.get_objects("notification-open-notification",
                                        pk=i.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(user_notifications.filter(
            notification_statuses__user=self.user).count(), 2)

        for i in user_notifications[2:]:
            response = self.get_objects("notification-open-notification",
                                        pk=i.id)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(user_notifications.filter(
            notification_statuses__user=self.user).count(), 5)

        for i in user_notifications[:2]:
            response = self.get_objects("notification-detail",
                                        client=self.employee_client, pk=i.id)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(NotificationStatus.objects.count(), 5)

    def test_notification_with_manager(self):
        notifications = [Notification.objects.create(
            title=f"Hello world{i}",
            text="There are new chain for you",
            campaign=self.campaign,
            target_user=self.user
        )
            for i in range(5)]
        self.employee.managed_campaigns.add(self.campaign)
        for i in notifications[:]:
            response = self.get_objects("notification-detail",
                                        client=self.employee_client, pk=i.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Notification.objects.filter(
            notification_statuses__user=self.employee).count(), 5)
        self.employee.managed_campaigns.remove(self.campaign)
        self.assertEqual(NotificationStatus.objects.count(), 5)

    def test_notification_with_target_rank(self):
        ranks_notifications = [Notification.objects.create(
            title=f"Hello world{i}",
            text="There are new chain for you",
            campaign=self.campaign,
            rank=self.default_rank
        )
            for i in range(5)]

        self.assertFalse(self.default_rank in self.user.ranks.all())
        for i in ranks_notifications[:]:
            response = self.get_objects("notification-detail",
                                        client=self.employee_client, pk=i.id)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            Notification.objects.filter(rank=self.default_rank,
                                        notification_statuses__user=self.user).count(),
            0)

        self.user.ranks.add(self.default_rank)
        for i in ranks_notifications[:]:
            response = self.get_objects("notification-detail", pk=i.id)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Notification.objects.filter(rank=self.default_rank,
                                        notification_statuses__user=self.user).count(),
            5)
        self.assertEqual(NotificationStatus.objects.count(), 5)

    def test_auto_notification_simple(self):
        js_schema = {
            "type": "object",
            "properties": {
                'foo': {
                    "type": "string",
                }
            }
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name='Second stage',
                json_schema=self.initial_stage.json_schema,
                assign_user_by=TaskStageConstants.STAGE
            )
        )

        notification = Notification.objects.create(
            title='Congrats you have completed your first task!',
            campaign=self.campaign
        )

        auto_notification = AutoNotification.objects.create(
            trigger_stage=self.initial_stage,
            recipient_stage=self.initial_stage,
            notification=notification
        )

        task = self.create_initial_task()
        task = self.complete_task(task, {"foo": "hello world!"})

        self.assertEqual(self.user.notifications.count(), 1)
        self.assertEqual(Notification.objects.count(), 2)
        self.assertEqual(self.user.notifications.filter(sender_task=task,
                                                        receiver_task=task).count(),
                         1)
        self.assertEqual(self.user.notifications.all()[0].title,
                         notification.title)

    def test_push_notification(self):
        token = 'far0LXGJRHW6cMR7_FD6Nt:APA91bEK2eOy3Yp959sjWqtZ8uzmoTnWr_wQxDcdMOfZttN4ClIyo9_U3koPp6weImaJ9u6yHLvZePEBOP7AlozVeooCyzatLF8FQ1V4fFCfzmUpaC4FZSGXhxp_t2uK2zxh7oxyYWuq'

        send_push_notification(token, 'Hello', 'Body')
