import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants
from api.models import *
from api.tests import GigaTurnipTestHelper


class AutoNotificationTest(GigaTurnipTestHelper):

    def test_auto_notification_last_one_option_as_go(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "foo": {"type": "string"}
            }
        })
        notification = Notification.objects.create(
            title='Congrats!',
            campaign=self.campaign
        )
        AutoNotification.objects.create(
            trigger_stage=self.initial_stage,
            recipient_stage=self.initial_stage,
            notification=notification,
            go=AutoNotificationConstants.LAST_ONE
        )
        task = self.create_initial_task()
        task = self.complete_task(task, {"foo": "boo"})
        self.assertEqual(Notification.objects.count(), 2)
        self.assertEqual(self.user.notifications.filter(sender_task=task,
                                                        receiver_task=task).count(), 1)
        response = self.get_objects('task-user-selectable', client=self.employee_client)

    def test_last_task_notification_errors_creation(self):
        js_schema = {
            "type": "object",
            "properties": {
                'answer': {
                    "type": "string",
                }
            }
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        rank_verifier = Rank.objects.create(name='verifier rank')
        RankRecord.objects.create(rank=rank_verifier, user=self.employee)

        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Get on verification",
            assign_user_by=TaskStageConstants.RANK,
            json_schema=json.dumps(js_schema)
        ))
        RankLimit.objects.create(rank=rank_verifier, stage=second_stage)
        third_stage = second_stage.add_stage(TaskStage(
            name="Some routine stage",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=second_stage,
            json_schema=json.dumps(js_schema)
        ))
        four_stage = third_stage.add_stage(TaskStage(
            name="Finish stage",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=third_stage,
            json_schema=json.dumps(js_schema)
        ))

        notif_1 = Notification.objects.create(
            title='It is your first step along the path to the goal.',
            text='',
            campaign=self.campaign,
        )
        notif_2 = Notification.objects.create(
            title='Verifier get your task and complete it already.',
            text='You almost finish your chan',
            campaign=self.campaign,
        )
        notif_3 = Notification.objects.create(
            title='Documents in the process',
            text='',
            campaign=self.campaign,
        )
        notif_4 = Notification.objects.create(
            title='You have finished your chain!',
            text='',
            campaign=self.campaign,
        )

        AutoNotification.objects.create(
            trigger_stage=self.initial_stage,
            recipient_stage=self.initial_stage,
            notification=notif_1,
            go=AutoNotificationConstants.FORWARD,
        )
        AutoNotification.objects.create(
            trigger_stage=second_stage,
            recipient_stage=self.initial_stage,
            notification=notif_2,
            go=AutoNotificationConstants.FORWARD,
        )
        AutoNotification.objects.create(
            trigger_stage=self.initial_stage,
            recipient_stage=third_stage,
            notification=notif_3,
            go=AutoNotificationConstants.FORWARD,
        )
        AutoNotification.objects.create(
            recipient_stage=four_stage,
            trigger_stage=self.initial_stage,
            notification=notif_4,
            go=AutoNotificationConstants.LAST_ONE,
        )

        task = self.create_initial_task()
        task = self.complete_task(
            task, {"answer": "Hello World!My name is Artur"}
        )

        self.assertEqual(ErrorItem.objects.count(), 1)
        self.assertEqual(ErrorItem.objects.get().campaign, self.campaign)

    def test_last_task_notification(self):
        js_schema = {
            "type": "object",
            "properties": {
                'answer': {
                    "type": "string",
                }
            }
        }
        self.initial_stage.json_schema = json.dumps(js_schema)
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Get on verification",
            assign_user_by=TaskStageConstants.RANK,
            json_schema=json.dumps(js_schema)
        ))
        third_stage = second_stage.add_stage(TaskStage(
            name="Some routine stage",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=second_stage,
            json_schema=json.dumps(js_schema)
        ))
        four_stage = third_stage.add_stage(TaskStage(
            name="Finish stage",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=third_stage,
            json_schema=json.dumps(js_schema)
        ))

        notif_1 = Notification.objects.create(
            title='It is your first step along the path to the goal.',
            text='',
            campaign=self.campaign,
        )
        notif_2 = Notification.objects.create(
            title='Verifier get your task and complete it already.',
            text='You almost finish your chan',
            campaign=self.campaign,
        )
        notif_3 = Notification.objects.create(
            title='Documents in the process',
            text='',
            campaign=self.campaign,
        )
        notif_4 = Notification.objects.create(
            title='You have finished your chain!',
            text='',
            campaign=self.campaign,
        )

        AutoNotification.objects.create(
            trigger_stage=self.initial_stage,
            recipient_stage=self.initial_stage,
            notification=notif_1,
            go=AutoNotificationConstants.FORWARD,
        )
        AutoNotification.objects.create(
            trigger_stage=second_stage,
            recipient_stage=self.initial_stage,
            notification=notif_2,
            go=AutoNotificationConstants.FORWARD,
        )
        AutoNotification.objects.create(
            trigger_stage=third_stage,
            recipient_stage=self.initial_stage,
            notification=notif_3,
            go=AutoNotificationConstants.FORWARD,
        )
        AutoNotification.objects.create(
            trigger_stage=four_stage,
            recipient_stage=self.initial_stage,
            notification=notif_4,
            go=AutoNotificationConstants.LAST_ONE,
        )

        verifier = self.prepare_client(second_stage, self.employee)

        task = self.create_initial_task()
        task = self.complete_task(
            task, {"answer": "Hello World!My name is Artur"}
        )
        self.assertEqual(self.user.notifications.count(), 1)
        self.assertEqual(Notification.objects.count(), 5)

        response = self.get_objects('notification-last-task-notifications')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'],
                         self.user.notifications.get().id)

        out_task = self.request_assignment(
            task.out_tasks.get(), verifier
        )

        step = 1
        total_notifications_count = 5
        for i, notification in enumerate([notif_2, notif_3, notif_4]):
            out_task = self.complete_task(
                out_task,
                {"answer": f"Good answer. Process {step}/4"},
                client=verifier
            )
            total_notifications_count += 1
            step += 1
            # check notification creation on task completion
            self.assertTrue(Task.objects.get(pk=out_task.pk).responses)
            self.assertEqual(self.user.notifications.count(), step)
            self.assertEqual(Notification.objects.count(),
                             total_notifications_count)

            # check last notifications for every tasks
            response = self.get_objects('notification-last-task-notifications')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['count'], 1)
            notification_received = response.data['results'][0]
            self.assertEqual(notification_received['id'],
                             self.user.notifications
                             .order_by('-created_at')[0].id)
            self.assertEqual(notification_received['title'], notification.title)
            if step < 4:
                out_task = out_task.out_tasks.get()