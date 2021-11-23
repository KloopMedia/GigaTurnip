import django, json, random, os
from django.forms.models import model_to_dict
# from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import threading

django.setup()

from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, override_settings
from django.contrib.auth.models import Group
from api.models import CustomUser, Campaign, Chain, ConditionalStage, TaskStage, Rank, RankLimit, Task, RankRecord, \
    Track, CampaignManagement, Stage, Case
from rest_framework import status


class TaskTest(APITestCase):
    # todo: test release_assignment, request_assignment, list_displayed_previous
    def setUp(self):
        self.url_campaign = reverse("campaign-list")
        self.url_chain = reverse("chain-list")
        self.url_conditional_stage = reverse('conditionalstage-list')
        self.url_task_stage = reverse('taskstage-list')
        self.url_tasks = reverse('task-list')
        self.url_webhook_quiz = "https://us-central1-journal-bb5e3.cloudfunctions.net/check_quiz_responses"

        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.new_user = CustomUser.objects.create_user(username="new_user", email='new_user@email.com',
                                                       password='new_user')
        self.employee = CustomUser.objects.create(username="empl", email='empl@email.com', password='empl')

        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(name="Campaign")
        self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        self.conditional_stage = ConditionalStage.objects.create(name="Conditional Stage", x_pos=1, y_pos=1,
                                                                 chain=self.chain)
        self.task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                   chain=self.chain)
        self.another_campaign = Campaign.objects.create(name="Campaign")
        self.another_chain = Chain.objects.create(name="Chain", campaign=self.another_campaign)
        self.another_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                           chain=self.another_chain)

        self.campaign_json = {"name": "campaign", "description": "description"}
        self.chain_json = {"name": "chain", "description": "description", "campaign": None}
        self.task_stage_json = {
            "name": "conditional_stage",
            "chain": None,
            "x_pos": 1,
            "y_pos": 1
        }
        self.task_stage_json_modified = self.task_stage_json
        self.task_stage_json_modified['name'] = "Modified conditional stage"
        self.campaign_creator_group = Group.objects.create(name='campaign_creator')

    ## there is task_stage after task. new tasks are creating depending on
    def function(self, id):
        return self.client.patch(self.url_tasks + f"{id}/", {"complete": True})


    def test_complete_next_task_stage_on_dublicate(self):
        new_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                  chain=self.chain)
        new_task_stage.in_stages.add(self.task_stage)
        self.new_user.managed_campaigns.add(self.campaign)

        case = Case.objects.create()
        task = Task.objects.create(assignee=self.user, stage=self.task_stage, case=case)

        pool = ThreadPool(2)
        pool.map(self.function, [task.id, task.id])
        pool.close()
        pool.join()
        response = self.client.patch(self.url_tasks + f"{task.id}/", {"complete": True})
        created_tasks = Task.objects.filter(case=case).filter(stage__in_stages__in=[self.task_stage])
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_complete_next_task_stage_on_dublicate_differend_tasks(self):
        new_another_task_stage = TaskStage.objects.create(name="another Task stage", x_pos=1, y_pos=1,
                                                          chain=self.another_chain)

        new_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                  chain=self.chain)
        new_task_stage.in_stages.add(self.task_stage)
        new_another_task_stage.in_stages.add(self.another_task_stage)
        self.new_user.managed_campaigns.add(self.campaign)

        case = Case.objects.create()
        another_case = Case.objects.create()
        task = Task.objects.create(assignee=self.user, stage=self.task_stage, case=case)
        another_task = Task.objects.create(assignee=self.user, stage=self.another_task_stage, case=another_case)

        pool = ThreadPool(2)
        pool.map(self.function, [task.id, another_task.id])
        pool.close()
        pool.join()
        # response = self.client.patch(self.url_tasks + f"{task.id}/", {"complete": True})
        created_tasks = Task.objects.filter(case=case).filter(stage__in_stages__in=[self.task_stage])
        # self.assertEqual(response.status_code, status.HTTP_200_OK)

