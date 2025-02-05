import json

from rest_framework import status

from api.constans import AutoNotificationConstants, TaskStageConstants
from api.models import *
from api.tests import GigaTurnipTestHelper, to_json


class CampaignLinkerTest(GigaTurnipTestHelper):

    def test_campaign_linker(self):
        pepsi_data = self.generate_new_basic_campaign("Pepsi")
        fanta_data = self.generate_new_basic_campaign("Fanta")
        sprite_data = self.generate_new_basic_campaign("Sprite")

        self.assertEqual(Rank.objects.count(), 5)
        self.assertEqual(Track.objects.count(), 4)
        self.assertEqual(Campaign.objects.count(), 4)

        # creation queries to give another campaign ranks
        cola_to_pepsi = CampaignLinker.objects.create(
            name="From cola to PEPSI",
            out_stage=self.initial_stage,
            stage_with_user=self.initial_stage,
            target=pepsi_data["campaign"]
        )
        cola_to_fanta = CampaignLinker.objects.create(
            name="From cola to FANTA",
            out_stage=self.initial_stage,
            stage_with_user=self.initial_stage,
            target=fanta_data["campaign"]
        )
        cola_to_sprite = CampaignLinker.objects.create(
            name="From cola to SPRITE",
            out_stage=self.initial_stage,
            stage_with_user=self.initial_stage,
            target=sprite_data["campaign"]
        )

        # Prize Notification
        pepsi_not = Notification.objects.create(
            title="You access new rank from Pepsi campaign!",
            campaign=pepsi_data["campaign"]
        )
        sprite_not = Notification.objects.create(
            title="You access new rank from Pepsi campaign!",
            campaign=pepsi_data["campaign"]
        )
        pepsi_auto_not = AutoNotification.objects.create(
            notification=pepsi_not,
            go=AutoNotificationConstants.FORWARD
        )
        sprite_auto_not = AutoNotification.objects.create(
            notification=pepsi_not,
            go=AutoNotificationConstants.FORWARD
        )
        # approving links
        ApproveLink.objects.create(
            campaign=pepsi_data['campaign'],
            linker=cola_to_pepsi,
            rank=pepsi_data['rank'],
            notification=pepsi_auto_not,
            approved=True
        )
        ApproveLink.objects.create(
            campaign=sprite_data['campaign'],
            linker=cola_to_sprite,
            rank=sprite_data['rank'],
            notification=sprite_auto_not
        )

        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"]
        })
        task = self.create_initial_task()
        task = self.complete_task(task, {"answer": "Hello!"})
        self.assertTrue(task.complete)

        self.assertEqual(self.user.ranks.count(), 2)
        self.assertIn(pepsi_data['rank'], self.user.ranks.all())
        self.assertEqual(Notification.objects.count(), 3)
        self.assertEqual(self.user.notifications.count(), 1)

    def test_campaign_linker_assignee_rank(self):
        pepsi_data = self.generate_new_basic_campaign("Pepsi")
        fanta_data = self.generate_new_basic_campaign("Fanta")
        sprite_data = self.generate_new_basic_campaign("Sprite")

        self.assertEqual(Rank.objects.count(), 5)
        self.assertEqual(Track.objects.count(), 4)
        self.assertEqual(Campaign.objects.count(), 4)

        # creation queries to give another campaign ranks
        cola_to_pepsi = CampaignLinker.objects.create(
            name="From cola to PEPSI",
            out_stage=self.initial_stage,
            stage_with_user=self.initial_stage,
            target=pepsi_data["campaign"]
        )
        cola_to_fanta = CampaignLinker.objects.create(
            name="From cola to FANTA",
            out_stage=self.initial_stage,
            stage_with_user=self.initial_stage,
            target=fanta_data["campaign"]
        )
        cola_to_sprite = CampaignLinker.objects.create(
            name="From cola to SPRITE",
            out_stage=self.initial_stage,
            stage_with_user=self.initial_stage,
            target=sprite_data["campaign"]
        )

        # Prize Notification
        pepsi_not = Notification.objects.create(
            title="You access new rank from Pepsi campaign!",
            campaign=pepsi_data["campaign"]
        )
        sprite_not = Notification.objects.create(
            title="You access new rank from Pepsi campaign!",
            campaign=pepsi_data["campaign"]
        )
        pepsi_auto_not = AutoNotification.objects.create(
            notification=pepsi_not,
            go=AutoNotificationConstants.FORWARD
        )
        sprite_auto_not = AutoNotification.objects.create(
            notification=pepsi_not,
            go=AutoNotificationConstants.FORWARD
        )
        # approving links
        pepsi_init_stage = TaskStage.objects.create(
            name="Initial pepsi stage",
            x_pos=1,
            y_pos=1,
            chain=pepsi_data['chain'],
            is_creatable=True)
        ApproveLink.objects.create(
            campaign=pepsi_data['campaign'],
            linker=cola_to_pepsi,
            rank=pepsi_data['rank'],
            task_stage=pepsi_init_stage,
            notification=pepsi_auto_not,
            approved=True
        )

        self.initial_stage.json_schema = json.dumps({
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"]
        })
        task = self.create_initial_task()
        response = self.complete_task(task, {"answer": "Hello!"},
                                      whole_response=True)
        response_content = json.loads(response.content)
        task = Task.objects.get(id=response_content['id'])

        self.assertTrue(response_content['is_new_campaign'])
        self.assertTrue(task.complete)
        self.assertEqual(self.user.tasks.count(), 2)

        self.assertIn(pepsi_data['rank'], self.user.ranks.all())
        self.assertNotIn(sprite_data['rank'], self.user.ranks.all())

        self.assertEqual(Notification.objects.count(), 3)
        self.assertEqual(self.user.notifications.count(), 1)

    def test_campaign_list_user_campaigns(self):
        # check that employee doesn't have any rank
        response = self.get_objects(
            "campaign-list-user-campaigns", client=self.employee_client
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(to_json(response.content)['count'], 0)

        # join employee to campaign
        self.campaign.open = True
        self.campaign.save()
        response = self.get_objects("campaign-join-campaign",
                                    pk=self.campaign.id,
                                    client=self.employee_client)
        # response = self.employee_client.get(
        #     reverse("campaign-join-campaign", kwargs={"pk": self.campaign.id})
        # )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check that employee joined
        response = self.get_objects(
            "campaign-list-user-campaigns", client=self.employee_client
        )
        response_content = to_json(response.content)
        self.assertEqual(response_content["count"], 1)
        # self.assertEqual(
        #     response_content["results"][0]["notifications_count"], 0)

        # check serializer works properly
        notifications_count = 15
        [Notification.objects.create(
            title="Hello world",
            campaign=self.campaign
        ) for _ in range(notifications_count)]
        response = self.get_objects(
            "campaign-list-user-campaigns", client=self.employee_client
        )
        response_content = to_json(response.content)
        self.assertEqual(response_content["count"], 1)
        # self.assertEqual(
        #     response_content["results"][0]["notifications_count"], 0)

        # check serializer works properly
        notifications_count = int(notifications_count / 2)
        [Notification.objects.all().first().delete()
         for _ in range(notifications_count + 1)]
        response = self.get_objects(
            "campaign-list-user-campaigns", client=self.employee_client
        )
        response_content = to_json(response.content)
        self.assertEqual(response_content["count"], 1)
        # self.assertEqual(
        #     response_content["results"][0]["notifications_count"],
        #     0)