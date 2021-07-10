from rest_access_policy import AccessPolicy
from api.models import Campaign, Track


class CampaignAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow",

		},
		{
			"action": ["create"],
			"principal": ["group:campaign_creator"],
			"effect": "allow"
		},
		{
			"action": ["destroy"],
			"principal": ["group:campaign_creator"],
			"effect": "allow"
		},
		{
			"action": ["partial_update"],
			"principal": ["*"],
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
			"effect": "allow"
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
			"condition": "is_manager_create"

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
		# при вызове action list вызывается эта функция и request.POST.get('campaign') = none, из-за этого всё крашится
		if not request.POST.get('campaign'):
			return False

		campaign_id = int(request.POST.get('campaign'))
		campaign = Campaign.objects.get(id=campaign_id)
		managers = campaign.managers.all()

		return request.user in managers


class TaskAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["update"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_assignee" and "not_complete"
		},
		{
			"action": ["partial_update"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_assignee" and "not_complete"
		}
	]

	def is_assignee(self, request, view, action):
		task = view.get_object()
		return request.user == task.assignee

	def not_complete(self, request, view, action):
		task = view.get_object()
		return task.complete is False


class TaskStageAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["create"],
			"principal": "authenticated",
			"effect": "allow",
			"condition": "is_manager"
		}
	]

	def is_manager(self, request, view, action) -> bool:
		task_stage = view.get_object()
		managers = task_stage.managers.all()

		return request.user in managers


class RankAccessPolicy(AccessPolicy):
	statements = [
		{
			"action": ["list"],
			"principal": "authenticated",
			"effect": "allow"
		},
		{
			"action": ["create"],
			"principal": "group:rank_creator",
			"effect": "allow"
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

	def is_manager(self, request, view, action) -> bool:

		rank = view.get_object()

		tracks = Track.objects.filter(ranks__in=[rank.id]).all()
		for track in tracks:
			campaign = Campaign.objects.get(id=track.campaign_id)
			managers = campaign.managers.all()
			if request.user in managers:
				return True
		return False
