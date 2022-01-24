import json
from uuid import uuid4

from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase, APIClient, RequestsClient
from rest_framework.reverse import reverse
from rest_framework import status

from api.models import CustomUser, Campaign, CampaignManagement, Chain, TaskStage, Integration, Webhook, Task, Track, \
    RankRecord, Notification, Rank, RankLimit, CopyField, StagePublisher, Quiz, Case


class GigaTurnip(APITestCase):

    def prepare_client(self, stage, user=None, rank_limit=None):
        u = user
        if u is None:
            user_name = str(uuid4())
            u = CustomUser.objects.create_user(
                username=user_name,
                email=user_name + "@email.com",
                password='test')
        rank = Rank.objects.create(name=stage.name)
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
        client = APIClient()
        client.force_authenticate(u)
        return client

    def get_objects(self, endpoint, params=None, client=None, pk=None):
        c = client
        if c is None:
            c = self.client
        if pk:
            url = reverse(endpoint, kwargs={"pk": pk})
        else:
            url = reverse(endpoint)
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

    def complete_task(self, task, responses=None, client=None):
        c = client
        if c is None:
            c = self.client
        task_update_url = reverse("task-detail", kwargs={"pk": task.pk})
        if responses:
            args = {"complete": True, "responses": responses}
        else:
            args = {"complete": True}
        response = c.patch(task_update_url, args, format='json')
        return Task.objects.get(id=response.data["id"])

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


