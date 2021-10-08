from django.http import Http404, HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from rest_access_policy import AccessPolicy
from api.models import Campaign, TaskStage, Track
from . import utils


class CampaignAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",
			# "condition": "is_manager_exist"
		},
		{
			"action": ["create"],
			"principal": ["group:campaign_creator"],
			"effect": "allow"
		},
		{
			"action": ["destroy"],
			"principal": ["*"],
			"effect": "deny"
		},
		{
			"action": ["partial_update"],
			"principal": ["authenticated"],
			"effect": "allow",
			"condition": "is_manager"
		},
		{
			"action": ["retrieve"],
			"principal": ["authenticated"],
			"effect": "allow",
			"condition": "is_manager"
		}
	]

	def is_manager(self, request, view, action) -> bool:
		campaign = view.get_object()
		managers = campaign.managers.all()

		return request.user in managers


class ChainAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["create"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_create"

		},
		{
			"action": ["retrieve"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager"

		},
		{
			"action": ["partial_update"],
			"principal": ["authenticated"],
			"effect": "allow",
			"condition": "is_manager"

		},
		{
			"action": ["destroy"],
			"principal": ["authenticated"],
			"effect": "deny"
		}
	]

	def is_manager(self, request, view, action) -> bool:
		chain = view.get_object()
		managers = chain.campaign.managers.all()

		return request.user in managers

	def is_manager_create(self, request, view, action) -> bool:
		# при вызове action list вызывается эта функция и request.POST.get('campaign') = none,
		# из-за этого всё крашится
		if not request.POST.get('campaign'):
			return False

		campaign_id = int(request.POST.get('campaign'))
		campaign = Campaign.objects.get(id=campaign_id)
		managers = campaign.managers.all()

		return request.user in managers

	def is_manager_exist(self, request, view, action) -> bool:
		try:
			return bool(Campaign.objects.get(managers=request.user))
		except Campaign.DoesNotExist:
			raise Http404("Product Couldn't be found")


class TaskAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["destroy"],
			"principal": "*",
			"effect": "deny",
		},
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_or_have_assignee_task"
		},
		{
			"action": ["retrieve"],
			"principal": "authenticated",
			"effect": "allow",
			"condition_expression": 'is_assignee or is_manager_of_campaign'
		},
		{
			"action": ["create"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_can_create"
		},
		{
			"action": ["user_selectable"],
			"principal": "*",
			"effect": "allow",
			"condition": "is_user_can_request_assignment"
		},
		{
			"action": ["user_relevant"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_can_create"
		},
		{
			"action": ["release_assignment"],
			"principal": "*",
			"effect": "deny",
		},
		{
			"action": ["request_assignment"],
			"principal": "*",
			"effect": "allow",
			"condition": "is_user_can_request_assignment"
		},
		{
			"action": ["update", "partial_update"],
			"principal": "authenticated",
			"effect": "allow",
			"condition_expression": "is_assignee and is_not_complete"
		}
	]

	def is_assignee(self, request, view, action):
		task = view.get_object()
		return request.user == task.assignee
from api.models import Campaign, TaskStage, Track
from . import utils

class CampaignAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",
			# "condition": "is_manager_exist"
		},
		{
			"action": ["create"],
			"principal": ["group:campaign_creator"],
			"effect": "allow"
		},
		{
			"action": ["destroy"],
			"principal": ["*"],
			"effect": "deny"
		},
		{
			"action": ["partial_update"],
			"principal": ["*"],
			"effect": "allow",
			"condition": "is_manager"
		},
		{
			"action": ["retrieve"],
			"principal": ["*"],
			"effect": "allow",
			"condition": "is_manager"
		}
	]

	def is_manager(self, request, view, action) -> bool:
		campaign = view.get_object()
		managers = campaign.managers.all()

		return request.user in managers

	def is_manager_exist(self, request, view, action) -> bool:
		try:
			return bool(Campaign.objects.get(managers=request.user))
		except Campaign.DoesNotExist:
			raise Http404("Product Couldn't be found11")


class ChainAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["create"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_create"

		},
		{
			"action": ["retrieve"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager"

		},
		{
			"action": ["partial_update"],
			"principal": ["authenticated"],
			"effect": "allow",
			"condition": "is_manager"

		},
		{
			"action": ["destroy"],
			"principal": ["authenticated"],
			"effect": "deny"
		}
	]

	def is_manager(self, request, view, action) -> bool:
		chain = view.get_object()
		managers = chain.campaign.managers.all()

		return request.user in managers

	def is_manager_create(self, request, view, action) -> bool:
		# при вызове action list вызывается эта функция и request.POST.get('campaign') = none,
		# из-за этого всё крашится
		if not request.POST.get('campaign'):
			return False

		campaign_id = int(request.POST.get('campaign'))
		campaign = Campaign.objects.get(id=campaign_id)
		managers = campaign.managers.all()

		return request.user in managers

	def is_manager_exist(self, request, view, action) -> bool:
		return bool(Campaign.objects.filter(managers=request.user))



class TaskAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["destroy"],
			"principal": "*",
			"effect": "deny",
		},
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_or_have_assignee_task"
		},
		{
			"action": ["retrieve"],
			"principal": "authenticated",
			"effect": "allow",
			"condition_expression": 'is_assignee or is_manager_of_campaign'
		},
		{
			"action": ["create"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_can_create"
		},
		{
			"action": ["user_selectable"],
			"principal": "*",
			"effect": "allow",
			"condition": "is_user_can_request_assignment"
		},
		{
			"action": ["user_relevant"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_can_create"
		},
		{
			"action": ["release_assignment"],
			"principal": "*",
			"effect": "deny",
		},
		{
			"action": ["request_assignment"],
			"principal": "*",
			"effect": "allow",
			"condition": "is_user_can_request_assignment"
		},
		{
			"action": ["update", "partial_update"],
			"principal": "authenticated",
			"effect": "allow",
			"condition_expression": "is_assignee and is_not_complete"
		}
	]

	def is_assignee(self, request, view, action):
		task = view.get_object()
		return request.user == task.assignee

	def is_not_complete(self, request, view, action):
		task = view.get_object()
		return task.complete is False

	def is_user_can_request_assignment(self, request, view, action):
		is_have_access = utils.filter_for_user_selectable_tasks(view.queryset, request)
		return bool(is_have_access)

	# if user have relevant task stages
	def is_can_create(self, request, view, action):
		queryset = TaskStage.objects.all()
		relevant_stages = utils.filter_for_user_creatable_stages(queryset, request)
		new_task_based_on_relevant_stages = relevant_stages.filter(id=request.data.get('stage'))
		return bool(new_task_based_on_relevant_stages)

	def is_manager_or_have_assignee_task(self, request, view, action):
		is_manager = bool(utils.filter_tasks_for_manager(view.queryset, request))
		is_have_assignee = bool(utils.filter_assignee_tasks(view.queryset, request))
		return is_have_assignee or is_manager

	def is_manager_of_campaign(self, request, view, action):
		managed_campaigns = utils.filter_managed_campaigns(request)
		task = view.get_object()
		task_campaign = task.stage.chain.campaign
		return task_campaign in managed_campaigns


class TaskStageAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",
			"condition_expression": "is_manager_exist or is_user_relevant"
		},
		{
			"action": ["create"],
			"principal": "authenticated",
			"effect": "allow",
			"condition_expression": "is_manager_exist or is_user_relevant"
		},
		{
			"action": ["retrieve"],
			"principal": "authenticated",
			"effect": "allow",
			"condition_expression": "is_manager_exist or is_user_relevant"
		},
		{
			"action": ["partial_update"],
			"principal": "authenticated",
			"effect": "allow",
			"condition_expression": "is_manager or is_user_relevant"
		},
		{
			"action": ["user_relevant"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_user_relevant"
		},
		{
			"action": ["destroy"],
			"principal": "authenticated",
			"effect": "deny",
		}
	]

	def is_manager(self, request, view, action) -> bool:
		conditional_stage = view.get_object()
		managers = conditional_stage.сhain.campaign.managers.all()

		return request.user in managers

	def is_manager_exist(self, request, view, action) -> bool:
		return bool(Campaign.objects.filter(managers=request.user))

	def is_user_relevant(self, request, view, action) -> bool:
		queryset = TaskStage.objects.all()
		filtered_stages = utils.filter_for_user_creatable_stages(queryset, request)

		return bool(filtered_stages)


class ConditionalStageAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "*",
			"effect": "allow",
			"condition": "is_manager_exist"

		},
		{
			"action": ["create",],
			"principal": "*",
			"effect": "allow",
			"condition": "is_manager_exist"

		},
		{
			"action": ["retrieve",],
			"principal": "*",
			"effect": "allow",
			"condition": "is_manager"

		},
		{
			"action": ["partial_update"],
			"principal": "*",
			"effect": "allow",
			"condition": "is_manager"

		},
		{
			"action": ["destroy"],
			"principal": "*",
			"effect": "deny",
		}
	]

	def is_manager(self, request, view, action) -> bool:
		conditional_stage = view.get_object()
		managers = conditional_stage.сhain.campaign.managers.all()

		return request.user in managers

	def is_manager_exist(self, request, view, action) -> bool:
		return bool(Campaign.objects.filter(managers=request.user))


class RankAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["create"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["retrieve", "partial_update"],
			"principal": ["authenticated"],
			"effect": "allow",
			"condition": "is_manager"

		},
		{
			"action": ["destroy"],
			"principal": ["authenticated"],
			"effect": "deny"
		}
	]

	def is_manager_exist(self, request, view, action) -> bool:
		return bool(Campaign.objects.filter(managers=request.user))

	def is_manager(self, request, view, action) -> bool:

		rank = view.get_object()

		tracks = Track.objects.filter(ranks__in=[rank.id]).all()
		for track in tracks:
			campaign = Campaign.objects.get(id=track.campaign_id)
			managers = campaign.managers.all()
			if request.user in managers:
				return True
		return False


class RankLimitAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["create"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["retrieve", "partial_update"],
			"principal": ["authenticated"],
			"effect": "allow",
			"condition": "is_can_create"

		},
		{
			"action": ["destroy"],
			"principal": ["authenticated"],
			"effect": "deny"
		}
	]

	def is_manager_exist(self, request, view, action) -> bool:
		return bool(Campaign.objects.filter(managers=request.user))

	def is_not_complete(self, request, view, action):
		task = view.get_object()
		return task.complete is False

	def is_user_can_request_assignment(self, request, view, action):
		is_have_access = utils.filter_for_user_selectable_tasks(view.queryset, request)
		return bool(is_have_access)

	# if user have relevant task stages
	def is_can_create(self, request, view, action):
		queryset = TaskStage.objects.all()
		relevant_stages = utils.filter_for_user_creatable_stages(queryset, request)
		new_task_based_on_relevant_stages = relevant_stages.filter(id=request.data.get('stage'))
		return bool(new_task_based_on_relevant_stages)

	def is_manager_or_have_assignee_task(self, request, view, action):
		is_manager = bool(utils.filter_tasks_for_manager(view.queryset, request))
		is_have_assignee = bool(utils.filter_assignee_tasks(view.queryset, request))
		return is_have_assignee or is_manager

	def is_manager_of_campaign(self, request, view, action):
		managed_campaigns = utils.filter_managed_campaigns(request)
		task = view.get_object()
		task_campaign = task.stage.chain.campaign
		return task_campaign in managed_campaigns


class TaskStageAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_user_relevant"
		},
		{
			"action": ["create"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["retrieve"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_user_relevant"
		},
		{
			"action": ["partial_update"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager"
		},
		{
			"action": ["user_relevant"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_user_relevant"
		},
		{
			"action": ["destroy"],
			"principal": "authenticated",
			"effect": "deny",
		}
	]

	def is_manager(self, request, view, action) -> bool:
		task_stage = view.get_object()
		managers = task_stage.managers.all()

	def is_manager(self, request, view, action) -> bool:
		conditional_stage = view.get_object()
		managers = conditional_stage.сhain.campaign.managers.all()

		return request.user in managers

	def is_manager_exist(self, request, view, action) -> bool:
		return bool(Campaign.objects.filter(managers=request.user))

	def is_user_relevant(self, request, view, action) -> bool:
		queryset = TaskStage.objects.all()
		filtered_stages = utils.filter_for_user_creatable_stages(queryset, request)

		return bool(filtered_stages)


class ConditionalStageAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "*",
			"effect": "allow",
			"condition": "is_manager_exist"

		},
		{
			"action": ["create",],
			"principal": "*",
			"effect": "allow",
			"condition": "is_manager_exist"

		},
		{
			"action": ["retrieve",],
			"principal": "*",
			"effect": "allow",
			"condition": "is_manager"

		},
		{
			"action": ["partial_update"],
			"principal": "*",
			"effect": "allow",
			"condition": "is_manager"

		},
		{
			"action": ["destroy"],
			"principal": "*",
			"effect": "deny",
		}
	]

	def is_manager(self, request, view, action) -> bool:
		conditional_stage = view.get_object()
		managers = conditional_stage.сhain.campaign.managers.all()

		return request.user in managers

	def is_manager_exist(self, request, view, action) -> bool:
		return bool(Campaign.objects.filter(managers=request.user))


class RankAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["create"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["retrieve", "partial_update"],
			"principal": ["authenticated"],
			"effect": "allow",
			"condition": "is_manager"

		},
		{
			"action": ["destroy"],
			"principal": ["authenticated"],
			"effect": "deny"
		}
	]

	def is_manager_exist(self, request, view, action) -> bool:
		return bool(Campaign.objects.filter(managers=request.user))

	def is_manager(self, request, view, action) -> bool:

		rank = view.get_object()

		tracks = Track.objects.filter(ranks__in=[rank.id]).all()
		for track in tracks:
			campaign = Campaign.objects.get(id=track.campaign_id)
			managers = campaign.managers.all()
			if request.user in managers:
				return True
		return False


class RankLimitAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["create"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["retrieve", "partial_update"],
			"principal": ["authenticated"],
			"effect": "allow",
			"condition": "is_manager"

		},
		{
			"action": ["destroy"],
			"principal": ["authenticated"],
			"effect": "deny"
		}
	]

	def is_manager_exist(self, request, view, action) -> bool:
		return bool(Campaign.objects.filter(managers=request.user))

	def is_manager(self, request, view, action) -> bool:

		rank_limit = view.get_object()

		tracks = Track.objects.filter(ranks__in=[rank_limit.rank_id]).all()
		for track in tracks:
			campaign = Campaign.objects.get(id=track.campaign_id)
			managers = campaign.managers.all()
			if request.user in managers:
				return True
		return False


class RankRecordAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["create"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["retrieve", "partial_update"],
			"principal": ["authenticated"],
			"effect": "allow",
			"condition": "is_manager"

		},
		{
			"action": ["destroy"],
			"principal": ["authenticated"],
			"effect": "deny"
		}
	]

	def is_manager_exist(self, request, view, action) -> bool:
		return bool(Campaign.objects.filter(managers=request.user))

	def is_manager(self, request, view, action) -> bool:

		rank_limit = view.get_object()

		tracks = Track.objects.filter(ranks__in=[rank_limit.rank_id]).all()
		for track in tracks:
			campaign = Campaign.objects.get(id=track.campaign_id)
			managers = campaign.managers.all()
			if request.user in managers:
				return True
		return False


class TrackAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["create"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager_exist"
		},
		{
			"action": ["retrieve", "partial_update"],
			"principal": ["authenticated"],
			"effect": "allow",
			"condition": "is_manager"

		},
		{
			"action": ["destroy"],
			"principal": ["*"],
			"effect": "deny"
		}
	]

	def is_manager_exist(self, request, view, action) -> bool:
		return bool(Campaign.objects.filter(managers=request.user))

	def is_manager(self, request, view, action) -> bool:
		track = view.get_object()

		campaign = Campaign.objects.get(id=track.campaign_id)
		managers = campaign.managers.all()

		return request.user in managers