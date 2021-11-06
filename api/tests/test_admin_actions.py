from django.test import TestCase
from django.urls import reverse
from api.models import CustomUser, Campaign, Chain, ConditionalStage, TaskStage, Task, Case

class CustomUserAdminTest(TestCase):
    def setUp(self):
        self.url = reverse("admin:api_customuser_changelist")
        self.u_password = '123'
        self.user = CustomUser.objects.create_superuser(username="test", email='test@email.com',
                                                        password=self.u_password)
        self.user.is_staff = True
        self.user.save()
        self.new_user = CustomUser.objects.create_user(username="new_user", email='new_user@email.com',
                                                       password='new_user')
        self.employee = CustomUser.objects.create(username="empl", email='empl@email.com', password='empl')

        self.campaign = Campaign.objects.create(name="Campaign")
        self.another_campaign = Campaign.objects.create(name="Campaign")

        self.chain = Chain.objects.create(name="Chain", campaign=self.campaign)
        self.another_chain = Chain.objects.create(name="Chain", campaign=self.another_campaign)

        self.task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,chain=self.chain)
        self.another_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,chain=self.another_chain)

class TaskAdminTest(TestCase):
    def setUp(self):
        self.url = reverse("admin:api_task_changelist")

        self.u_password = '123'
        self.user = CustomUser.objects.create_superuser(username="test", email='test@email.com',
                                                        password=self.u_password)
        self.user.is_staff = True
        self.user.save()
        self.new_user = CustomUser.objects.create_user(username="new_user", email='new_user@email.com',
                                                       password='new_user')
        self.employee = CustomUser.objects.create(username="empl", email='empl@email.com', password='empl')

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
    def test_mark_complete(self):
        case = Case.objects.create()
        task = Task.objects.create(assignee=self.new_user, stage=self.task_stage, case=case)
        new_task_stage = TaskStage.objects.create(name="Task stage", x_pos=1, y_pos=1,
                                                  chain=self.chain)
        new_task_stage.in_stages.add(self.task_stage)

        data = {'action': 'make_completed',
                '_selected_action': [task.id]}

        self.client.login(username=self.user.username, password=self.u_password)
        self.client.post(self.url, data, follow=True)
        self.assertTrue(Task.objects.get(id=task.id).complete)

    def test_mark_complete_force(self):
        case = Case.objects.create()
        tasks = [Task.objects.create(assignee=self.new_user, stage=self.task_stage, case=case,
                                     complete=False) for x in range(5)]
        tasks_complete = tasks[:3]
        data = {'action': 'make_completed_force',
                '_selected_action': [t.id for t in tasks_complete]}
        self.client.login(username=self.user.username, password=self.u_password)
        response = self.client.post(self.url, data, follow=True)
        self.assertEqual(list(Task.objects.filter(complete=True)),
                         list(Task.objects.filter(pk__in=data['_selected_action'])))