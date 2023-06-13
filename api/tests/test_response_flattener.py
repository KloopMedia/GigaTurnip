import json

from rest_framework import status
from rest_framework.reverse import reverse

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class ResponseFlattenerTest(GigaTurnipTestHelper):

    def test_response_flattener_list_wrong_not_manager(self):
        response = self.get_objects('responseflattener-list', client=self.client)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_response_flattener_list_happy(self):
        self.user.managed_campaigns.add(self.campaign)
        AdminPreference.objects.create(user=self.user, campaign=self.campaign)

        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage)

        response = self.get_objects('responseflattener-list', client=self.client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_flattener_retrieve_wrong_not_manager(self):
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage)

        response = self.get_objects('responseflattener-detail', pk=response_flattener.id, client=self.client)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_response_flattener_retrieve_wrong_not_my_flattener(self):
        self.employee.managed_campaigns.add(self.campaign)
        AdminPreference.objects.create(user=self.employee, campaign=self.campaign)

        new_campaign = Campaign.objects.create(name="Another")
        self.user.managed_campaigns.add(new_campaign)

        AdminPreference.objects.create(user=self.user, campaign=self.campaign)

        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage)

        response = self.get_objects('responseflattener-detail', pk=response_flattener.id, client=self.client)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_response_flattener_retrieve_happy_my_flattener(self):
        self.user.managed_campaigns.add(self.campaign)
        AdminPreference.objects.create(user=self.user, campaign=self.campaign)

        response_flattener = ResponseFlattener.objects.create(
            task_stage=self.initial_stage
        )

        response = self.get_objects('responseflattener-detail', pk=response_flattener.id, client=self.client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_flattener_create_wrong(self):
        resp_flattener = {'task_stage': self.initial_stage.id,}

        response = self.client.post(reverse('responseflattener-list'), data=resp_flattener)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_response_flattener_create_happy(self):
        self.user.managed_campaigns.add(self.campaign)
        AdminPreference.objects.create(user=self.user, campaign=self.campaign)

        resp_flattener = {'task_stage': self.initial_stage.id,}

        response = self.client.post(reverse('responseflattener-list'), data=resp_flattener)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_response_flattener_update_wrong(self):
        resp_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True)
        self.assertTrue(resp_flattener.copy_first_level)

        response = self.client.patch(reverse('responseflattener-detail', kwargs={"pk": resp_flattener.id}),
                                     data={"copy_first_level": False})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp_flattener.copy_first_level)

    def test_response_flattener_update_happy(self):
        self.user.managed_campaigns.add(self.campaign)
        AdminPreference.objects.create(user=self.user, campaign=self.campaign)

        resp_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True)

        response = self.client.patch(reverse('responseflattener-detail', kwargs={"pk": resp_flattener.id}),
                                     {"copy_first_level": False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resp_flattener = ResponseFlattener.objects.get(id=resp_flattener.id)
        self.assertFalse(resp_flattener.copy_first_level)

    def test_response_flattener_create_row(self):
        task = self.create_initial_task()

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        responses = {"column1": "First", "column2": "SecondColumn", "oik": {"uik1": "SecondLayer"}}
        row = {'id': task.id, 'column1': 'First', 'column2': 'SecondColumn', 'oik__(i)uik': 'SecondLayer'}
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(i)uik"])

        task = self.complete_task(task, responses, self.client)

        flattener_row = response_flattener.flatten_response(task)
        self.assertEqual(row, flattener_row)

    def test_response_flattener_flatten_all(self):
        task = self.create_initial_task()

        self.initial_stage.json_schema = '{"properties":{"opening":{"15_c":{}, "16_c":{}, "17_c":{}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["opening"]}'
        self.initial_stage.save()

        answers = {"opening": {"15_c": "secured", "16_c": "no", "17_c": "no"}}
        task.responses = answers
        task.save()
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage,
                                                              flatten_all=True)

        result = response_flattener.flatten_response(task)
        self.assertEqual({"id": task.id, "opening__15_c": "secured", "opening__16_c": "no", "opening__17_c": "no"},
                         result)

    def test_response_flattener_regex_happy(self):
        task = self.create_initial_task()

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        responses = {"column1": "First", "column2": "SecondColumn", "oik": {"uik1": "SecondLayer"}}
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(r)uik[\d]{1,2}"])

        task = self.complete_task(task, responses, self.client)

        result = response_flattener.flatten_response(task)
        self.employee.managed_campaigns.add(self.campaign)
        answer = {"id": task.id, "column1": "First", "column2": "SecondColumn", "oik__(r)uik[\d]{1,2}": "SecondLayer"}

        self.assertEqual(answer, result)

    def test_response_flattener_regex_wrong(self):
        task = self.create_initial_task()

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        responses = {"column1": "First", "column2": "SecondColumn", "oik": {"uik1": "SecondLayer"}}
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(r)ui[\d]{1,2}"])

        task = self.complete_task(task, responses, self.client)

        result = response_flattener.flatten_response(task)
        self.employee.managed_campaigns.add(self.campaign)
        answer = {"id": task.id, "column1": "First", "column2": "SecondColumn"}

        self.assertEqual(answer, result)

    def test_get_response_flattener_success(self):
        task = self.create_initial_task()

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik__uik"]}'
        self.initial_stage.save()

        responses = {"column1": "First", "column2": "SecondColumn", "oik": {"uik1": "SecondLayer"}}
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(i)uik", "dfasdf", "dfasdfasd"])

        task = self.complete_task(task, responses, self.client)

        self.employee.managed_campaigns.add(self.campaign)
        new_client = self.create_client(self.employee)

        params = {"response_flattener": response_flattener.id, "stage": self.initial_stage.id}
        response = self.get_objects("responseflattener-csv", params=params, client=new_client, pk=response_flattener.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_flattener_unique_success(self):
        task = self.create_initial_task()

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        responses = {"column1": "First", "column2": "SecondColumn", "oik": {"uik1": "SecondLayer"}}
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(i)uik"])
        response_flattener_second = ResponseFlattener.objects.get_or_create(task_stage=self.initial_stage)

        self.assertEqual(ResponseFlattener.objects.count(), 1)

        task = self.complete_task(task, responses, self.client)

        self.employee.managed_campaigns.add(self.campaign)
        new_client = self.create_client(self.employee)

        params = {"response_flattener": response_flattener.id, "stage": self.initial_stage.id}
        response = self.get_objects("responseflattener-csv", params=params, client=new_client, pk=response_flattener.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_flattener_get_tasks_success(self):
        tasks = self.create_initial_tasks(5)

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        responses = {"column2": "SecondColumn", "oik": {"uik1": "SecondLayer"}}
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, flatten_all=True)

        for i, t in enumerate(tasks):
            task = self.complete_task(t, responses, self.client)
            tasks[i] = task

        self.employee.managed_campaigns.add(self.campaign)
        new_client = self.create_client(self.employee)

        params = {"response_flattener": response_flattener.id}
        response = self.get_objects("responseflattener-csv", params=params, client=new_client, pk=response_flattener.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        r = {"column2": "SecondColumn", "oik__uik1": "SecondLayer"}
        for t in tasks:
            r["id"] = t.id
            self.assertEqual(r, response_flattener.flatten_response(t))

    def test_get_response_flattener_copy_whole_response_success(self):
        task = self.create_task(self.initial_stage)

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        responses = {"column1": "First", "column2": "SecondColumn", "oik": {"uik1": {"uik1": [322, 123, 23]}}}
        task.responses = responses
        task.save()
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, flatten_all=True)

        result = {'id': task.id, 'column1': 'First', 'column2': 'SecondColumn', 'oik__uik1__uik1': [322, 123, 23]}
        self.assertEqual(response_flattener.flatten_response(task), result)

    def test_get_response_flattener_generate_file_url(self):

        task = self.create_task(self.initial_stage)
        self.initial_stage.ui_schema = '{"AAA":{"ui:widget":"customfile"},"ui:order": ["AAA"]}'
        self.initial_stage.json_schema = '{"properties":{"AAA": {"AAA":{}}}}'
        self.initial_stage.save()

        responses = {"AAA": '{"i":"public/img.jpg"}'}
        task.responses = responses
        task.save()
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, flatten_all=True)
        flattened_task = response_flattener.flatten_response(task)
        self.assertEqual(flattened_task, {"id": task.id,
                                          "AAA": "https://storage.cloud.google.com/gigaturnip-b6b5b.appspot.com/public/img.jpg?authuser=1"})

    def test_get_response_flattener_order_columns(self):

        task = self.create_task(self.initial_stage)
        self.initial_stage.ui_schema = '{"ui:order": [ "col2", "col3", "col1"]}'
        self.initial_stage.json_schema = '{"properties":{"col1": {"col1_1":{}}, "col2": {"col2_1":{}}, "col3": {"properties": {"d": {"properties": {"d": {}}}}}}}'
        self.initial_stage.save()

        responses = {"col1": "SecondColumn", "col2": "First", "col3": {"d": {"d": 122}}}
        task.responses = responses
        task.save()
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, flatten_all=True)

        ordered_columns = response_flattener.ordered_columns()
        self.assertEqual(ordered_columns, ["id", "col2", "col3__d__d", "col1"])

        # Testing system fields
        response_flattener.copy_system_fields = True
        response_flattener.save()
        ordered_columns = response_flattener.ordered_columns()
        system_columns = ["id", 'created_at', 'updated_at', 'assignee_id', 'stage_id', 'case_id',
                          'integrator_group', 'complete', 'force_complete', 'reopened',
                          'internal_metadata', 'start_period', 'end_period',
                          'schema', 'ui_schema']
        responses_fields = ["col2", "col3__d__d", "col1"]

        all_columns = system_columns + responses_fields
        self.assertEqual(ordered_columns, all_columns)
        flattened_task = response_flattener.flatten_response(task)
        for i in system_columns:
            self.assertEqual(task.__getattribute__(i), flattened_task[i])

    def test_response_flattener_with_previous_names(self):
        tasks = self.create_initial_tasks(5)
        self.employee.managed_campaigns.add(self.campaign)
        new_client = self.create_client(self.employee)

        self.initial_stage.json_schema = '{"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}'
        self.initial_stage.ui_schema = '{"ui:order": ["column2", "column1", "oik"]}'
        self.initial_stage.save()

        responses = {"column2": "SecondColumn", "oik": {"uik1": "SecondLayer"}}
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, flatten_all=True)

        for i, t in enumerate(tasks[:3]):
            task = self.complete_task(t, responses, self.client)
            tasks[i] = task

        for i, t in enumerate(tasks[3:]):
            responses['another'] = "field not in schema"
            task = self.complete_task(t, responses, self.client)
            tasks[i + 3] = task

        params = {"response_flattener": response_flattener.id}
        response = self.get_objects("responseflattener-csv", params=params, client=new_client, pk=response_flattener.id)
        columns = response.content.decode().split("\r\n", 1)[0].split(',')
        self.assertEqual(columns, ['id', 'column2', 'column1', 'oik__uik1', 'description'])

        response_flattener.columns = ['another']
        response_flattener.save()

        response = self.get_objects("responseflattener-csv", params=params, client=new_client, pk=response_flattener.id)
        columns = response.content.decode().split("\r\n", 1)[0].split(',')
        self.assertEqual(columns, ['id', 'another', 'column2', 'column1', 'oik__uik1'])

    def test_get_response_flattener_fail(self):
        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(i)uik"])

        new_client = self.create_client(self.employee)
        params = {"response_flattener": response_flattener.id, "stage": self.initial_stage.id}
        response = self.get_objects("responseflattener-csv", params=params, client=new_client, pk=response_flattener.id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_response_flattener_not_found(self):

        response_flattener = ResponseFlattener.objects.create(task_stage=self.initial_stage, copy_first_level=True,
                                                              columns=["oik__(i)uik"])

        response = self.get_objects("responseflattener-csv", pk=response_flattener.id + 111)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
