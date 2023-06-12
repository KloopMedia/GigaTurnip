import hashlib
import json
from uuid import uuid4

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIClient

from api.constans import (
    TaskStageConstants, CopyFieldConstants, AutoNotificationConstants,
    ErrorConstants, TaskStageSchemaSourceConstants, WebhookTargetConstants,
    WebhookConstants)
from api.models import CampaignLinker, ApproveLink, Language, Category, \
    Country, TranslateKey, Translation
from api.models import CustomUser, TaskStage, Campaign, Chain, \
    ConditionalStage, Stage, Rank, RankRecord, RankLimit, \
    Task, CopyField, Integration, Quiz, ResponseFlattener, Log, \
    AdminPreference, Track, TaskAward, Notification, \
    DynamicJson, PreviousManual, Webhook, AutoNotification, NotificationStatus, \
    ConditionalLimit, DatetimeSort, \
    ErrorGroup, ErrorItem, CampaignManagement


def to_json(string):
    return json.loads(string)


class GigaTurnipTest(APITestCase):

    def create_client(self, u):
        client = APIClient()
        client.force_authenticate(u)
        return client

    def prepare_client(self, stage, user=None, rank_limit=None, track=None,
                       priority=None):
        u = user
        if u is None:
            user_name = str(uuid4())
            u = CustomUser.objects.create_user(
                username=user_name,
                email=user_name + "@email.com",
                password='test')
        t = track if track else self.default_track
        p = priority if priority != None else 0
        rank = Rank.objects.create(name=stage.name, track=t, priority=p)
        RankRecord.objects.create(
            user=u,
            rank=rank)

        rank_l = rank_limit
        if rank_l is None:
            rank_l = RankLimit.objects.create(
                rank=rank,
                stage=stage,
                open_limit=0,
                total_limit=0,
                is_listing_allowed=True,
                is_creation_open=False)
        else:
            rank_l.rank = rank
            rank_l.stage = stage
        rank_l.save()
        return self.create_client(u)

    def generate_new_basic_campaign(self, name, lang=None, countries=None):
        l = lang
        if not l:
            l = self.lang
        c = countries
        if not c:
            c = [self.country]

        campaign = Campaign.objects.create(name=name, language=l)
        campaign.countries.set(c)
        default_track = Track.objects.create(
            campaign=campaign,

        )
        campaign.default_track = default_track
        rank = Rank.objects.create(name=f"Default {name} rank",
                                   track=default_track)
        default_track.default_rank = rank
        campaign.save()
        default_track.save()

        chain = Chain.objects.create(
            name=f"Default {name} chain",
            campaign=campaign
        )
        return {
            "campaign": campaign,
            "default_track": default_track,
            "rank": rank,
            "chain": chain
        }

    def setUp(self):
        self.lang = Language.objects.create(
            name="English",
            code="en"
        )
        self.category = Category.objects.create(
            name="Commerce"
        )
        self.country = Country.objects.create(
            name="Vinland"
        )

        basic_data = self.generate_new_basic_campaign("Coca-Cola")

        self.campaign = basic_data['campaign']
        self.campaign.categories.add(self.category)
        self.default_track = basic_data['default_track']
        self.default_rank = basic_data['rank']
        self.chain = basic_data['chain']
        self.initial_stage = TaskStage.objects.create(
            name="Initial",
            x_pos=1,
            y_pos=1,
            chain=self.chain,
            is_creatable=True)
        self.user = CustomUser.objects.create_user(username="test",
                                                   email='test@email.com',
                                                   password='test')

        self.employee = CustomUser.objects.create_user(username="employee",
                                                       email='employee@email.com',
                                                       password='employee')
        self.employee_client = self.create_client(self.employee)

        self.client = self.prepare_client(
            self.initial_stage,
            self.user,
            RankLimit(is_creation_open=True))

    def get_objects(self, endpoint, params=None, client=None, pk=None, headers=None):
        c = client
        if c is None:
            c = self.client
        if pk:
            url = reverse(endpoint, kwargs={"pk": pk})
        else:
            url = reverse(endpoint)
        h = headers if headers else {}
        if params:
            return c.get(url, data=params, **h)
        else:
            return c.get(url, **h)

    def create_task(self, stage, client=None):
        c = client
        task_create_url = reverse(
            "taskstage-create-task",
            kwargs={"pk": stage.pk})
        if c is None:
            c = self.client
        response = c.get(task_create_url)
        return Task.objects.get(id=response.data["id"])

    def request_assignment(self, task, client=None):
        c = client
        request_assignment_url = reverse(
            "task-request-assignment",
            kwargs={"pk": task.pk})
        if c is None:
            c = self.client
        response = c.get(request_assignment_url)
        task = Task.objects.get(id=response.data["id"])
        self.assertEqual(response.wsgi_request.user, task.assignee)
        return task

    def create_initial_task(self):
        return self.create_task(self.initial_stage)

    def create_initial_tasks(self, count):
        return [self.create_initial_task() for x in range(count)]

    def complete_task(self, task, responses=None, client=None, whole_response=False):
        c = client
        if c is None:
            c = self.client
        task_update_url = reverse("task-detail", kwargs={"pk": task.pk})
        if responses:
            args = {"complete": True, "responses": responses}
        else:
            args = {"complete": True}
        response = c.patch(task_update_url, args, format='json')
        if not whole_response and response.data.get('id'):
            return Task.objects.get(id=response.data["id"])
        elif whole_response:
            return response
        else:
            return response

    def update_task_responses(self, task, responses, client=None):
        c = client
        if c is None:
            c = self.client
        task_update_url = reverse("task-detail", kwargs={"pk": task.pk})
        args = {"responses": responses}
        response = c.patch(task_update_url, args, format='json')
        return Task.objects.get(id=response.data["id"])

    def check_task_manual_creation(self, task, stage):
        self.assertEqual(task.stage, stage)
        self.assertFalse(task.complete)
        self.assertFalse(task.force_complete)
        self.assertFalse(task.reopened)
        self.assertIsNone(task.integrator_group)
        self.assertFalse(task.in_tasks.exists())
        self.assertIsNone(task.responses)
        self.assertEqual(len(Task.objects.filter(stage=task.stage)), 1)

    def check_task_auto_creation(self, task, stage, initial_task):
        self.assertEqual(task.stage, stage)
        self.assertFalse(task.complete)
        self.assertFalse(task.force_complete)
        self.assertFalse(task.reopened)
        self.assertIsNone(task.integrator_group)
        self.assertTrue(task.in_tasks.exists())
        self.assertIn(initial_task.id, task.in_tasks.values_list("id", flat=True))
        self.assertTrue(len(task.in_tasks.values_list("id", flat=True)) == 1)
        self.assertEqual(len(Task.objects.filter(stage=task.stage)), 1)

    def check_task_completion(self, task, stage, responses=None):
        self.assertEqual(task.stage, stage)
        self.assertTrue(task.complete)
        self.assertFalse(task.force_complete)
        self.assertFalse(task.reopened)
        self.assertIsNone(task.integrator_group)
        self.assertFalse(task.in_tasks.exists())
        if responses is not None:
            self.assertEqual(task.responses, responses)
        self.assertEqual(len(Task.objects.filter(stage=task.stage)), 1)

    def test_error_creating_for_managers(self):
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "answer": {
                    "title": "Question 1",
                    "type": "string"
                }
            },
            "required": [
                "answer"
            ]
        })
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name="Stage with webhook",
                json_schema=self.initial_stage.json_schema,
            )
        )
        Webhook.objects.create(
            task_stage=second_stage,
            url="https://us-central1-journal-bb5e3.cloudfunctions.net/exercise_translate_word",
            is_triggered=True,
        )
        task = self.create_initial_task()
        task = self.complete_task(task, {"answer": "hello world"})
        self.assertEqual(ErrorGroup.objects.count(), 1)
        self.assertEqual(ErrorItem.objects.count(), 1)

        task = self.create_initial_task()
        task = self.complete_task(task, {"answer": "hello world"})
        self.assertEqual(ErrorGroup.objects.count(), 1)
        self.assertEqual(ErrorItem.objects.count(), 2)

        err_campaigns = Campaign.objects.filter(name=ErrorConstants.ERROR_CAMPAIGN)
        self.assertEqual(err_campaigns.count(), 1)
        self.assertEqual(err_campaigns[0].chains.count(), 1)
        err_tasks = Task.objects.filter(stage__chain__campaign=err_campaigns[0])
        self.assertEqual(err_tasks.count(), 2)

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

