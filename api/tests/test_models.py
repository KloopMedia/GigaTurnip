from django.test import TestCase
import django

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
	pass


class SchemaProviderModelTest(TestCase):
	pass


class CampaignModelTest(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.campaign = Campaign.objects.create(name="Test campaign")

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
	pass


class ChainModelTest(TestCase):
	pass


class StageModelTest(TestCase):
	pass


class TaskStageModelTest(TestCase):
	pass


class WebHookStageModelTest(TestCase):
	pass


class ConditionalStageModelTest(TestCase):
	pass


class CaseModelTest(TestCase):
	pass


class TaskModelTest(TestCase):
	pass


class RankModelTest(TestCase):
	pass


class TrackModelTest(TestCase):
	pass


class RankRecordModelTest(TestCase):
	pass


class RankLimitModelTest(TestCase):
	pass
