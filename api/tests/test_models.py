from django.test import TestCase
import django
from django.db import connection

django.setup()
from api.models import CustomUser, BaseModel, SchemaProvider, Campaign, \
	CampaignManagement, Chain, Stage, TaskStage, \
	WebHookStage, ConditionalStage, Case, Task, \
	Rank, Track, RankRecord, RankLimit


class CustomUserModelTest(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.user = CustomUser.objects.create(username="Test custom user", email='example@inbox.com')

	def test_object_name(self):
		expected_object_name = str(self.user.email + " " + self.user.last_name)
		self.assertEqual(expected_object_name, str(self.user))

	def test_custom_user_can_be_attached_to_multiple_ranks(self):
		ranks = [Rank.objects.create(name=_) for _ in range(3)]

		for rank in ranks:
			rank.users.add(self.user)

		self.assertEqual(len(ranks), self.user.ranks.count())
		for rank in ranks:
			self.assertIn(rank, self.user.ranks.all())


class BaseModelModelTest(TestCase):
	pass  # TODO: how test abstract model


class SchemaProviderModelTest(TestCase):
	pass  # TODO: how test abstract model


class CampaignModelTest(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.campaign = Campaign.objects.create(name="Test campaign!!!AAAAAAA IM IN TESTS")

	def test_labels(self):
		field_name = self.campaign._meta.get_field('name').verbose_name
		field_description = self.campaign._meta.get_field('description').verbose_name
		field_default_track = self.campaign._meta.get_field('default_track').verbose_name
		field_managers = self.campaign._meta.get_field('managers').verbose_name

		self.assertEqual(field_name, 'name')
		self.assertEqual(field_description, 'description')
		self.assertEqual(field_default_track, 'default track')
		self.assertEqual(field_managers, 'managers')

	def test_description_is_blank(self):
		is_blank = self.campaign._meta.get_field('description').blank
		self.assertTrue(is_blank)

	def test_default_track_is_blank(self):
		is_blank = self.campaign._meta.get_field('default_track').blank
		self.assertTrue(is_blank)

	def test_object_name(self):
		expected_object_name = str("Campaign: " + self.campaign.name)
		self.assertEqual(expected_object_name, str(self.campaign))

	def test_campaign_can_be_attached_to_multiple_managers(self):

		managers = [CustomUser.objects.create(username=i) for i in range(3)]

		for manager in managers:
			manager.managed_campaigns.add(self.campaign)

		self.assertEqual(len(managers), self.campaign.managers.count())
		for manager in managers:
			self.assertIn(manager, self.campaign.managers.all())


class CampaignManagementModelTest(TestCase):
	@classmethod
	def setUpTestData(cls):
		new_user = CustomUser.objects.create(username="Test custom user", email='example12324@inbox.com')
		new_campaign = Campaign.objects.create(name="Test campaign 12324!")
		cls.campaign_management = CampaignManagement.objects.create(user=new_user, campaign=new_campaign)

	def test_labels(self):
		field_user = self.campaign_management._meta.get_field('user').verbose_name
		field_campaing = self.campaign_management._meta.get_field('campaign').verbose_name

		self.assertEqual(field_user, 'user')
		self.assertEqual(field_campaing, 'campaign')

	def test_foreign_field_user(self):
		self.assertEqual(self.campaign_management.user.email, 'example12324@inbox.com')

	def test_foreign_field_campaign(self):
		self.assertEqual(self.campaign_management.campaign.name, 'Test campaign 12324!')


class ChainModelTest(TestCase):
	@classmethod
	def setUpTestData(cls):
		campaign = Campaign.objects.create(name="Test campaign 12324!")
		cls.chain = Chain.objects.create(name="New chain for tests 12324!", campaign=campaign)

	def test_labels(self):
		field_name = self.chain._meta.get_field('name').verbose_name
		field_description = self.chain._meta.get_field('description').verbose_name
		field_campaign = self.chain._meta.get_field('campaign').verbose_name

		self.assertEqual(field_name, 'name')
		self.assertEqual(field_description, 'description')
		self.assertEqual(field_campaign, 'campaign')

	def test_foreign_key_campaign(self):
		self.assertEqual(self.chain.campaign.name, "Test campaign 12324!")

	def test_object_name(self):
		chain_name = "Chain: " + self.chain.name
		campaign_str = self.chain.campaign.__str__()
		expected_object_name = str(chain_name + " " + campaign_str)
		self.assertEqual(expected_object_name, str(self.chain))


class StageModelTest(TestCase):
	@classmethod
	def setUpTestData(cls):
		campaign = Campaign.objects.create(name="Test campaign 12324!")
		chain = Chain.objects.create(name="New chain for tests 12324!", campaign=campaign)
		cls.stage = Stage.objects.create(x_pos=1, y_pos=1, chain=chain)

	def test_labels(self):
		field_name = self.stage._meta.get_field('name').verbose_name
		field_description = self.stage._meta.get_field('description').verbose_name
		field_x_pos = self.stage._meta.get_field('x_pos').verbose_name
		field_y_pos = self.stage._meta.get_field('y_pos').verbose_name
		field_chain = self.stage._meta.get_field('chain').verbose_name
		field_in_stages = self.stage._meta.get_field('in_stages').verbose_name

		self.assertEqual(field_name, 'name')
		self.assertEqual(field_description, 'description')
		self.assertEqual(field_x_pos, 'x pos')
		self.assertEqual(field_y_pos, 'y pos')
		self.assertEqual(field_chain, 'chain')
		self.assertEqual(field_in_stages, 'in stages')

	def test_foreign_field_chain(self):
		self.assertEqual(self.stage.chain.campaign.name, "Test campaign 12324!")
		self.assertEqual(self.stage.chain.name, "New chain for tests 12324!")

	def test_chain_can_be_attached_to_multiple_stages(self):
		# managers = [CustomUser.objects.create(username=i) for i in range(3)]
		#
		# for manager in managers:
		# 	manager.managed_campaigns.add(self.campaign)
		#
		# self.assertEqual(len(managers), self.campaign.managers.count())
		# for manager in managers:
		# 	self.assertIn(manager, self.campaign.managers.all())

		in_stages = []

	def test_object_name(self):
		stage = "Stage: " + self.stage.name + " "
		chain = self.stage.chain.__str__()
		self.assertEqual(str(self.stage), str(stage + chain))


class TaskStageModelTest(TestCase):
	@classmethod
	def setUpTestData(cls):
		campaign = Campaign.objects.create(name="Test campaign 12324!")
		chain = Chain.objects.create(name="New chain for tests 12324!", campaign=campaign)
		cls.task_stage = TaskStage.objects.create(chain=chain, x_pos=1, y_pos=1)

	def test_labels(self):
		field_name = self.task_stage._meta.get_field('name').verbose_name
		field_description = self.task_stage._meta.get_field('description').verbose_name
		field_x_pos = self.task_stage._meta.get_field('x_pos').verbose_name
		field_y_pos = self.task_stage._meta.get_field('y_pos').verbose_name
		field_chain = self.task_stage._meta.get_field('chain').verbose_name
		field_in_stages = self.task_stage._meta.get_field('in_stages').verbose_name

		field_copy_input = self.task_stage._meta.get_field('copy_input').verbose_name
		field_allow_multiple_files = self.task_stage._meta.get_field('allow_multiple_files').verbose_name
		field_is_creatable = self.task_stage._meta.get_field('is_creatable').verbose_name
		field_displayed_prev_stages = self.task_stage._meta.get_field('displayed_prev_stages').verbose_name
		field_assign_user_by = self.task_stage._meta.get_field('assign_user_by').verbose_name
		field_assign_user_from_stage = self.task_stage._meta.get_field('assign_user_from_stage').verbose_name

		field_json_schema = self.task_stage._meta.get_field('json_schema').verbose_name
		field_ui_schema = self.task_stage._meta.get_field('ui_schema').verbose_name
		field_library = self.task_stage._meta.get_field('library').verbose_name

		self.assertEqual(field_name, 'name')
		self.assertEqual(field_description, 'description')
		self.assertEqual(field_x_pos, 'x pos')
		self.assertEqual(field_y_pos, 'y pos')
		self.assertEqual(field_chain, 'chain')
		self.assertEqual(field_in_stages, 'in stages')

		self.assertEqual(field_copy_input, "copy input")
		self.assertEqual(field_allow_multiple_files, "allow multiple files")
		self.assertEqual(field_is_creatable, "is creatable")
		self.assertEqual(field_displayed_prev_stages, "displayed prev stages")
		self.assertEqual(field_assign_user_by, "assign user by")
		self.assertEqual(field_assign_user_from_stage, "assign user from stage")

		self.assertEqual(field_json_schema, "json schema")
		self.assertEqual(field_ui_schema, "ui schema")
		self.assertEqual(field_library, "library")

	def test_foreign_field_chain(self):
		self.assertEqual(self.task_stage.chain.campaign.name, "Test campaign 12324!")
		self.assertEqual(self.task_stage.chain.name, "New chain for tests 12324!")


class WebHookStageModelTest(TestCase):  # TODO: finish up tests for web hook stage
	@classmethod
	def setUpTestData(cls):
		campaign = Campaign.objects.create(name="Test campaign 12324!")
		chain = Chain.objects.create(name="New chain for tests 12324!", campaign=campaign)
		cls.web_hook_stage = WebHookStage.objects.create(chain=chain, x_pos=1, y_pos=1)

	def test_labels(self):
		field_name = self.web_hook_stage._meta.get_field('name').verbose_name
		field_description = self.web_hook_stage._meta.get_field('description').verbose_name
		field_x_pos = self.web_hook_stage._meta.get_field('x_pos').verbose_name
		field_y_pos = self.web_hook_stage._meta.get_field('y_pos').verbose_name
		field_chain = self.web_hook_stage._meta.get_field('chain').verbose_name
		field_in_stages = self.web_hook_stage._meta.get_field('in_stages').verbose_name

		field_json_schema = self.web_hook_stage._meta.get_field('json_schema').verbose_name
		field_ui_schema = self.web_hook_stage._meta.get_field('ui_schema').verbose_name
		field_library = self.web_hook_stage._meta.get_field('library').verbose_name

		field_web_hook_address = self.web_hook_stage._meta.get_field('web_hook_address').verbose_name

		self.assertEqual(field_name, 'name')
		self.assertEqual(field_description, 'description')
		self.assertEqual(field_x_pos, 'x pos')
		self.assertEqual(field_y_pos, 'y pos')
		self.assertEqual(field_chain, 'chain')
		self.assertEqual(field_in_stages, 'in stages')

		self.assertEqual(field_json_schema, "json schema")
		self.assertEqual(field_ui_schema, "ui schema")
		self.assertEqual(field_library, "library")

		self.assertEqual(field_web_hook_address, "web hook address")


# def test_object_name(self):
# 	expected_name = str("Web Hook Stage Filler for " + self.web_hook_stage.stage.__str__())
# 	self.assertEqual(expected_name, str(self.web_hook_stage))


class ConditionalStageModelTest(TestCase):
	@classmethod
	def setUpTestData(cls):
		campaign = Campaign.objects.create(name="Test campaign 12324!")
		chain = Chain.objects.create(name="New chain for tests 12324!", campaign=campaign)
		cls.conditional_stage = ConditionalStage.objects.create(chain=chain, x_pos=1, y_pos=1)

	def test_labels(self):
		field_conditions = self.conditional_stage._meta.get_field('conditions').verbose_name
		field_pingpong = self.conditional_stage._meta.get_field('pingpong').verbose_name

		self.assertEqual(field_conditions, 'conditions')
		self.assertEqual(field_pingpong, 'pingpong')


class CaseModelTest(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.case = Case.objects.create()

	def test_object_name(self):
		self.assertEqual(str(self.case), str("Case #" + str(self.case.id)))


class TaskModelTest(TestCase):
	@classmethod
	def setUpTestData(cls):
		assignee = CustomUser.objects.create(username="Test custom user", email='example12324@inbox.com')
		campaign = Campaign.objects.create(name="Test campaign 12324!")
		chain = Chain.objects.create(name="New chain for tests 12324!", campaign=campaign)
		stage = TaskStage.objects.create(chain=chain, x_pos=1, y_pos=1)
		cls.my_case = case = Case.objects.create()
		cls.task = Task.objects.create(assignee=assignee, stage=stage, case=case)

	def test_labels(self):
		field_assignee = self.task._meta.get_field("assignee").verbose_name
		field_stage = self.task._meta.get_field("stage").verbose_name
		field_case = self.task._meta.get_field("case").verbose_name
		field_responses = self.task._meta.get_field("responses").verbose_name
		field_in_tasks = self.task._meta.get_field("in_tasks").verbose_name
		field_complete = self.task._meta.get_field("complete").verbose_name

		self.assertEqual(field_assignee, "assignee")
		self.assertEqual(field_stage, "stage")
		self.assertEqual(field_case, "case")
		self.assertEqual(field_responses, "responses")
		self.assertEqual(field_in_tasks, "in tasks")
		self.assertEqual(field_complete, "complete")

	def test_foreign_field_assignee(self):
		self.assertEqual(self.task.assignee.username, "Test custom user")
		self.assertEqual(self.task.assignee.email, "example12324@inbox.com")

	def test_foreign_field_stage(self):
		self.assertEqual(self.task.stage.chain.name, "New chain for tests 12324!")
		self.assertEqual(self.task.stage.chain.campaign.name, "Test campaign 12324!")
		self.assertEqual(self.task.stage.x_pos, 1)
		self.assertEqual(self.task.stage.y_pos, 1)

	def test_foreign_field_case(self):
		self.assertEqual(self.task.case.id, self.my_case.id)

	def test_object_name(self):
		expected_name = str("Task #:" + str(self.task.id) + self.task.case.__str__())
		self.assertEqual(str(self.task), expected_name)


class RankModelTest(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.rank = Rank.objects.create(name='My rank 12324!')

	def test_labels(self):
		field_name = self.rank._meta.get_field("name").verbose_name
		field_description = self.rank._meta.get_field("description").verbose_name
		field_stages = self.rank._meta.get_field("stages").verbose_name

		self.assertEqual(field_name,'name')
		self.assertEqual(field_description,'description')
		self.assertEqual(field_stages,'stages')

	def test_rank_can_be_attached_to_multiple_stages(self):
		campaign = Campaign.objects.create(name="Test campaign 12324!")
		chain = Chain.objects.create(name="New chain for tests 12324!", campaign=campaign)

		stages = [TaskStage.objects.create(chain=chain, x_pos=1, y_pos=1) for i in range(3)]

		for stage in stages:
			stage.ranks.add(self.rank)

		self.assertEqual(len(stages), self.rank.stages.count())
		for stage in stages:
			self.assertIn(stage, self.rank.stages.all())

	def test_object_name(self):
		self.assertEqual(str(self.rank), self.rank.name)


class TrackModelTest(TestCase):
	pass


class RankRecordModelTest(TestCase):
	pass


class RankLimitModelTest(TestCase):
	pass
