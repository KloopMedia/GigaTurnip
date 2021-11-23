import django, json, random
from django.forms.models import model_to_dict

django.setup()

from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from django.contrib.auth.models import Group
from api.models import CustomUser, Campaign, Chain, ConditionalStage, TaskStage, Rank, RankLimit, Task, RankRecord, \
    Track, CampaignManagement, Stage, Case
from rest_framework import status

class DefTest(APITestCase):
    def setUp(self):
        self.url_tasks = reverse('task-list')
        self.url = "https://us-central1-journal-bb5e3.cloudfunctions.net/check_quiz_responses"
        self.new_user = CustomUser.objects.create_user(username="new_user", email='new_user@email.com', password='new_user')
        self.user = CustomUser.objects.create_user(username="test", email='test@email.com', password='test')
        self.campaign = Campaign.objects.create(name="Campaign")
        self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        self.task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                   chain=self.chain)
        self.new_task_stage = TaskStage.objects.create(name="NEW Task stage", x_pos=1, y_pos=1,
                                                   chain=self.chain)
        self.new_user.managed_campaigns.add(self.campaign)
        self.client.force_authenticate(user=self.user)