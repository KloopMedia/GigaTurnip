import json

from rest_framework import status

from rest_framework.test import APITestCase, APIClient

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class TaskStageTest(GigaTurnipTestHelper):

    def test_delete_stage_assign_by_ST(self):
        second_stage = self.initial_stage.add_stage(TaskStage(
            name="second_stage",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage
        ))
        third_stage = second_stage.add_stage(TaskStage(
            name="third stage",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=second_stage
        ))

        self.assertEqual(TaskStage.objects.count(), 3)
        self.initial_stage.delete()
        self.assertEqual(TaskStage.objects.count(), 2)

    def test_open_previous_option(self):
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage,
                allow_go_back=True
            ))
        initial_task = self.create_initial_task()
        self.complete_task(initial_task, responses={})

        second_task = Task.objects.get(
            stage=second_stage,
            case=initial_task.case)
        self.assertEqual(initial_task.assignee, second_task.assignee)

        response = self.get_objects("task-open-previous", pk=second_task.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], initial_task.id)

        initial_task = Task.objects.get(id=initial_task.id)
        second_task = Task.objects.get(id=second_task.id)

        self.assertTrue(second_task.complete)
        self.assertTrue(initial_task.reopened)
        self.assertFalse(initial_task.complete)
        self.assertEqual(Task.objects.all().count(), 2)

        initial_task = self.complete_task(initial_task)

        second_task = Task.objects.get(id=second_task.id)

        self.assertTrue(initial_task.complete)
        self.assertEqual(Task.objects.all().count(), 2)
        self.assertFalse(second_task.complete)
        self.assertTrue(second_task.reopened)

    def test_public_stages(self):
        new_stage = self.initial_stage.add_stage(
            TaskStage(
                name="Publich stage",
                json_schema=self.initial_stage.json_schema,
                ui_schema=self.initial_stage.ui_schema,
                is_public=True,
            )
        )
        client = APIClient()
        response = self.get_objects("taskstage-public", client=client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], new_stage.id)

    def test_stage_user_relevant_paginate(self):
        response = self.get_objects('taskstage-user-relevant')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(json.loads(response.content).keys()),
            {"count", "next", "previous", "results"}
        )

    def test_stages_by_highest_ranks(self):
        chain_low_priority = Chain.objects.create(
            campaign=self.campaign,
            name="Low priority chain",
            is_individual=True
        )
        chain_middle_priority = Chain.objects.create(
            campaign=self.campaign,
            name="Middle priority chain",
            is_individual=True
        )
        chain_guru_priority = Chain.objects.create(
            campaign=self.campaign,
            name="Guru priority chain",
            is_individual=True
        )

        task_stage_low = TaskStage.objects.create(
            name="Low stage",
            x_pos=1,
            y_pos=1,
            chain=chain_low_priority,
            is_creatable=True)
        task_stage_middle = TaskStage.objects.create(
            name="Middle stage",
            x_pos=1,
            y_pos=1,
            chain=chain_middle_priority,
            is_creatable=True)
        task_stage_guru = TaskStage.objects.create(
            name="Guru stage",
            x_pos=1,
            y_pos=1,
            chain=chain_guru_priority,
            is_creatable=True)

        new_track = Track.objects.create(campaign=self.campaign)

        self.prepare_client(task_stage_low, self.user,
                            RankLimit(is_creation_open=True),
                            priority=1)
        self.prepare_client(task_stage_middle, self.user,
                            RankLimit(is_creation_open=True),
                            track=new_track, priority=2)
        self.prepare_client(task_stage_guru, self.user,
                            RankLimit(is_creation_open=True),
                            track=new_track, priority=3)

        response = self.get_objects("taskstage-user-relevant")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 1)

        response = self.get_objects("taskstage-user-relevant")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 1)

        params = {"by_highest_ranks": "true"}
        response = self.get_objects("taskstage-user-relevant", params=params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 0)
        # self.assertEqual([task_stage_low.id, task_stage_guru.id],
        #                  sorted([i["id"] for i in content["results"]]))

    def test_stages_by_ranks(self):
        chain_low_priority = Chain.objects.create(
            campaign=self.campaign,
            name="Low priority chain",
            is_individual=True
        )
        chain_middle_priority = Chain.objects.create(
            campaign=self.campaign,
            name="Middle priority chain",
            is_individual=True
        )
        chain_guru_priority = Chain.objects.create(
            campaign=self.campaign,
            name="Guru priority chain",
            is_individual=True
        )

        task_stage_low = TaskStage.objects.create(
            name="Low stage",
            x_pos=1,
            y_pos=1,
            chain=chain_low_priority,
            is_creatable=True)
        task_stage_middle = TaskStage.objects.create(
            name="Middle stage",
            x_pos=1,
            y_pos=1,
            chain=chain_middle_priority,
            is_creatable=True)
        task_stage_guru = TaskStage.objects.create(
            name="Guru stage",
            x_pos=1,
            y_pos=1,
            chain=chain_guru_priority,
            is_creatable=True)

        new_track = Track.objects.create(campaign=self.campaign)

        self.prepare_client(task_stage_low, self.user,
                            RankLimit(is_creation_open=True),
                            priority=1)
        self.prepare_client(task_stage_middle, self.user,
                            RankLimit(is_creation_open=True),
                            track=new_track, priority=2)
        self.prepare_client(task_stage_guru, self.user,
                            RankLimit(is_creation_open=True),
                            track=new_track, priority=3)

        response = self.get_objects("taskstage-user-relevant")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 1)

        guru_rank = Rank.objects.filter(track=new_track,
                                        name=task_stage_guru.name).first()

        params = {"ranks": guru_rank.id}
        response = self.get_objects("taskstage-user-relevant", params=params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 0)
        # self.assertEqual([task_stage_guru.id],
        #                  sorted([i["id"] for i in content["results"]]))

        middle_rank = Rank.objects.filter(track=new_track,
                                          name=task_stage_middle.name).first()

        params = {"ranks": middle_rank.id}
        response = self.get_objects("taskstage-user-relevant", params=params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 0)
        # self.assertEqual([task_stage_middle.id],
        #                  sorted([i["id"] for i in content["results"]]))

    def test_task_stage_serializers_by_flag(self):
        self.user.managed_campaigns.add(self.campaign)
        response = self.get_objects('taskstage-list')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'],
                         self.initial_stage.id)
        ranks = response.data['results'][0]['ranks']
        self.assertEqual(len(ranks), self.initial_stage.ranks.count())
        self.assertEqual(ranks, list(
            self.initial_stage.ranks.values_list('id', flat=True)))

        image = '<i class="fa-solid fa-filter"></i>'
        rank = self.initial_stage.ranks.filter(
            id=self.initial_stage.ranks.all()[0].id).update(avatar=image)
        response = self.get_objects('taskstage-list',
                                    params={"ranks_avatars": "yes"})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'],
                         self.initial_stage.id)
        ranks = response.data['results'][0]['ranks']
        stage_rank = self.initial_stage.ranks.all()[0]
        self.assertEqual(len(ranks), self.initial_stage.ranks.count())
        self.assertEqual(ranks[0]['avatar'], stage_rank.avatar)

    def test_add_stage(self):
        self.initial_stage.add_stage(ConditionalStage()).add_stage(TaskStage())
        stages_queryset = Stage.objects.filter(chain=self.chain)
        self.assertEqual(len(stages_queryset), 3)

    def test_copy_input(self):
        schema = {"type": "object", "properties": {
            "name": {"type": "string"}, "phone": {"type": "integer"},
            "address": {"type": "string"}}}
        self.initial_stage.json_schema = json.dumps(schema)
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(
            TaskStage(
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage,
                copy_input=True)
        )
        task = self.create_initial_task()
        correct_responses = {"name": "kloop", "phone": 3, "address": "kkkk"}
        task = self.complete_task(task, responses=correct_responses)
        task_2 = task.out_tasks.all()[0]

        self.assertEqual(task_2.responses, task.responses)

    def test_get_tasks_stages_selectable(self):
        second_stage = self.initial_stage.add_stage(TaskStage())
        self.client = self.prepare_client(second_stage, self.user)
        task_1 = self.create_initial_task()
        task_1 = self.complete_task(task_1)
        task_2 = task_1.out_tasks.all()[0]
        response = self.get_objects("task-user-selectable")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], task_2.id)

        response = self.get_objects("taskstage-selectable", client=self.client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(second_stage.id, response.data["results"][0]["id"])

        response_assign = self.get_objects('task-request-assignment',
                                           pk=task_2.id)
        self.assertEqual(response_assign.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.tasks.count(), 2)

        response = self.get_objects("taskstage-selectable", client=self.client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0,
                         "Maybe it is bug, because there is no tasks to assign,"
                         "but tasks of this stage maybe selectable")
        # self.assertEqual(second_stage.id, response.data["results"][0]["id"])

    def test_task_stage_get_schema_fields(self):
        schema = {"properties":{"column1":{"column1":{}},"column2":{"column2":{}},"oik":{"properties":{"uik1":{}}}}}
        ui_schema = {"ui:order": ["column2", "column1", "oik"]}
        self.initial_stage.json_schema = json.dumps(schema)
        self.initial_stage.ui_schema = json.dumps(ui_schema)
        self.initial_stage.save()

        response = self.get_objects('taskstage-schema-fields',
                                    pk=self.initial_stage.id)
        self.assertEqual(response.data['fields'],
                         ['column2', 'column1', 'oik__uik1'])

    def test_stage_max_limits(self):
        [i.delete() for i in RankLimit.objects.all()]
        rank_1 = self.user.ranks.first()
        RankLimit.objects.create(
            stage=self.initial_stage,
            rank=rank_1,
            open_limit=1,
            total_limit=2,
        )
        rank_2 = Rank.objects.create(name="rank 2", track=self.default_track, priority=0)
        RankRecord.objects.create(
            user=self.user,
            rank=rank_2)
        RankLimit.objects.create(
            stage=self.initial_stage,
            rank=rank_2,
            open_limit=0,
            total_limit=2,
        )

        rank_3 = Rank.objects.create(name="rank 2", track=self.default_track, priority=0)
        RankRecord.objects.create(
            user=self.user,
            rank=rank_3)
        RankLimit.objects.create(
            stage=self.initial_stage,
            rank=rank_3,
            open_limit=0,
            total_limit=5,
        )

        response = self.get_objects('taskstage-user-relevant')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        stage = response.data["results"][0]
        self.assertEqual(stage["rank_limit"], {"open_limit": 0, "total_limit": 5})
