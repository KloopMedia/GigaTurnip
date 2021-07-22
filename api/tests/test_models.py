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
	pass


class SchemaProviderModelTest(TestCase):
	pass


class CampaignModelTest(TestCase):
	@classmethod
	def setUpTestData(cls):
		Campaign.objects.create(name="Test campaign")

	def test_name(self):
		campaign = Campaign.objects.get(id=1)
		field_name = campaign._meta.get_field('name').verbose_name
		self.assertEqual(field_name, 'name')


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

