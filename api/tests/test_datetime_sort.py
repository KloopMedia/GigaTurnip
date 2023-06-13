import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants
from api.models import *
from api.tests import GigaTurnipTestHelper


class DateTimeSortTest(GigaTurnipTestHelper):

    def test_datetime_sort_for_tasks(self):
        from datetime import datetime

        second_stage = self.initial_stage.add_stage(TaskStage(
            assign_user_by="RA"
        ))
        third_stage = second_stage.add_stage(TaskStage(
            assign_user_by="RA"
        ))
        verifier_rank = Rank.objects.create(name="verifier")
        RankRecord.objects.create(
            user=self.employee,
            rank=verifier_rank)
        RankLimit.objects.create(
            rank=verifier_rank,
            stage=second_stage,
            open_limit=5,
            total_limit=0,
            is_creation_open=False,
            is_listing_allowed=True,
            is_selection_open=True,
            is_submission_open=True
        )
        RankLimit.objects.create(
            rank=verifier_rank,
            stage=third_stage,
            open_limit=5,
            total_limit=0,
            is_creation_open=False,
            is_listing_allowed=True,
            is_selection_open=True,
            is_submission_open=True
        )
        time_limit = datetime(year=2020, month=1, day=1)
        DatetimeSort.objects.create(
            stage=second_stage,
            start_time=time_limit
        )
        DatetimeSort.objects.create(
            stage=third_stage,
            end_time=time_limit
        )

        task1 = self.create_initial_task()
        task1 = self.complete_task(task1)
        task2 = task1.out_tasks.get()

        response = self.get_objects('task-user-selectable', client=self.employee_client)
        content = json.loads(response.content)
        self.assertEqual(len(content['results']), 1)
        self.assertEqual(content['results'][0]['id'], task2.id)

        response_assign = self.get_objects('task-request-assignment', pk=task2.id, client=self.employee_client)
        self.assertEqual(response_assign.status_code, status.HTTP_200_OK)
        self.assertEqual(self.employee.tasks.count(), 1)

        task2 = Task.objects.get(id=task2.id)
        task2 = self.complete_task(task2, client=self.employee_client)

        last_task = task2.out_tasks.get()

        response = self.get_objects('task-user-selectable', client=self.employee_client)
        content = json.loads(response.content)
        self.assertEqual(len(content['results']), 0)

        response_assign = self.get_objects('task-request-assignment', pk=last_task.id, client=self.employee_client)
        self.assertEqual(response_assign.status_code, status.HTTP_200_OK)

        last_task = Task.objects.get(id=last_task.id)
        self.complete_task(last_task, client=self.employee_client)

    def test_task_with_timer_is_exist(self):
        second_stage = self.initial_stage.add_stage(TaskStage(
            assign_user_by="RA"
        ))
        verifier_rank = Rank.objects.create(name="verifier")
        RankRecord.objects.create(
            user=self.employee,
            rank=verifier_rank)
        RankLimit.objects.create(
            rank=verifier_rank,
            stage=second_stage,
            open_limit=5,
            total_limit=0,
            is_creation_open=False,
            is_listing_allowed=True,
            is_selection_open=True,
            is_submission_open=True
        )
        DatetimeSort.objects.create(
            stage=second_stage,
            how_much=2,
            after_how_much=0.1
        )
        task1 = self.create_initial_task()
        task1 = self.complete_task(task1)
        task1.out_tasks.get()

        response = self.get_objects('task-user-relevant')
        content = json.loads(response.content)
        self.assertEqual(len(content['results']), 1)

    def test_number_rank_endpoint(self):
        CampaignManagement.objects.create(user=self.employee,
                                          campaign=self.campaign)
        manager = CustomUser.objects.create_user(username="manager",
                                                       email='manager@email.com',
                                                       password='manager')
        track = Track.objects.create(campaign=self.campaign)
        rank1 = Rank.objects.create(name='rank1', track=track)
        rank2 = Rank.objects.create(name='rank2', track=track)
        rank2.prerequisite_ranks.add(rank1)
        rank3 = Rank.objects.create(name='rank3', track=track)
        track.default_rank = rank1
        self.campaign.default_track = track
        self.campaign.save(), track.save()

        task_awards = TaskAward.objects.create(
            task_stage_completion=self.initial_stage,
            task_stage_verified=self.initial_stage,
            rank=rank3,
            count=1,
        )

        RankRecord.objects.create(user=self.employee,
                                  rank=rank1)
        RankRecord.objects.create(user=manager,
                                  rank=rank1)
        RankRecord.objects.create(user=self.employee,
                                  rank=rank2)
        RankRecord.objects.create(user=self.employee,
                                  rank=rank3)

        response = self.get_objects('numberrank-list', client=self.employee_client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()[0]
        my_ranks_list = [
            {'name': 'rank1', 'condition': 'default', 'count': 2},
            {'name': 'rank2', 'condition': 'prerequisite_ranks', 'count': 1},
            {'name': 'rank3', 'condition': 'task_awards', 'count': 1},
        ]
        received_ranks = []

        for received_rank in data['ranks']:
            d = {
                'name': received_rank['name'],
                'condition': received_rank['condition'],
                'count': received_rank['count'],
            }
            received_ranks.append(d)

        for my_rank in my_ranks_list:
            self.assertIn(my_rank, received_ranks)
