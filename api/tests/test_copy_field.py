import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class CopyFieldTest(GigaTurnipTestHelper):
    def test_copy_field(self):
        id_chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        schema = {"type": "object","properties": {"name": {"type": "string"},"phone": {"type": "integer"},"address": {"type": "string"}}}
        id_stage = TaskStage.objects.create(
            name="ID",
            x_pos=1,
            y_pos=1,
            chain=id_chain,
            json_schema=schema,
            is_creatable=True)
        self.client = self.prepare_client(
            id_stage,
            self.user,
            RankLimit(is_creation_open=True))
        task1 = self.create_task(id_stage)

        task1 = self.complete_task(
            task1,
            {"name": "rinat", "phone": 2, "address": "ssss"}
        )

        CopyField.objects.create(
            copy_by="US",
            task_stage=self.initial_stage,
            copy_from_stage=id_stage,
            fields_to_copy="name->name phone->phone1 absent->absent")

        task = self.create_initial_task()

        self.assertEqual(len(task.responses), 2)
        self.assertEqual(task.responses["name"], task1.responses["name"])
        self.assertEqual(task.responses["phone1"], task1.responses["phone"])

    def test_copy_field_with_no_source_task(self):
        id_chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        id_stage = TaskStage.objects.create(
            name="ID",
            x_pos=1,
            y_pos=1,
            chain=id_chain,
            is_creatable=True)

        CopyField.objects.create(
            copy_by="US",
            task_stage=self.initial_stage,
            copy_from_stage=id_stage,
            fields_to_copy="name->name phone->phone1 absent->absent")

        task = self.create_initial_task()

        self.check_task_manual_creation(task, self.initial_stage)

    def test_copy_field_fail_for_different_campaigns(self):
        campaign = Campaign.objects.create(name="Campaign")
        id_chain = Chain.objects.create(name="Chain", campaign=campaign)
        schema = {"type": "object","properties": {"name": {"type": "string"},"phone": {"type": "integer"},"address": {"type": "string"}}}
        id_stage = TaskStage.objects.create(
            name="ID",
            x_pos=1,
            y_pos=1,
            json_schema=schema,
            chain=id_chain,
            is_creatable=True)
        self.client = self.prepare_client(
            id_stage,
            self.user,
            RankLimit(is_creation_open=True))
        task1 = self.create_task(id_stage)
        task2 = self.create_task(id_stage)
        task3 = self.create_task(id_stage)

        correct_responses = {"name": "kloop", "phone": 3, "address": "kkkk"}

        task1 = self.complete_task(
            task1,
            {"name": "rinat", "phone": 2, "address": "ssss"})
        task3 = self.complete_task(
            task3,
            {"name": "ri", "phone": 5, "address": "oooo"})
        task2 = self.complete_task(task2, correct_responses)

        CopyField.objects.create(
            copy_by="US",
            task_stage=self.initial_stage,
            copy_from_stage=id_stage,
            fields_to_copy="name->name phone->phone1 absent->absent")

        task = self.create_initial_task()

        self.assertIsNone(task.responses)

    def test_copy_field_by_case(self):
        self.initial_stage.json_schema = {"type": "object","properties": {"name": {"type": "string"},"phone": {"type": "integer"},"address": {"type": "string"}}}
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(
            TaskStage(
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage)
        )
        third_schema = {"type": "object","properties": {"name": {"type": "string"},"phone1": {"type": "integer"},"absent": {"type": "string"}}}
        third_stage = second_stage.add_stage(
            TaskStage(
                assign_user_by=TaskStageConstants.STAGE,
                json_schema=third_schema,
                assign_user_from_stage=self.initial_stage)
        )
        CopyField.objects.create(
            copy_by=CopyFieldConstants.CASE,
            task_stage=third_stage,
            copy_from_stage=self.initial_stage,
            fields_to_copy="name->name phone->phone1 absent->absent")

        task = self.create_initial_task()
        correct_responses = {"name": "kloop", "phone": 3, "address": "kkkk"}
        task = self.complete_task(task, responses=correct_responses)
        task_2 = task.out_tasks.all()[0]
        self.complete_task(task_2)
        task_3 = task_2.out_tasks.all()[0]

        self.assertEqual(Task.objects.count(), 3)
        self.assertEqual(len(task_3.responses), 2)
        self.assertEqual(task_3.responses["name"], task.responses["name"])
        self.assertEqual(task_3.responses["phone1"], task.responses["phone"])

    def test_copy_field_by_case_copy_all(self):
        self.initial_stage.json_schema = {"type": "object","properties": {"name": {"type": "string"},"phone": {"type": "integer"},"address": {"type": "string"}}}
        self.initial_stage.save()
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage)
        )
        third_schema = {"type": "object","properties": {"name": {"type": "string"},"phone": {"type": "integer"},"address": {"type": "string"}}}
        third_stage = second_stage.add_stage(
            TaskStage(
                assign_user_by=TaskStageConstants.STAGE,
                json_schema=third_schema,
                assign_user_from_stage=self.initial_stage)
        )
        CopyField.objects.create(
            copy_by=CopyFieldConstants.CASE,
            task_stage=third_stage,
            copy_from_stage=self.initial_stage,
            copy_all=True)

        task = self.create_initial_task()
        correct_responses = {"name": "kloop", "phone": 3, "addr": "kkkk"}
        task = self.complete_task(task, responses=correct_responses)
        task_2 = task.out_tasks.all()[0]
        self.complete_task(task_2)
        task_3 = task_2.out_tasks.all()[0]
        self.assertEqual(task_3.responses, task.responses)