class ModelsTest(GigaTurnip):
    def setUp(self):
        self.campaign = Campaign.objects.create(name="Coca cola Campaign")
        self.chain = Chain.objects.create(
            name="Monday Chain",
            campaign=self.campaign)
        self.initial_stage = TaskStage.objects.create(
            name="Initial task stage",
            x_pos=1,
            y_pos=1,
            chain=self.chain,
            is_creatable=True
        )
        self.user = CustomUser.objects.create_user(
            username="Test User",
            email="test@email.com",
            password="test"
        )

        self.client = self.prepare_client(
            stage=self.initial_stage,
            user=self.user,
            rank_limit=RankLimit(is_creation_open=True)
        )

    def test_campaign_management_on_delete_user_instance(self):
        old_count_managers = CampaignManagement.objects.count()
        self.user.managed_campaigns.add(self.campaign)

        self.assertNotEqual(old_count_managers, CampaignManagement.objects.count())

        self.user.delete()

        self.assertEqual(old_count_managers, CampaignManagement.objects.count())
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(Chain.objects.count(), 1)
        self.assertEqual(TaskStage.objects.count(), 1)

    def test_campaign_management_on_delete_campaign_instance(self):
        old_count_managers = CampaignManagement.objects.count()
        self.user.managed_campaigns.add(self.campaign)

        self.assertNotEqual(old_count_managers, CampaignManagement.objects.count())

        self.campaign.delete()

        self.assertEqual(old_count_managers, CampaignManagement.objects.count())
        self.assertEqual(CustomUser.objects.count(), 1)
        self.assertEqual(Chain.objects.count(), 0)
        self.assertEqual(TaskStage.objects.count(), 0)

    def test_campaign_management_relations(self):
        campaign2 = Campaign.objects.create(name="New Campaign")
        campaign3 = Campaign.objects.create(name="New Campaign")

        self.user.managed_campaigns.add(self.campaign)
        self.user.managed_campaigns.add(campaign2)
        self.user.managed_campaigns.add(campaign3)

        self.assertEqual(3, CampaignManagement.objects.count())

        self.assertEqual([self.user], list(self.campaign.managers.all()))
        self.assertEqual([self.user], list(campaign2.managers.all()))
        self.assertEqual([self.user], list(campaign3.managers.all()))

    def test_chain_on_delete_campaign(self):
        old_count = Chain.objects.count()
        self.campaign.delete()
        self.assertLess(Chain.objects.count(), old_count)
        self.assertFalse(Chain.objects.filter(id=self.chain.id).exists())

    def test_task_stage_on_delete_chain(self):
        old_count = TaskStage.objects.count()
        self.chain.delete()
        self.assertLess(TaskStage.objects.count(), old_count)
        self.assertFalse(TaskStage.objects.filter(id=self.initial_stage.id).exists())

    def test_delete_stage_assign_by_ST(self):
        second_stage = self.initial_stage.add_stage(TaskStage(
                name="second_stage",
                assign_user_by="ST",
                assign_user_from_stage=self.initial_stage
            ))
        third_stage = second_stage.add_stage(TaskStage(
                name="third stage",
                assign_user_by="ST",
                assign_user_from_stage=second_stage
            ))

        self.assertEqual(TaskStage.objects.count(), 3)

        self.initial_stage.delete()

        self.assertEqual(TaskStage.objects.count(), 2)

        second_stage = TaskStage.objects.get(id=second_stage.id)
        self.assertEqual(second_stage.assign_user_from_stage, None)

    def test_display_prev_stages(self):
        stage2 = TaskStage.objects.create(
            name="second task stage",
            x_pos=1,
            y_pos=1,
            chain=self.chain,
            is_creatable=True
        )
        stage3 = TaskStage.objects.create(
            name="third task stage",
            x_pos=1,
            y_pos=1,
            chain=self.chain,
            is_creatable=True
        )

        self.initial_stage.displayed_prev_stages.add(stage2)
        self.initial_stage.displayed_prev_stages.add(stage3)

        stage2.displayed_prev_stages.add(self.initial_stage)
        stage2.displayed_prev_stages.add(stage3)

        self.assertEqual(self.initial_stage.displayed_prev_stages.count(), 2)
        self.assertEqual(stage2.displayed_prev_stages.count(), 2)
        self.assertEqual(stage3.displayed_prev_stages.count(), 0)

    def test_integration_on_delete_task_stage(self):
        integration = Integration.objects.create(task_stage=self.initial_stage, group_by="int")
        old_count = Integration.objects.count()

        self.initial_stage.delete()

        self.assertEqual(TaskStage.objects.count(), 0)
        self.assertLess(Integration.objects.count(), old_count)
        self.assertEqual(Integration.objects.count(), 0)

    def test_integration_on_relation_task_stage(self):
        integration = Integration.objects.create(task_stage=self.initial_stage, group_by="int")
        error = False
        try:
            with transaction.atomic():
                integration1 = Integration.objects.create(task_stage=self.initial_stage, group_by="int1")
            self.fail('Duplicate question allowed.')
        except IntegrityError:
            error = True

        self.assertEqual(TaskStage.objects.count(), 1)
        self.assertEqual(Integration.objects.count(), 1)
        self.assertTrue(error)

    def test_webhook_on_delete_task_stage(self):
        webhook = Webhook.objects.create(task_stage=self.initial_stage)
        old_count = Webhook.objects.count()

        self.initial_stage.delete()

        self.assertEqual(old_count, 1)
        self.assertNotEqual(old_count, Webhook.objects.count())

    def test_webhook_on_relation_task_stage(self):
        webhook = Webhook.objects.create(task_stage=self.initial_stage)
        error = False
        try:
            with transaction.atomic():
                integration1 = Webhook.objects.create(task_stage=self.initial_stage)
            self.fail('Duplicate question allowed.')
        except IntegrityError:
            error = True

        self.assertEqual(TaskStage.objects.count(), 1)
        self.assertEqual(Webhook.objects.count(), 1)
        self.assertTrue(error)

    def test_copy_field_on_delete_task_stage(self):
        second_stage = self.initial_stage.add_stage(TaskStage(
            name="second_stage",
            assign_user_by="ST",
            assign_user_from_stage=self.initial_stage
        ))
        copy_field = CopyField.objects.create(
            task_stage=second_stage,
            copy_from_stage=self.initial_stage,
            copy_all=True
        )
        old_count = CopyField.objects.count()

        self.initial_stage.delete()

        self.assertEqual(old_count, 1)
        self.assertNotEqual(old_count, CopyField.objects.count())
        self.assertEqual(0, CopyField.objects.count())

    def test_copy_field_on_delete_copy_from_stage(self):
        second_stage = self.initial_stage.add_stage(TaskStage(
            name="second_stage",
            assign_user_by="ST",
            assign_user_from_stage=self.initial_stage
        ))
        copy_field = CopyField.objects.create(
            task_stage=second_stage,
            copy_from_stage=self.initial_stage,
            copy_all=True
        )
        old_count = CopyField.objects.count()

        second_stage.delete()

        self.assertEqual(old_count, 1)
        self.assertNotEqual(old_count, CopyField.objects.count())
        self.assertEqual(0, CopyField.objects.count())

    def test_stage_publisher_on_task_stage_field(self):
        stage_publisher = StagePublisher.objects.create(task_stage=self.initial_stage)
        error = False
        try:
            with transaction.atomic():
                stage_publisher1 = StagePublisher.objects.create(task_stage=self.initial_stage)
            self.fail('Duplicate question allowed.')
        except IntegrityError:
            error = True

        self.assertEqual(TaskStage.objects.count(), 1)
        self.assertEqual(StagePublisher.objects.count(), 1)
        self.assertTrue(error)

    def test_stage_publisher_on_delete_task_stage(self):
        stage_publisher = StagePublisher.objects.create(task_stage=self.initial_stage)
        old_count = StagePublisher.objects.count()

        self.initial_stage.delete()

        self.assertEqual(old_count, 1)
        self.assertNotEqual(old_count, StagePublisher.objects.count())
        self.assertEqual(0, StagePublisher.objects.count())

    def test_quiz_on_one_to_one_correct_responses_task(self):
        task = self.create_initial_task()
        task1 = self.create_initial_task()
        quiz = Quiz.objects.create(task_stage=self.initial_stage, correct_responses_task=task)
        error = False
        try:
            with transaction.atomic():
                quiz1 = Quiz.objects.create(task_stage=self.initial_stage, correct_responses_task=task1)
            self.fail('Duplicate question allowed.')
        except IntegrityError:
            error = True

        self.assertEqual(TaskStage.objects.count(), 1)
        self.assertEqual(Quiz.objects.count(), 1)
        self.assertTrue(error)

    def test_quiz_on_one_to_one_task_stage(self):
        task = self.create_initial_task()
        second_stage = TaskStage.objects.create(
            name="ID",
            x_pos=1,
            y_pos=1,
            chain=self.chain,
            is_creatable=True
        )
        quiz = Quiz.objects.create(task_stage=self.initial_stage, correct_responses_task=task)
        error = False
        try:
            with transaction.atomic():
                quiz1 = Quiz.objects.create(task_stage=second_stage, correct_responses_task=task)
            self.fail('Duplicate question allowed.')
        except IntegrityError:
            error = True

        self.assertEqual(TaskStage.objects.count(), 2)
        self.assertEqual(Quiz.objects.count(), 1)
        self.assertTrue(error)

    def test_quiz_on_one_to_one(self):
        task = self.create_initial_task()
        second_stage = TaskStage.objects.create(
            name="ID",
            x_pos=1,
            y_pos=1,
            chain=self.chain,
            is_creatable=True
        )
        self.client = self.prepare_client(
            stage=second_stage,
            user=self.user,
            rank_limit=RankLimit(is_creation_open=True)
        )
        task1 = self.create_task(second_stage)

        quiz1 = Quiz.objects.create(task_stage=second_stage, correct_responses_task=task1)
        quiz = Quiz.objects.create(task_stage=self.initial_stage, correct_responses_task=task)

        self.assertEqual(TaskStage.objects.count(), 2)
        self.assertEqual(Quiz.objects.count(), 2)

    def test_quiz_on_delete_task_stage(self):
        task = self.create_initial_task()
        quiz = Quiz.objects.create(task_stage=self.initial_stage, correct_responses_task=task)

        old_count = Quiz.objects.count()

        self.initial_stage.delete()

        self.assertEqual(old_count, 1)
        self.assertNotEqual(old_count, Quiz.objects.count())
        self.assertEqual(0, Quiz.objects.count())

    def test_quiz_on_delete_task(self):
        task = self.create_initial_task()
        quiz = Quiz.objects.create(task_stage=self.initial_stage, correct_responses_task=task)

        old_count = Quiz.objects.count()

        task.delete()

        self.assertEqual(old_count, 1)
        self.assertNotEqual(old_count, Quiz.objects.count())
        self.assertEqual(0, Quiz.objects.count())

    # TODO test task referenced user delete
    # def test_task_on_delete_assignee(self):
        # new_user = CustomUser.objects.create_user(
        #     username="New User",
        #     email="new_user@email.com",
        #     password="new_user"
        # )
        #
        # task = Task.objects.create(assignee=new_user,
        #                            stage=self.initial_stage
        #                            )
        # old_count = Task.objects.count()
        #
        # new_user.delete()
        #
        # self.assertEqual(old_count, 1)
        # self.assertLess(Task.objects.count(), old_count)
        # self.assertEqual(Task.objects.count(), 0)

    def test_task_on_delete_task_stage(self):
        task = Task.objects.create(assignee=self.user,
                                   stage=self.initial_stage
                                   )
        old_count = Task.objects.count()

        self.initial_stage.delete()

        self.assertEqual(old_count, 1)
        self.assertLess(Task.objects.count(), old_count)
        self.assertEqual(Task.objects.count(), 0)

    def test_task_on_delete_case(self):
        case = Case.objects.create()
        task = Task.objects.create(assignee=self.user,
                                   stage=self.initial_stage,
                                   case=case
                                   )
        old_count = Task.objects.count()

        case.delete()

        self.assertEqual(old_count, 1)
        self.assertLess(Task.objects.count(), old_count)
        self.assertEqual(Task.objects.count(), 0)

    def test_rank_on_delete_track(self):
        track = Track.objects.create(name="track", campaign=self.campaign)
        rank = Rank.objects.all()[0]
        old_count = Rank.objects.count()

        track.delete()

        self.assertEqual(old_count, 1)
        self.assertEqual(Rank.objects.count(), old_count)

    def test_track_on_delete_campaign(self):
        track = Track.objects.create(
            name="Track",
            campaign=self.campaign,
        )
        rank = Rank.objects.all()[0]
        track.default_rank = rank
        track.save()

        old_count = Track.objects.count()
        self.campaign.delete()

        self.assertEqual(old_count, 1)
        self.assertLess(Track.objects.count(), old_count)
        self.assertEqual(Track.objects.count(), 0)

    def test_track_on_delete_default_rank(self):
        track = Track.objects.create(
            name="Track",
            campaign=self.campaign,
        )
        rank = Rank.objects.all()[0]

        track.default_rank = rank
        track.save()

        old_count = Track.objects.count()
        rank.delete()

        # TODO: make decision with on_delete argument
        self.assertEqual(old_count, Track.objects.count())

