from django.test import TestCase
import django
django.setup()
from api.models import CustomUser, BaseModel, SchemaProvider, Campaign, \
	CampaignManagement, Chain, Stage, TaskStage, \
	WebHookStage, ConditionalStage, Case, Task, \
	Rank, Track, RankRecord, RankLimit


class CustomUserModelTest(TestCase):
	pass


class BaseModelModelTest(TestCase):
	# @classmethod
	# def setUpTestData(cls):
	# 	BaseModel.objects.create(name="Test basemodel")
	#
	# def test_labels(self):
	# 	base_model = BaseModel.objects.get(id=1)
	#
	# 	field_name = base_model._meta.get_field('name').verbose_name
	# 	field_description = base_model._meta.get_field('name').verbose_name
	pass

class SchemaProviderModelTest(TestCase):
	pass


class CampaignModelTest(TestCase):
	@classmethod
	def setUpTestData(cls):
		Campaign.objects.create(name="Test campaign")

	def test_labels(self):
		campaign = Campaign.objects.get(id=1)

		field_name = campaign._meta.get_field('name').verbose_name
		field_description = campaign._meta.get_field('description').verbose_name
		field_default_track = campaign._meta.get_field('default_track').verbose_name
		field_managers = campaign._meta.get_field('managers').verbose_name

		self.assertEqual(field_name, 'name')
		self.assertEqual(field_description, 'description')
		self.assertEqual(field_default_track, 'default track')
		self.assertEqual(field_managers, 'managers')


	def test_description_is_blank(self):
		campaign = Campaign.objects.get(id=1)
		is_blank = campaign._meta.get_field('description').blank
		self.assertEqual(is_blank, True)

	def test_default_track_is_blank(self):
		campaign = Campaign.objects.get(id=1)
		is_blank = campaign._meta.get_field('default_track').blank
		self.assertEqual(is_blank, True)

	def test_object_name(self):
		campaign = Campaign.objects.get(id=1)
		expected_object_name = str("Campaign: " + campaign.name)
		self.assertEqual(expected_object_name, str(campaign))


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

