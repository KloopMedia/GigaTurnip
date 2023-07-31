import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants, \
    CopyFieldConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class ChainTest(GigaTurnipTestHelper):
    def test_simple_chain(self):
        second_stage = self.initial_stage.add_stage(TaskStage())
        initial_task = self.create_initial_task()
        self.complete_task(initial_task)
        second_task = initial_task.out_tasks.get()
        self.check_task_auto_creation(second_task, second_stage, initial_task)

    def test_chain_individuals_by_highest_rank(self):
        self.chain.is_individual = True
        self.chain.save()

        middle_chain = Chain.objects.create(
            name="Middle chain",
            campaign=self.campaign,
            is_individual=True
        )
        middle_stage = TaskStage.objects.create(
            name="Middle chain stage",
            x_pos=1,
            y_pos=1,
            chain=middle_chain,
            is_creatable=True
        )
        middle_rank = Rank.objects.create(
            name="Middle rank",
            track=self.default_track,
            priority=1
        )
        RankLimit.objects.create(
            rank=middle_rank,
            stage=middle_stage,
            is_creation_open=True
        )

        highest_chain = Chain.objects.create(
            name="Highest chain",
            campaign=self.campaign,
            is_individual=True
        )
        highest_stage = TaskStage.objects.create(
            name="Highest chain stage",
            x_pos=1,
            y_pos=1,
            chain=highest_chain,
            is_creatable=True
        )
        highest_rank = Rank.objects.create(
            name="Highest rank",
            track=self.default_track,
            priority=2
        )
        RankLimit.objects.create(
            rank=highest_rank,
            stage=highest_stage,
            is_creation_open=True
        )

        RankRecord.objects.create(rank=middle_rank, user=self.user)
        RankRecord.objects.create(rank=highest_rank, user=self.user)

        highest_ranks_qs = self.user.get_highest_ranks_by_track()
        self.assertEqual(highest_ranks_qs.count(), 1)
        self.assertEqual(
            highest_ranks_qs.first()["max_rank_id"],
            highest_rank.id
        )

        params = {"by_highest_ranks": "true"}
        response = self.get_objects("taskstage-user-relevant", params=params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = to_json(response.content)
        self.assertEqual(content["count"], 1)
        self.assertEqual([highest_stage.id],
                         sorted([i["id"] for i in content["results"]]))

        response = self.get_objects("chain-individuals")
        content = to_json(response.content)
        self.assertEqual(content["count"], 3)
        chains = [self.chain.id, middle_chain.id, highest_chain.id]
        self.assertEqual(chains, [i["id"] for i in content["results"]])


        response = self.get_objects("chain-individuals", params=params)
        content = to_json(response.content)
        self.assertEqual(content["count"], 1)
        chains = [highest_chain.id]
        self.assertEqual(chains, [i["id"] for i in content["results"]])

        new_track = Track.objects.create(
            campaign=self.campaign,
            default_rank=middle_rank
        )
        new_track.save()

        highest_rank.track = new_track
        highest_rank.save()

        highest_ranks = self.user.get_highest_ranks_by_track().values_list(
            "max_rank_id", flat=True)
        self.assertIn(highest_rank.id, highest_ranks)
        self.assertIn(middle_rank.id, highest_ranks)

        response = self.get_objects("chain-individuals", params=params)
        content = to_json(response.content)
        self.assertEqual(content["count"], 2)
        chains = [middle_chain.id, highest_chain.id]
        self.assertEqual(chains, [i["id"] for i in content["results"]])

    def test_individual_chain_update_task(self):
        self.chain.is_individual = True
        self.chain.save()

        self.initial_stage.json_schema = '{"type": "object","properties": {"firstName": {"type": "string"}}}'
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(TaskStage(
            name="Second Stage",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage,
        ))
        second_stage.json_schema = '{"type": "object","properties": {"lastName": {"type": "string"}}}'
        second_stage.save()

        third_stage = second_stage.add_stage(TaskStage(
            name="Second Stage",
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage,
        ))
        third_stage.json_schema = '{"type": "object","properties": {"phoneNumber": {"type": "string"}}}'
        third_stage.save()

        # Adjust copy name in second stage
        CopyField.objects.create(
            copy_by=CopyFieldConstants.CASE,
            task_stage=second_stage,
            copy_from_stage=self.initial_stage,
            fields_to_copy="firstName->firstName")
        CopyField.objects.create(
            copy_by=CopyFieldConstants.CASE,
            task_stage=third_stage,
            copy_from_stage=second_stage,
            fields_to_copy="firstName->firstName lastName->lastName")

        response_1 = {"firstName": "Ivan"}
        task_1 = self.create_task(self.initial_stage)
        task_1 = self.complete_task(task_1, response_1)
        self.check_task_completion(task_1, self.initial_stage, response_1)

        task_2 = task_1.out_tasks.first()
        self.assertFalse(task_2.complete)
        self.assertFalse(task_2.reopened)
        self.assertEqual(task_2.responses, {"firstName": "Ivan"})

        # update first task and watch how it is affect
        task_1 = self.complete_task(task_1, {"firstName": "Mark Bulah"})
        self.assertIsInstance(task_1, Task)
        self.assertEqual(Task.objects.count(), 2)
        self.assertEqual(task_1.out_tasks.first().responses,
                         {"firstName": "Mark Bulah"})

        response_2 = {"firstName": "Mark Bulah", "lastName": "Ivanov"}
        task_2 = self.complete_task(task_2, response_2)
        self.assertTrue(task_2.complete)
        self.assertFalse(task_2.reopened)
        self.assertEqual(task_2.responses, response_2)
        self.assertEqual(Task.objects.count(), 3)

        task_3 = task_2.out_tasks.first()
        self.assertEqual(task_3.responses, {"lastName": "Ivanov", "firstName": "Mark Bulah"})
        self.assertFalse(task_3.complete)
        self.assertFalse(task_3.reopened)

        # update second task
        task_2 = self.complete_task(task_2, {"lastName": "Zubarev"})
        self.assertIsInstance(task_2, Task)
        self.assertEqual(task_2.out_tasks.first().responses,
                         {"firstName": "Mark Bulah", "lastName": "Zubarev"})
        task_3 = task_2.out_tasks.first()
        # self.assertEqual(task_3.responses, {"firstName": "Mark", "lastName": "Ivanov"}) todo: it is may be bug
        response_3 = {"firstName": "Mark Bulah", "lastName": "Zubarev", "phone": 123}
        task_3 = self.complete_task(task_3, response_3)
        self.assertIsInstance(task_3, Task)
        self.assertTrue(task_3.complete)
        self.assertFalse(task_3.reopened)
        self.assertEqual(Task.objects.count(), 3)

    def test_chain_get_graph(self):
        self.user.managed_campaigns.add(self.campaign)
        second_stage = self.initial_stage.add_stage(
            TaskStage(
                name='Second Task Stage',
                assign_user_by='ST',
                assign_user_from_stage=self.initial_stage,
            )
        )
        cond_stage = second_stage.add_stage(
            ConditionalStage(
                name="MyCondStage",
                conditions=[{"field": "foo", "value": "boo", "condition": "=="}]
            )
        )

        info_about_graph = [
            {'pk': self.initial_stage.id, 'name': self.initial_stage.name, 'in_stages': [None],
             'out_stages': [second_stage.id]},
            {'pk': second_stage.id, 'name': second_stage.name, 'in_stages': [self.initial_stage.id],
             'out_stages': [cond_stage.id]},
            {'pk': cond_stage.id, 'name': cond_stage.name, 'in_stages': [second_stage.id], 'out_stages': [None]}
        ]

        response = self.get_objects("chain-get-graph", pk=self.chain.id)
        self.assertEqual(len(response.data), 3)
        for i in info_about_graph:
            self.assertIn(i, response.data)

    def test_forking_chain_happy(self):
        self.initial_stage.json_schema = {"type": "object",
                                          "properties": {"1": {"enum": ["a", "b", "c", "d"], "type": "string"}}}
        self.initial_stage.json_schema = json.dumps(self.initial_stage.json_schema)
        self.initial_stage.save()

        second_stage = self.initial_stage.add_stage(TaskStage(
            name='You have complete task successfully',
            json_schema=self.initial_stage.json_schema,
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage
        ))
        rating_stage = self.initial_stage.add_stage(TaskStage(
            name='Rating stage',
            json_schema=self.initial_stage.json_schema,
            assign_user_by=TaskStageConstants.STAGE,
            assign_user_from_stage=self.initial_stage
        ))

        task = self.create_initial_task()
        responses = {"1": "a"}
        response = self.complete_task(task, responses=responses, whole_response=True)
        task = Task.objects.get(id=response.data['id'])
        self.assertEqual(task.case.tasks.count(), 3)
        self.assertIn(
            response.data.get('next_direct_id'),
            task.out_tasks.values_list('id', flat=True)
        )

    def test_chain_individuals(self):
        self.chain.is_individual = True
        self.chain.save()
        individual_chain_1 = Chain.objects.create(
            name="Not individual chain 1",
            is_individual=True,
            campaign=self.campaign,
        )
        individual_chain_2 = Chain.objects.create(
            name="Not individual chain 2",
            is_individual=True,
            campaign=self.campaign,
        )

        # create stages
        stage_1 = TaskStage.objects.create(
            chain=individual_chain_1,
            x_pos=1,
            y_pos=1,
            is_creatable=True
        )
        stage_2 = TaskStage.objects.create(
            chain=individual_chain_2,
            x_pos=1,
            y_pos=1,
            is_creatable=True
        )

        [self.prepare_client(i, user=self.user) for i in [stage_1, stage_2]]

        # complete tasks
        case_initial = Case.objects.create()
        task_initial = Task.objects.create(
            stage=self.initial_stage,
            case=case_initial,
            assignee=self.user,
            responses={},
            complete=False
        )
        case_1 = Case.objects.create()
        task_1 = Task.objects.create(
            stage=stage_1,
            case=case_1,
            assignee=self.user,
            responses={},
            complete=True
        )
        case_2 = Case.objects.create()
        task_2 = Task.objects.create(
            stage=stage_2,
            case=case_2,
            assignee=self.user,
            responses={},
            complete=True
        )

        response_all = self.get_objects("chain-individuals")
        response_completed = self.get_objects("chain-individuals", params={"completed": True})
        response_not_completed = self.get_objects("chain-individuals", params={"completed": False})

        self.assertEqual(response_all.status_code, status.HTTP_200_OK)
        self.assertEqual(response_completed.status_code, status.HTTP_200_OK)
        self.assertEqual(response_not_completed.status_code, status.HTTP_200_OK)

        self.assertEqual(response_all.data["count"], 3)
        self.assertEqual(response_completed.data["count"], 2)
        self.assertEqual(response_not_completed.data["count"], 1)
