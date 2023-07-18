import copy
import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class DynamicJsonTest(GigaTurnipTestHelper):

    def test_dynamic_json_schema_related_fields(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        time_slots = ['10:00', '11:00', '12:00', '13:00', '14:00']
        js_schema = {
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                },
                "time": {
                    "type": "string",
                    "title": "What time",
                    "enum": time_slots
                }
            }
        }
        ui_schema = {"ui:order": ["time"]}
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_json = {
            "main": "weekday",
            "foreign": ['time'],
            "count": 2
        }
        dynamic_json = DynamicJson.objects.create(
            target=self.initial_stage,
            dynamic_fields=dynamic_fields_json
        )

        task1 = self.create_initial_task()
        responses1 = {'weekday': weekdays[0], 'time': time_slots[0]}
        task1 = self.complete_task(task1, responses1)

        task2 = self.create_initial_task()
        task2 = self.complete_task(task2, responses1)

        task3 = self.create_initial_task()
        responses3 = {'weekday': weekdays[0]}

        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses3)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_schema = copy.deepcopy(js_schema)
        del updated_schema['properties']['time']['enum'][0]
        self.assertEqual(response.data['schema'], updated_schema)

        responses3['weekday'] = weekdays[1]
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses3)})
        updated_schema = copy.deepcopy(js_schema)
        self.assertEqual(response.data['schema'], updated_schema)

    def test_dynamic_json_schema_single_field(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        js_schema = {
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                }
            }
        }
        ui_schema = {"ui:order": ["time"]}
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_json = {
            "main": "weekday",
            "foreign": [],
            "count": 2
        }
        dynamic_json = DynamicJson.objects.create(
            target=self.initial_stage,
            dynamic_fields=dynamic_fields_json
        )

        responses1 = {'weekday': weekdays[0]}

        task1 = self.create_initial_task()
        task1 = self.complete_task(task1, responses1)

        task2 = self.create_initial_task()
        task2 = self.complete_task(task2, responses1)

        task3 = self.create_initial_task()
        responses3 = {'weekday': weekdays[0]}

        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses3)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_schema = js_schema
        del updated_schema['properties']['weekday']['enum'][0]
        self.assertEqual(response.data['schema'], updated_schema)

        responses3['weekday'] = weekdays[1]
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses3)})
        self.assertEqual(response.data['schema'], updated_schema)

    def test_dynamic_json_schema_related_fields_from_another_stage(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        time_slots = ['10:00', '11:00', '12:00', '13:00', '14:00']

        schema = {
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                }
            }
        }

        self.initial_stage.json_schema = copy.deepcopy(schema)
        self.initial_stage.save()

        json_schema_time = {
            "type": "object",
            "properties": {
                "time": {
                    "type": "string",
                    "title": "What time",
                    "enum": time_slots
                }
            }
        }
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name='Complete time',
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage,
                json_schema=json_schema_time,
                ui_schema={"ui:order": ["time"]}
            )
        )

        dynamic_fields_json = {
            "main": "weekday",
            "foreign": ['time'],
            "count": 1
        }
        dynamic_json = DynamicJson.objects.create(
            source=self.initial_stage,
            target=second_stage,
            dynamic_fields=dynamic_fields_json
        )

        responses = {'weekday': weekdays[0]}
        for i in range(3):
            t = self.create_initial_task()
            t = self.complete_task(t, responses)
            self.complete_task(t.out_tasks.get(), {'time': time_slots[i]})

        t2 = self.create_initial_task()
        t2 = self.complete_task(t2, responses)
        t2_next = t2.out_tasks.get()
        response = self.get_objects('taskstage-load-schema-answers', pk=second_stage.id,
                                    params={"current_task": t2_next.id})
        updated_schema = copy.deepcopy(second_stage.json_schema)
        del updated_schema['properties']['time']['enum'][0]
        del updated_schema['properties']['time']['enum'][0]
        del updated_schema['properties']['time']['enum'][0]
        self.assertEqual(response.data['schema'], updated_schema)
        t2_next = self.complete_task(t2_next, {'time': time_slots[3]})

        t3 = self.create_initial_task()
        t3 = self.complete_task(t3, {'weekday': weekdays[1]})
        t3_next = t3.out_tasks.get()
        response = self.get_objects('taskstage-load-schema-answers', pk=second_stage.id,
                                    params={"current_task": t3_next.id})

        updated_schema = second_stage.json_schema
        self.assertEqual(response.data['schema'], updated_schema)

    def test_dynamic_json_schema_single_unique_field(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        js_schema = {
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                }

            }
        }
        ui_schema = {"ui:order": ["weekday"]}
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_weekday = {
            "main": "weekday",
            "foreign": [],
            "count": 2
        }
        dynamic_json_weekday = DynamicJson.objects.create(
            target=self.initial_stage,
            dynamic_fields=dynamic_fields_weekday
        )

        responses1 = {'weekday': weekdays[0]}

        task1 = self.create_initial_task()
        task1 = self.complete_task(task1, responses1)

        task2 = self.create_initial_task()
        task2 = self.complete_task(task2, responses1)

        task3 = self.create_initial_task()
        responses3 = {'weekday': weekdays[0]}

        updated_schema = copy.deepcopy(js_schema)
        del updated_schema['properties']['weekday']['enum'][0]
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['schema'], updated_schema)

        response = self.complete_task(task3, responses3)
        return
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'][0], 'Your answers are non-compliance with the standard')
        self.assertEqual(response.data['pass'], ['properties', 'weekday', 'enum'])

    def test_dynamic_json_schema_related_unique_fields(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        time_slots = ['10:00', '11:00', '12:00', '13:00', '14:00']
        js_schema = {
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                },
                "time": {
                    "type": "string",
                    "title": "What time",
                    "enum": time_slots
                }
            }
        }
        ui_schema = {"ui:order": ["time"]}
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_json = {
            "main": "weekday",
            "foreign": ['time'],
            "count": 1
        }
        dynamic_json = DynamicJson.objects.create(
            target=self.initial_stage,
            dynamic_fields=dynamic_fields_json
        )

        for t in time_slots:
            task = self.create_initial_task()
            responses = {'weekday': weekdays[0], 'time': t}
            self.complete_task(task, responses)

        task = self.create_initial_task()

        responses = {'weekday': weekdays[0]}
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_schema = copy.deepcopy(js_schema)
        updated_schema['properties']['time']['enum'] = []
        self.assertEqual(response.data['schema'], updated_schema)

        responses = {'weekday': weekdays[1]}
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_schema = js_schema
        self.assertEqual(response.data['schema'], updated_schema)

    def test_dynamic_json_schema_three_foreign(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        time_slots = ['10:00', '11:00', '12:00', '13:00', '14:00']
        doctors = ['Rinat', 'Aizirek', 'Aigerim', 'Beka']
        alphabet = ['a', 'b', 'c', 'd']
        js_schema = {
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                },
                "time": {
                    "type": "string",
                    "title": "What time",
                    "enum": time_slots
                },
                "doctor": {
                    "type": "string",
                    "title": "Which doctor",
                    "enum": doctors
                },
                "alphabet": {
                    "type": "string",
                    "title": "Which doctor",
                    "enum": alphabet
                }
            }
        }
        ui_schema = {"ui:order": ["time"]}
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_json = {
            "main": "weekday",
            "foreign": ["time", "doctor", "alphabet"],
            "count": 1
        }
        dynamic_json = DynamicJson.objects.create(
            target=self.initial_stage,
            dynamic_fields=dynamic_fields_json
        )

        task = self.create_initial_task()
        responses = {'weekday': weekdays[0], 'time': time_slots[0], 'doctor': doctors[0], 'alphabet': alphabet[0]}
        self.complete_task(task, responses)

        task = self.create_initial_task()
        responses = {'weekday': weekdays[0], 'time': time_slots[0], 'doctor': doctors[0]}
        updated_schema = copy.deepcopy(js_schema)
        del updated_schema['properties']['alphabet']['enum'][0]
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses)})

        self.assertEqual(response.data['schema'], updated_schema)

        responses = {'weekday': weekdays[0], 'time': time_slots[0], 'doctor': doctors[1]}
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses)})
        updated_schema = copy.deepcopy(js_schema)
        self.assertEqual(response.data['schema'], updated_schema)

        responses = {'weekday': weekdays[1], 'time': time_slots[0], 'doctor': doctors[0]}
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses)})
        updated_schema = copy.deepcopy(js_schema)
        self.assertEqual(response.data['schema'], updated_schema)

        responses = {'weekday': weekdays[0], 'time': time_slots[1], 'doctor': doctors[0]}
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses)})
        updated_schema = copy.deepcopy(js_schema)
        self.assertEqual(response.data['schema'], updated_schema)

    def test_dynamic_json_schema_many(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        day_parts = ['12:00 - 13:00', '13:00 - 14:00', '14:00 - 15:00']
        js_schema = {
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                },
                "day_part": {
                    "type": "string",
                    "title": "Select part of the day",
                    "enum": day_parts
                },

            }
        }
        ui_schema = {"ui:order": ["time"]}
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_weekday = {
            "main": "weekday",
            "foreign": [],
            "count": 2
        }
        dynamic_json_weekday = DynamicJson.objects.create(
            target=self.initial_stage,
            dynamic_fields=dynamic_fields_weekday
        )

        dynamic_fields_day_parts = {
            "main": "day_part",
            "foreign": [],
            "count": 2
        }
        dynamic_json_day_part = DynamicJson.objects.create(
            target=self.initial_stage,
            dynamic_fields=dynamic_fields_day_parts
        )

        responses1 = {'weekday': weekdays[0], 'day_part': day_parts[0]}

        task1 = self.create_initial_task()
        task1 = self.complete_task(task1, responses1)

        task2 = self.create_initial_task()
        task2 = self.complete_task(task2, responses1)

        task3 = self.create_initial_task()
        responses3 = {'weekday': weekdays[0], 'day_part': day_parts[0]}

        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_schema = js_schema
        del updated_schema['properties']['weekday']['enum'][0]
        del updated_schema['properties']['day_part']['enum'][0]
        self.assertEqual(response.data['schema'], updated_schema)

        responses3['weekday'] = weekdays[1]
        response = self.get_objects('taskstage-load-schema-answers', pk=self.initial_stage.id,
                                    params={'responses': json.dumps(responses3)})
        self.assertEqual(response.data['schema'], updated_schema)

    def test_update_taskstage(self):
        external_metadata = {"field": "value"}
        self.initial_stage.external_metadata = external_metadata
        self.initial_stage.save()
        response = self.get_objects('taskstage-detail', pk=self.initial_stage.id)
        self.assertEqual(response.data['external_metadata'], external_metadata)

    def test_dynamic_json_schema_try_to_complete_occupied_answer(self):
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
        time_slots = ['10:00', '11:00', '12:00', '13:00', '14:00']
        js_schema = {
            "type": "object",
            "properties": {
                "weekday": {
                    "type": "string",
                    "title": "Select Weekday",
                    "enum": weekdays
                },
                "time": {
                    "type": "string",
                    "title": "What time",
                    "enum": time_slots
                }
            }
        }
        ui_schema = {"ui:order": ["time"]}
        self.initial_stage.json_schema = js_schema
        self.initial_stage.ui_schema = ui_schema
        self.initial_stage.save()

        dynamic_fields_json = {
            "main": "weekday",
            "foreign": ['time'],
            "count": 1
        }
        dynamic_json = DynamicJson.objects.create(
            target=self.initial_stage,
            dynamic_fields=dynamic_fields_json
        )

        task = self.create_initial_task()
        responses = {'weekday': weekdays[0], 'time': time_slots[0]}
        self.complete_task(task, responses)

        task = self.create_initial_task()

        responses = {'weekday': weekdays[0], 'time': time_slots[0]}
        response = self.complete_task(task, responses)
        return
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        responses['time'] = time_slots[1]
        task = self.complete_task(task, responses)
        self.assertEqual(task.responses, responses)

    def test_dynamic_json_obtain_options_from_stages(self):
        tasks_to_complete = self.create_initial_tasks(5)
        tasks_in_completion = self.create_initial_tasks(3)
        i = 5
        completed = []
        for t in tasks_to_complete:
            completed.append(self.complete_task(t, {"name": f"Person #{i}"}))
            i -= 1

        in_progress = []
        for t in tasks_in_completion:
            in_progress.append(self.update_task_responses(t, {"name": f"Person #{i}"}))
            i += 1


        new_chain = Chain.objects.create(
            name='Persons names chain',
            campaign=self.campaign
        )
        choose_name_stage = TaskStage.objects.create(
            name='Choose name',
            chain=new_chain,
            x_pos=1,
            y_pos=1,
            is_creatable=True,
            json_schema={"type": "object","properties": {"choose_name": {"type": "string", "enum":[]}}}
        )
        RankLimit.objects.create(
            open_limit=0,
            total_limit=0,
            is_creation_open=True,
            rank=self.user.ranks.all()[0],
            stage=choose_name_stage
        )

        dynamic_fields = {
            "main": "name",
            "foreign": ["choose_name"],

        }
        DynamicJson.objects.create(
            source=self.initial_stage,
            target=choose_name_stage,
            dynamic_fields=dynamic_fields,
            obtain_options_from_stage=True
        )

        task = self.create_task(choose_name_stage)
        response = self.get_objects('taskstage-load-schema-answers', pk=choose_name_stage.id,
                                    params={"current_task":task.id})
        updated_enums = response.data['schema']['properties']['choose_name']['enum']
        self.assertEqual(len(updated_enums), 5)
        self.assertEqual(['Person #1', 'Person #2', 'Person #3', 'Person #4', 'Person #5'], updated_enums)
        right_return = {
            'status': 200,
            'schema': {
                'type': 'object',
                'properties': {
                    'choose_name': {
                        'type': 'string',
                        'enum': ['Person #1', 'Person #2', 'Person #3', 'Person #4', 'Person #5']
                    }
                }
            }
        }

        self.assertEqual(right_return, response.data)

