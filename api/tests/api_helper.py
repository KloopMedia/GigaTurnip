import json
from uuid import uuid4

from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIClient
from django.db import connection
from django.conf import settings

from api.models import Rank, RankRecord, CustomUser, RankLimit, Campaign, \
    Track, Chain, Language, Category, Country, TaskStage, Task
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg import openapi
from urllib.parse import urlparse

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
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create info object for Swagger schema
        info = openapi.Info(
            title="GigaTurnip API",
            default_version='v1',
            description="API for GigaTurnip application",
        )
        
        # Generate schema once for all tests
        generator = OpenAPISchemaGenerator(info=info)
        cls.schema = generator.get_schema()

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
        print("setUp")
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
            print(f"\n{self._testMethodName}")
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
                if data['time'] > 0.1:  # Highlight slow queries (>100ms)
                    print(f"\nSlow query ({data['time']:.3f}s):")
                    print(sql)
                # elif data['count'] > 1:
                #     print(f"\nDuplicate query ({data['count']} times, total time: {data['time']:.3f}s):")
                #     print(sql)
                # else:
                #     print(f"\nNormal Query ({data['time']:.3f}s):")
                #     #  print(sql)
        
        super().tearDown()

    def compare_with_swagger_spec(self, url, response_data):
        """Compare response data with Swagger specification"""
        try:
            # Convert Django's URL to Swagger path format
            # e.g., '/api/chain/individuals/' -> '/api/chain/individuals/'
            parsed_url = urlparse(url)
            swagger_path = parsed_url.path

            print("SWAGGER PATH", swagger_path)

            print("\nAvailable Swagger Paths:")
            print("------------------------")
            for path, path_object in sorted(self.schema.paths.items()):
                print(f"\n📍 {path}")
                for method in ['get', 'post', 'put', 'patch', 'delete']:
                    method_spec = getattr(path_object, method, None)
                    if method_spec:
                        print(f"  └── {method.upper()}")
                        # if method_spec.description:
                        #     print(f"      └── Description: {method_spec.description}")
                        # if method_spec.responses:
                        #     print("      └── Responses:")
                        #     for status_code, response in method_spec.responses.items():
                        #         print(f"          └── {status_code}: {response.description}")
            
            print("\nCurrent endpoint:", swagger_path)
            print("------------------------")
            
            # Get the endpoint spec from Swagger
            path_spec = self.schema.paths.get(swagger_path)
            if not path_spec:
                print(f"Warning: No Swagger documentation found for {swagger_path}")
                return
                
            # Get GET method specification
            get_spec = getattr(path_spec, 'get', None)
            if not get_spec:
                print(f"Warning: No GET method documentation found for {swagger_path}")
                return
                
            # Get response specification for 200 status
            response_spec = get_spec.responses.get('200', None)
            if not response_spec or not response_spec.schema:
                print(f"Warning: No 200 response schema found for {swagger_path}")
                return

            # Validate response structure
            self._validate_response(response_data, response_spec.schema, path=swagger_path)
            print("VALIDATED")

        except Exception as e:
            print(f"Warning: Swagger validation failed for {url}: {str(e)}")

    def _validate_response(self, data, spec, path='', parent_path=''):
        """Recursively validate response against schema"""
        current_path = f"{parent_path}.{path}" if parent_path else path
        
        # Handle different types of specifications
        if hasattr(spec, 'properties'):
            # Object validation
            for field_name, field_spec in spec.properties.items():
                if field_name not in data:
                    print(f"Warning: Missing field '{field_name}' in response at {current_path}")
                else:
                    self._validate_response(data[field_name], field_spec, 
                                         path=field_name, parent_path=current_path)
                    
        elif hasattr(spec, 'items'):
            # Array validation
            if not isinstance(data, (list, tuple)):
                print(f"Warning: Expected array but got {type(data)} at {current_path}")
            elif data and spec.items:
                # Validate first item as example
                self._validate_response(data[0], spec.items, 
                                     parent_path=f"{current_path}[0]")
                
        elif hasattr(spec, 'type'):
            # Type validation
            expected_type = spec.type
            if expected_type == 'string' and not isinstance(data, str):
                print(f"Warning: Expected string but got {type(data)} at {current_path}")
            elif expected_type == 'integer' and not isinstance(data, int):
                print(f"Warning: Expected integer but got {type(data)} at {current_path}")
            elif expected_type == 'number' and not isinstance(data, (int, float)):
                print(f"Warning: Expected number but got {type(data)} at {current_path}")
            elif expected_type == 'boolean' and not isinstance(data, bool):
                print(f"Warning: Expected boolean but got {type(data)} at {current_path}")

    def get_objects(self, endpoint, params=None, client=None, pk=None):
        c = client
        if c is None:
            c = self.client
        
        if pk:
            url = reverse(endpoint, kwargs={"pk": pk})
        else:
            url = reverse(endpoint)
            
        if params:
            response = c.get(url, data=params)
        else:
            response = c.get(url)
            
        # Validate response if successful
        if response.status_code == 200:
            try:
                self.compare_with_swagger_spec(url, response.data)
            except Exception as e:
                print(f"Warning: Response validation failed: {str(e)}")
                
        return response

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
