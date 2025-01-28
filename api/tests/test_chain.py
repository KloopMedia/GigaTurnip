import json

from api.serializer import ChainIndividualsSerializer
from api.views import ChainViewSet
from rest_framework import status

from api.constans import (
    AutoNotificationConstants, TaskStageConstants,
    CopyFieldConstants, ChainConstants,
)
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Value, JSONField, Q, Count, Subquery, OuterRef


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
        self.assertEqual(content["count"], 0)
        # self.assertEqual([highest_stage.id],
        #                  sorted([i["id"] for i in content["results"]]))

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
        individual_chain_3 = Chain.objects.create(
            name="Not individual chain 3",
            is_individual=True,
            campaign=self.campaign,
        )

        # create stages
        self.initial_stage.complete_individual_chain = True
        self.initial_stage.save()
        stage_1 = TaskStage.objects.create(
            chain=individual_chain_1,
            x_pos=1,
            y_pos=1,
            is_creatable=True,
            complete_individual_chain=True
        )
        stage_2 = TaskStage.objects.create(
            chain=individual_chain_2,
            x_pos=1,
            y_pos=1,
            is_creatable=True,
            complete_individual_chain=True
        )
        stage_3 = TaskStage.objects.create(
            chain=individual_chain_3,
            x_pos=1,
            y_pos=1,
            is_creatable=True,
            complete_individual_chain=True
        )

        [self.prepare_client(i, user=self.user) for i in [stage_1, stage_2, stage_3]]

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

        expected_stages = {self.chain.id, individual_chain_1.id, individual_chain_2.id, individual_chain_3.id}
        actual_stages = {i["id"] for i in response_all.data["results"]}
        self.assertEqual(expected_stages, actual_stages)
        self.assertEqual(response_all.data["count"], 4)

        expected_stages = {individual_chain_1.id, individual_chain_2.id}
        actual_stages = {i["id"] for i in response_completed.data["results"]}
        self.assertEqual(expected_stages, actual_stages)
        self.assertEqual(response_completed.data["count"], 2)

        expected_not_completed = {self.chain.id, individual_chain_3.id}
        actual_not_completed = {i["id"] for i in response_not_completed.data["results"]}
        self.assertEqual(response_not_completed.data["count"], 2)
        self.assertEqual(expected_not_completed, actual_not_completed)


    def _create_individual_chains(self):
        """Helper to create test individual chains"""
        
        return [
            Chain.objects.create(
                name=f"Individual chain {i}",
                is_individual=True,
                campaign=self.campaign,
            ) for i in range(0, 3)
        ]

    # def _create_stages_for_chains(self, chains):
    #     """Helper to create and prepare stages for chains"""
    #     self.initial_stage.complete_individual_chain = True
    #     self.initial_stage.save()
        
    #     stages = []
    #     for chain in chains:
    #         stage = TaskStage.objects.create(
    #             chain=chain,
    #             x_pos=1,
    #             y_pos=1,
    #             is_creatable=True,
    #             complete_individual_chain=True
    #         )
    #         stages.append(stage)
            
    #     # Prepare clients for all stages
    #     [self.prepare_client(stage, user=self.user) for stage in stages]
    #     return stages

    def _create_stages_for_chains(self, chains):
        """Helper to create and prepare stages for chains"""

        first_stages = []
        second_stages = []
        
        for chain in chains:
            # Create first stage
            first_stage = TaskStage.objects.create(
                chain=chain,
                x_pos=1,
                y_pos=1,
                is_creatable=True,
                complete_individual_chain=False,  # Only second stage marks completion
                name="First Stage"
            )
            first_stages.append(first_stage)
            
            # Create and link second stage using add_stage
            second_stage = TaskStage(
                name="Second Stage",
                is_creatable=False,
                complete_individual_chain=True,  # This stage marks completion
                x_pos=2,
                y_pos=1
            )
            first_stage.add_stage(second_stage)
            second_stages.append(second_stage)
            
        # Prepare clients for all stages
        [self.prepare_client(stage, user=self.user) for stage in first_stages + second_stages]
        
        return first_stages, second_stages

    def _complete_tasks_for_stages(self, stages, complete_indices=[0, 1]):
        """Helper to create and complete tasks for specified stages"""
        tasks = []
        for i, stage in enumerate(stages):
            complete_state = False
            if i in complete_indices:
                complete_state = True
            case = Case.objects.create()
            task = Task.objects.create(
                stage=stage,
                case=case,
                assignee=self.user,
                responses={},
                complete=complete_state
            )
            tasks.append(task)
        return tasks

    def test_chain_individuals_all(self):
        """Test getting all individual chains"""
        chains = self._create_individual_chains()
        first_stages, second_stages = self._create_stages_for_chains(chains)
        self._complete_tasks_for_stages(first_stages + second_stages)

        response = self.get_objects("chain-individuals")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        
        # Verify chain IDs
        expected_chains = [chain.id for chain in chains]
        self.assertEqual(expected_chains, [i["id"] for i in response.data["results"]])

        # Verify stage connections for each chain
        for chain in response.data["results"]:
            stages_data = chain["stages_data"]
            self.assertEqual(len(stages_data), 2)  # Each chain has 2 stages
            
            # First stage should point to second stage
            first_stage = stages_data[0]
            second_stage = stages_data[1]
            
            self.assertEqual(first_stage["out_stages"], [second_stage["id"]])
            self.assertEqual(first_stage["in_stages"], [])
            
            # Second stage should be pointed to by first stage
            self.assertEqual(second_stage["out_stages"], [])
            self.assertEqual(second_stage["in_stages"], [first_stage["id"]])

    def test_chain_individuals_completed(self):
        """Test getting completed individual chains"""
        chains = self._create_individual_chains()
        first_stages, second_stages = self._create_stages_for_chains(chains)
        self._complete_tasks_for_stages(second_stages, complete_indices=[0, 1])

        response = self.get_objects("chain-individuals", params={"completed": True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        
        expected_chains = [chains[0].id, chains[1].id]
        self.assertEqual(expected_chains, [i["id"] for i in response.data["results"]])

    def test_chain_individuals_not_completed(self):
        """Test getting not completed individual chains"""
        chains = self._create_individual_chains()
        first_stages, second_stages = self._create_stages_for_chains(chains)
        self._complete_tasks_for_stages(second_stages, complete_indices=[0, 1])

        response = self.get_objects("chain-individuals", params={"completed": False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        
        expected_incomplete_chain = chains[2].id
        self.assertEqual(expected_incomplete_chain, response.data["results"][0]["id"])

    def test_chain_individuals_order_by_created_at(self):
        self.chain.is_individual = True
        self.chain.save()

        # create stages
        stage_2 = self.initial_stage.add_stage(
            TaskStage(
                chain=self.chain,
                x_pos=1,
                y_pos=1,
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage
            )
        )
        stage_3 = stage_2.add_stage(
            TaskStage(
                chain=self.chain,
                x_pos=1,
                y_pos=1,
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=stage_2
            )
        )

        response = self.get_objects("chain-individuals")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["count"], 1)

        actual_order_ids = [i["id"] for i in response.data["results"][0]["stages_data"]]
        expected_order_ids = [self.initial_stage.id, stage_2.id, stage_3.id]
        self.assertEqual(actual_order_ids, expected_order_ids)

    def test_chain_individuals_order_by_order(self):
        self.chain.is_individual = True
        self.chain.order_in_individuals = ChainConstants.ORDER
        self.chain.save()

        # create stages
        stage_2 = self.initial_stage.add_stage(
            TaskStage(
                chain=self.chain,
                x_pos=1,
                y_pos=1,
                is_creatable=True,
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage,
                order=15
            )
        )
        stage_3 = stage_2.add_stage(
            TaskStage(
                chain=self.chain,
                x_pos=1,
                y_pos=1,
                is_creatable=True,
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=stage_2,
                order=1,
            )
        )

        response = self.get_objects("chain-individuals")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["count"], 1)

        actual_order_ids = [i["id"] for i in response.data["results"][0]["stages_data"]]
        expected_order_ids = [self.initial_stage.id, stage_3.id, stage_2.id]
        self.assertEqual(actual_order_ids, expected_order_ids)

    def test_chain_individuals_order_by_chain_flow(self):
        self.chain.is_individual = True
        self.chain.order_in_individuals = ChainConstants.GRAPH_FLOW
        self.chain.save()

        # create stages
        stage_2 = self.initial_stage.add_stage(
            TaskStage(
                chain=self.chain,
                x_pos=1,
                y_pos=1,
                is_creatable=True,
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage,
            )
        )
        conditional = stage_2.add_stage(
            ConditionalStage(
                name='Check',
                conditions=[{"type": "integer", "field": "newInput1", "value": 1,"condition": ">"}]
            )
        )
        stage_3 = conditional.add_stage(
            TaskStage(
                chain=self.chain,
                x_pos=1,
                y_pos=1,
                is_creatable=True,
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=stage_2,
            )
        )

        response = self.get_objects("chain-individuals")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["count"], 1)

        actual_order_ids = [i["id"] for i in response.data["results"][0]["stages_data"]]
        expected_order_ids = [self.initial_stage.id, stage_2.id, stage_3.id]
        self.assertEqual(actual_order_ids, expected_order_ids)

    def test_chain_individuals_filter_stages_individuals(self):
        self.chain.is_individual = True
        self.chain.order_in_individuals = ChainConstants.GRAPH_FLOW
        self.chain.save()

        # create stages
        stage_2 = self.initial_stage.add_stage(
            TaskStage(
                chain=self.chain,
                x_pos=1,
                y_pos=1,
                is_creatable=True,
                assign_user_by=TaskStageConstants.AUTO_COMPLETE,
            )
        )
        stage_3 = stage_2.add_stage(
            TaskStage(
                name="stage to skip",
                chain=self.chain,
                x_pos=1,
                y_pos=1,
                is_creatable=True,
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=stage_2,
                skip_empty_individual_tasks=True
            )
        )

        response = self.get_objects("chain-individuals")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["count"], 1)

        actual_order_ids = [i["id"] for i in response.data["results"][0]["stages_data"]]
        expected_order_ids = [self.initial_stage.id]
        self.assertEqual(actual_order_ids, expected_order_ids)

    def test_chain_individuals_with_conditionals(self):
        """Test getting individual chain that includes conditional stage"""
        # Create individual chain
        chain = Chain.objects.create(
            name="Chain with conditional",
            campaign=self.campaign,
            is_individual=True,
            order_in_individuals=ChainConstants.CHRONOLOGICALLY  # or ChainConstants.ORDER
        )
        
        # Create first stage
        first_stage = TaskStage.objects.create(
            name="First Stage",
            chain=chain,
            x_pos=1,
            y_pos=1,
            is_creatable=True,
            order=1  # For manual ordering
        )
        
        # Create stages in sequence using add_stage
        conditional_stage = first_stage.add_stage(
            ConditionalStage(
                name="Conditional Stage",
                x_pos=2,
                y_pos=1,
                conditions=[{
                    "field": "answer",
                    "type": "string",
                    "value": "pass",
                    "condition": "=="
                }],
                order=2  # For manual ordering
            )
        )
        
        final_stage = conditional_stage.add_stage(
            TaskStage(
                name="Final Stage",
                x_pos=3,
                y_pos=1,
                complete_individual_chain=True,
                order=3  # For manual ordering
            )
        )
        
        # Prepare client for the stages
        [self.prepare_client(stage, user=self.user) for stage in [first_stage,final_stage]]
        
        response = self.get_objects("chain-individuals")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        
        # Verify stage connections
        chain_data = response.data["results"][0]
        
        stages_data = chain_data["stages_data"]
        
        self.assertEqual(len(stages_data), 2)  # Should have all 2 stages
        
        # Verify each stage's connections, conditional is not included as intended
        first = stages_data[0]
        final = stages_data[1]
        
        # First stage should point to conditional
        self.assertEqual(first["out_stages"], [conditional_stage.id]) # wrong number of out stages
        self.assertEqual(first["in_stages"], []) # wrong number of in stages
        
        # Final stage should be pointed to by conditional
        self.assertEqual(final["in_stages"], [conditional_stage.id]) # wrong number of in stages
        self.assertEqual(final["out_stages"], []) # wrong number of out stages


    def test_chain_individuals_campaign_filter(self):
        """Test filtering individual chains by campaign"""
        # Create first campaign with individual chain
        campaign1_data = self.generate_new_basic_campaign("Campaign 1")
        chain1 = Chain.objects.create(
            name="Individual Chain 1",
            campaign=campaign1_data["campaign"],
            is_individual=True,
            order_in_individuals=ChainConstants.CHRONOLOGICALLY
        )
        
        # Create first stage for chain1
        first_stage1 = TaskStage.objects.create(
            name="First Stage",
            chain=chain1,
            x_pos=1,
            y_pos=1,
            is_creatable=True
        )
        
        # Create final stage for chain1
        final_stage1 = first_stage1.add_stage(
            TaskStage(
                name="Final Stage",
                x_pos=2,
                y_pos=1,
                complete_individual_chain=True
            )
        )
        
        # Create second campaign with individual chain
        campaign2_data = self.generate_new_basic_campaign("Campaign 2")
        chain2 = Chain.objects.create(
            name="Individual Chain 2",
            campaign=campaign2_data["campaign"],
            is_individual=True,
            order_in_individuals=ChainConstants.CHRONOLOGICALLY
        )
        
        # Create first stage for chain2
        first_stage2 = TaskStage.objects.create(
            name="First Stage",
            chain=chain2,
            x_pos=1,
            y_pos=1,
            is_creatable=True
        )
        
        # Create final stage for chain2
        final_stage2 = first_stage2.add_stage(
            TaskStage(
                name="Final Stage",
                x_pos=2,
                y_pos=1,
                complete_individual_chain=True
            )
        )
        
        # Prepare client for all stages
        [self.prepare_client(stage, user=self.user) for stage in 
        [first_stage1, final_stage1, first_stage2, final_stage2]]
        
        # Test filtering by first campaign
        response = self.get_objects(
            "chain-individuals", 
            params={"campaign": campaign1_data["campaign"].id}
        )
        
        # print("\nResponse Data:")
        # print(json.dumps(response.data, indent=2, ensure_ascii=False))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], chain1.id)
        
        # Test filtering by second campaign
        response = self.get_objects(
            "chain-individuals", 
            params={"campaign": campaign2_data["campaign"].id}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], chain2.id)

    def test_chain_individuals_volume_filter(self):
        """Test filtering individual chains by volume"""
        # Create first campaign with volume and individual chain
        campaign1_data = self.generate_new_basic_campaign("Campaign 1")
        volume1 = Volume.objects.create(
            name="Volume 1",
            track_fk=campaign1_data["default_track"],
            order=1
        )
        
        chain1 = Chain.objects.create(
            name="Individual Chain 1",
            campaign=campaign1_data["campaign"],
            is_individual=True,
            order_in_individuals=ChainConstants.CHRONOLOGICALLY
        )
        
        # Create stages for chain1, connected to volume1
        first_stage1 = TaskStage.objects.create(
            name="First Stage",
            chain=chain1,
            x_pos=1,
            y_pos=1,
            is_creatable=True
        )
        first_stage1.volumes.add(volume1)
        
        final_stage1 = first_stage1.add_stage(
            TaskStage(
                name="Final Stage",
                x_pos=2,
                y_pos=1,
                complete_individual_chain=True
            )
        )
        final_stage1.volumes.add(volume1)
        
        # Create second volume in same campaign with another chain
        volume2 = Volume.objects.create(
            name="Volume 2",
            track_fk=campaign1_data["default_track"],
            order=2
        )
        
        chain2 = Chain.objects.create(
            name="Individual Chain 2",
            campaign=campaign1_data["campaign"],
            is_individual=True,
            order_in_individuals=ChainConstants.CHRONOLOGICALLY
        )
        
        # Create stages for chain2, connected to volume2
        first_stage2 = TaskStage.objects.create(
            name="First Stage",
            chain=chain2,
            x_pos=1,
            y_pos=1,
            is_creatable=True
        )
        first_stage2.volumes.add(volume2)
        
        final_stage2 = first_stage2.add_stage(
            TaskStage(
                name="Final Stage",
                x_pos=2,
                y_pos=1,
                complete_individual_chain=True
            )
        )
        final_stage2.volumes.add(volume2)
        
        # Prepare client for all stages
        [self.prepare_client(stage, user=self.user) for stage in 
         [first_stage1, final_stage1, first_stage2, final_stage2]]
        
        # Test filtering by first volume
        response = self.get_objects(
            "chain-individuals", 
            params={"stages__volumes": volume1.id}
        )
        
        # print("\nResponse Data for Volume 1:")
        # print(json.dumps(response.data, indent=2, ensure_ascii=False))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], chain1.id)
        
        # Test filtering by second volume
        response = self.get_objects(
            "chain-individuals", 
            params={"stages__volumes": volume2.id}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], chain2.id)

    def test_chain_individuals_campaign_and_volume_filter(self):
        """Test filtering individual chains by both campaign and volume"""
        # Create first campaign with volume
        campaign1_data = self.generate_new_basic_campaign("Campaign 1")
        volume1 = Volume.objects.create(
            name="Volume 1",
            track_fk=campaign1_data["default_track"],
            order=1
        )
        
        # Create chain1 in campaign1 with volume1
        chain1 = Chain.objects.create(
            name="Chain 1 Campaign 1 Volume 1",
            campaign=campaign1_data["campaign"],
            is_individual=True,
            order_in_individuals=ChainConstants.CHRONOLOGICALLY
        )
        
        # Create stages for chain1
        first_stage1 = TaskStage.objects.create(
            name="First Stage",
            chain=chain1,
            x_pos=1,
            y_pos=1,
            is_creatable=True
        )
        first_stage1.volumes.add(volume1)
        
        final_stage1 = first_stage1.add_stage(
            TaskStage(
                name="Final Stage",
                x_pos=2,
                y_pos=1,
                complete_individual_chain=True
            )
        )
        final_stage1.volumes.add(volume1)
        
        # Create second campaign with volume
        campaign2_data = self.generate_new_basic_campaign("Campaign 2")
        volume2 = Volume.objects.create(
            name="Volume 2",
            track_fk=campaign2_data["default_track"],
            order=1
        )
        
        # Create chain2 in campaign2 with volume2
        chain2 = Chain.objects.create(
            name="Chain 2 Campaign 2 Volume 2",
            campaign=campaign2_data["campaign"],
            is_individual=True,
            order_in_individuals=ChainConstants.CHRONOLOGICALLY
        )
        
        # Create stages for chain2
        first_stage2 = TaskStage.objects.create(
            name="First Stage",
            chain=chain2,
            x_pos=1,
            y_pos=1,
            is_creatable=True
        )
        first_stage2.volumes.add(volume2)
        
        final_stage2 = first_stage2.add_stage(
            TaskStage(
                name="Final Stage",
                x_pos=2,
                y_pos=1,
                complete_individual_chain=True
            )
        )
        final_stage2.volumes.add(volume2)
        
        # Create additional chain in campaign1 with volume2
        chain3 = Chain.objects.create(
            name="Chain 3 Campaign 1 Volume 2",
            campaign=campaign1_data["campaign"],
            is_individual=True,
            order_in_individuals=ChainConstants.CHRONOLOGICALLY
        )
        
        # Create stages for chain3
        first_stage3 = TaskStage.objects.create(
            name="First Stage",
            chain=chain3,
            x_pos=1,
            y_pos=1,
            is_creatable=True
        )
        first_stage3.volumes.add(volume2)
        
        final_stage3 = first_stage3.add_stage(
            TaskStage(
                name="Final Stage",
                x_pos=2,
                y_pos=1,
                complete_individual_chain=True
            )
        )
        final_stage3.volumes.add(volume2)
        
        # Prepare client for all stages
        [self.prepare_client(stage, user=self.user) for stage in 
         [first_stage1, final_stage1, first_stage2, final_stage2, first_stage3, final_stage3]]
        
        # Test filtering by campaign1 and volume1
        response = self.get_objects(
            "chain-individuals", 
            params={
                "campaign": campaign1_data["campaign"].id,
                "stages__volumes": volume1.id
            }
        )
        
        # print("\nResponse Data for Campaign 1 + Volume 1:")
        # print(json.dumps(response.data, indent=2, ensure_ascii=False))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], chain1.id)
        
        # Test filtering by campaign1 and volume2
        response = self.get_objects(
            "chain-individuals", 
            params={
                "campaign": campaign1_data["campaign"].id,
                "stages__volumes": volume2.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], chain3.id)
        
        # Test filtering by campaign2 and volume2
        response = self.get_objects(
            "chain-individuals", 
            params={
                "campaign": campaign2_data["campaign"].id,
                "stages__volumes": volume2.id
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], chain2.id)
        

    def test_chain_individuals_task_states(self):
        """Test individual chain tasks states (completed/opened/reopened) for different users"""
        # Convert existing chain to individual
        self.chain.is_individual = True
        self.chain.save()
        
        # Add schema to initial stage
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"]
        })
        self.initial_stage.save()
        
        # Create final stage that gets user from initial stage
        final_stage = self.initial_stage.add_stage(
            TaskStage(
                name="Final Stage",
                x_pos=2,
                y_pos=1,
                assign_user_by=TaskStageConstants.STAGE,
                assign_user_from_stage=self.initial_stage,
                complete_individual_chain=True
            )
        )

        second_user = CustomUser.objects.create_user(
            username="second_user",
            email="second_user@email.com",
            password="test"
        )
        RankRecord.objects.create(
            user=second_user,
            rank=self.user.ranks.first()  # Use the same rank as first user
        )
        second_client = self.create_client(second_user)
        
        # Create and complete task for first user
        task = self.create_initial_task()
        completed_task = self.complete_task(task, responses={"answer": "test"})
        
        # Create but don't complete task for second user
        second_user_task = self.create_task(self.initial_stage, client=second_client)
        
        # Get chain data for first user
        response = self.get_objects("chain-individuals")
        
        # print("\nResponse Data for First User:")
        # print(json.dumps(response.data, indent=2, ensure_ascii=False))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

        chain_data = response.data["results"][0]
        stages_data = chain_data["stages_data"]
        
        # Check first stage states for first user
        first_stage_data = stages_data[0]
        self.assertEqual(first_stage_data["completed"], [completed_task.id])
        self.assertEqual(first_stage_data["opened"], [])
        self.assertEqual(first_stage_data["reopened"], [])
        
        # Check final stage states for first user
        final_stage_data = stages_data[1]
        self.assertEqual(final_stage_data["completed"], [])
        first_user_second_stage_task = Task.objects.get(assignee=self.user, stage=final_stage)
        self.assertEqual(final_stage_data["opened"], [first_user_second_stage_task.id])
        self.assertEqual(final_stage_data["reopened"], [])
        
        # Get chain data for second user
        response = self.get_objects("chain-individuals", client=second_client)

        # print("\nResponse Data for Second User:")
        # print(json.dumps(response.data, indent=2, ensure_ascii=False))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        
        chain_data = response.data["results"][0]
        stages_data = chain_data["stages_data"]
        
        # Check first stage states for second user
        first_stage_data = stages_data[0]
        self.assertEqual(first_stage_data["completed"], [])
        self.assertEqual(first_stage_data["opened"], [second_user_task.id])
        self.assertEqual(first_stage_data["reopened"], [])
        
        # Check final stage states for second user
        final_stage_data = stages_data[1]
        self.assertEqual(final_stage_data["completed"], [])
        self.assertEqual(final_stage_data["opened"], [])
        self.assertEqual(final_stage_data["reopened"], [])

    def test_chain_individuals_rank_filter(self):
        """Test that individual chains endpoint only shows chains with matching ranks"""
        # Convert existing chain to individual and add schema
        self.chain.is_individual = True
        self.chain.save()
        
        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"]
        })
        self.initial_stage.save()
        
        # Create second chain in the same campaign
        second_chain = Chain.objects.create(
            name="Second Individual Chain",
            campaign=self.campaign,
            is_individual=True,
            order_in_individuals=ChainConstants.CHRONOLOGICALLY
        )
        
        # Create stage with different rank for second chain
        different_rank = Rank.objects.create(
            name="Different Rank",
            track=self.default_track
        )
        
        second_chain_stage = TaskStage.objects.create(
            name="Stage with Different Rank",
            chain=second_chain,
            x_pos=1,
            y_pos=1,
            is_creatable=True,
            json_schema=json.dumps({
                "type": "object",
                "properties": {
                    "answer": {"type": "string"}
                },
                "required": ["answer"]
            })
        )
        
        # Create rank limit for the new stage with different rank
        RankLimit.objects.create(
            rank=different_rank,
            stage=second_chain_stage,
            is_creation_open=True
        )
        
        # Get chain data for user (should only see first chain)
        response = self.get_objects("chain-individuals")

        # print("\nResponse Data for First User:")
        # print(json.dumps(response.data, indent=2, ensure_ascii=False))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.chain.id)
        
        # Create new user with the different rank
        different_rank_user = CustomUser.objects.create_user(
            username="different_rank_user",
            email="different_rank_user@email.com",
            password="test"
        )
        RankRecord.objects.create(
            user=different_rank_user,
            rank=different_rank
        )
        different_client = self.create_client(different_rank_user)
        
        # Get chain data for different rank user (should only see second chain)
        response = self.get_objects("chain-individuals", client=different_client)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], second_chain.id)

    def test_textbook_chains(self):
        """Test getting textbook chains with rich text stages"""
        rich_text = "Learn about Python variables and data types"
        rich_text_2 = "Introduction to Python programming"
        
        # Create a textbook chain
        textbook_chain = Chain.objects.create(
            name="Python Tutorial",
            campaign=self.campaign,
            is_text_book=True
        )
        
        # Create stages with rich text in different order
        stage_2 = TaskStage.objects.create(
            chain=textbook_chain,
            name="Variables and Types",
            order=2,
            rich_text=rich_text_2,
            x_pos=1,
            y_pos=1
        )
        
        stage_1 = TaskStage.objects.create(
            chain=textbook_chain,
            name="Introduction",
            order=1,
            rich_text=rich_text,
            x_pos=1,
            y_pos=1
        )
        
        # Create stage without rich text (should be excluded)
        stage_3 = TaskStage.objects.create(
            chain=textbook_chain,
            name="Empty Stage",
            order=3,
            rich_text="",
            x_pos=1,
            y_pos=1
        )
        
        # Link stages
        stage_1.add_stage(stage_2).add_stage(stage_3)
        
        response = self.get_objects("chain-textbooks")

        # print("\nResponse Data for Textbook Chain:")
        # print(json.dumps(response.data, indent=2, ensure_ascii=False))
        
        # Verify successful response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify we get exactly one textbook chain
        self.assertEqual(response.data["count"], 1)
        
        chain_data = response.data["results"][0]
        # Verify correct chain ID is returned
        self.assertEqual(chain_data["id"], textbook_chain.id)
        
        stages_data = chain_data["stages_data"]
        # Verify only stages with rich text are included (empty stage excluded)
        self.assertEqual(len(stages_data), 2)
        
        # Verify first stage data
        self.assertEqual(stages_data[0]["id"], stage_1.id)  # Should be stage_1 due to order=1
        self.assertEqual(stages_data[0]["order"], 1)  # Verify correct order
        self.assertEqual(stages_data[0]["out_stages"], [stage_2.id])  # Verify stage connection
        self.assertEqual(stages_data[0]["rich_text"], rich_text)  # Verify rich text content
        
        # Verify second stage data
        self.assertEqual(stages_data[1]["id"], stage_2.id)  # Should be stage_2 due to order=2
        self.assertEqual(stages_data[1]["order"], 2)  # Verify correct order
        self.assertEqual(stages_data[1]["out_stages"], [stage_3.id])  # Verify one outgoing connection
        self.assertEqual(stages_data[1]["rich_text"], rich_text_2)  # Verify rich text content