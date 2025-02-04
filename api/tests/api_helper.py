import json
from uuid import uuid4

from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIClient
from django.db import connection
from django.conf import settings

from api.models import Rank, RankRecord, CustomUser, RankLimit, Campaign, \
    Track, Chain, Language, Category, Country, TaskStage, Task

def to_json(string):
    return json.loads(string)

def get_schema():
    schema = {
    "type": "object",
    "properties": {
        "answer": {
            "title": "Question 1",
            "type": "string"
        },
        "answer2": {
            "title": "Question 2",
            "type": "string"
        },
        "answer3": {
            "title": "Question 3",
            "type": "string"
        },
        "answer4": {
            "title": "Question 4",
            "type": "string"
        }
    },
    "required": ["answer", "answer2", "answer3", "answer4"]
}
    return schema

class GigaTurnipTestHelper(APITestCase):

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
            l = [self.lang]
        c = countries
        if not c:
            c = [self.country]

        campaign = Campaign.objects.create(name=name, visible=True)
        campaign.languages.add(*l)
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
        print(f"\n{self._testMethodName}")
        # Enable query logging for tests
        settings.DEBUG = True
        # Clear any queries from setup
        #reset_queries()
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

    def tearDown(self):
        # Print query statistics after each test
        queries = len(connection.queries)
        if queries > 0:
            print(f"Number of queries: {queries}")
            # Track duplicate queries
            duplicates = {}
            for query in connection.queries:
                sql = query['sql']
                if sql in duplicates:
                    duplicates[sql]['count'] += 1
                    duplicates[sql]['time'] += float(query['time'])
                else:
                    duplicates[sql] = {'count': 1, 'time': float(query['time'])}
            
            # Print duplicates and slow queries
            for sql, data in duplicates.items():
                if data['time'] > 0.001:  # Highlight slow queries (>100ms)
                    print(f"\nSlow query ({data['time']:.3f}s):")
                    print(sql)
                elif data['count'] > 1:
                    print(f"\nDuplicate query ({data['count']} times, total time: {data['time']:.3f}s):")
                    #print(sql)
                # else:
                #     print(f"\nNormal Query ({data['time']:.3f}s):")
                    #print(sql)§
        
        super().tearDown()

    def get_objects(self, endpoint, params=None, client=None, pk=None):
        c = client
        if c is None:
            c = self.client
        if pk:
            url = reverse(endpoint, kwargs={"pk": pk})
        else:
            url = reverse(endpoint)
        print("URL: ", url)
        if params:
            return c.get(url, data=params)
        else:
            return c.get(url)

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
        self.assertEqual(task.responses, {})
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
