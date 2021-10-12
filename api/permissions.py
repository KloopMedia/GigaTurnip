from abc import ABCMeta, abstractmethod

from django.http import Http404, HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from rest_access_policy import AccessPolicy
from api.models import Campaign, TaskStage, Track, Chain, Rank, RankRecord
from . import utils


# def managed_campaigns_id(request):
# 	users_campaigns = utils.filter_managed_campaigns(request)
# 	return [str(x['id']) for x in users_campaigns.values("id")]


class CampaignAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["list",
                       "list_user_campaigns",
                       "list_user_selectable",
                       "join_campaign"],
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
            "principal": ["*"],
            "effect": "deny"
        },
        {
            "action": ["partial_update", "update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_manager"
        },
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        }
    ]

    def is_manager(self, request, view, action) -> bool:
        campaign = view.get_object()
        managers = campaign.managers.all()

        return request.user in managers


class ManagersOnlyAccessPolicy(AccessPolicy):
    __metaclass__ = ABCMeta

    statements = [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": ["create"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "can_create"

        },
        {
            "action": ["partial_update", "update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_manager"

        },
        {
            "action": ["destroy"],
            "principal": "*",
            "effect": "deny"
        }
    ]

    @classmethod
    @abstractmethod
    def scope_queryset(cls, request, queryset):
        pass

    @classmethod
    def is_user_campaign_manager(cls, user, value):
        return utils.is_user_campaign_manager(user, value.id)

    def is_manager(self, request, view, action) -> bool:
        managers = view.get_object().get_campaign().managers.all()
        return request.user in managers

    def can_create(self, request, view, action) -> bool:
        return bool(request.user.managed_campaigns.all())


class ChainAccessPolicy(ManagersOnlyAccessPolicy):
    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(campaign__campaign_managements__user=
                               request.user)


class ConditionalStageAccessPolicy(ManagersOnlyAccessPolicy):
    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(chain__campaign__campaign_managements__user=
                               request.user)


class TaskStageAccessPolicy(ManagersOnlyAccessPolicy):
    user_relevant_permissions = [
        {
            "action": ["user_relevant"],
            "principal": "authenticated",
            "effect": "allow",
        }
    ]
    statements = ManagersOnlyAccessPolicy().statements + user_relevant_permissions

    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(chain__campaign__campaign_managements__user=
                               request.user)


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
            "condition_expression": "is_manager or is_have_assignee_task"
        },
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": 'is_assignee or is_manager_retrieve'
        },
        {
            "action": ["create"],  # todo: nobody
            "principal": "authenticated",
            "effect": "deny",
            # "condition": "is_can_create"
        },
        {
            "action": ["user_selectable", "user_relevant"],
            "principal": "authenticated",  # todo: auth
            "effect": "allow",
            # "condition": "is_user_can_request_assignment"
        },
        {
            "action": ["release_assignment"],
            "principal": "authenticated",  # todo:
            "effect": "deny",
        },
        {
            "action": ["request_assignment"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_user_can_request_assignment"  # todo: right
        },
        {
            "action": ["update", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_assignee and is_not_complete"  # todo: right
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

    def is_manager(self, request, view, action) -> bool:
        if request.query_params:
            campaign = request.query_params['stage__chain__campaign']
            # stage = request.query_params['stage']
            # case = request.query_params['case']
            users_campaigns = managed_campaigns_id(request)
            return campaign in users_campaigns
        else:
            return False

    def is_have_assignee_task(self, request, view, action):
        if request.query_params:
            assignee = request.query_params['assignee']
            return request.user.id == assignee
        else:
            return False

    def is_manager_retrieve(self, request, view, action):
        managed_campaigns = utils.user_managed_campaigns(request)
        task = view.get_object()
        task_campaign = task.stage.chain.campaign
        return task_campaign in managed_campaigns


# class TaskStageAccessPolicy(AccessPolicy):
#     statements = [
#         {
#             "action": ["list"],
#             "principal": "authenticated",
#             "effect": "allow",
#             "condition_expression": "is_manager_campaigns and is_chain_of_campaign"  # todo: is manager
#         },
#         {
#             "action": ["create"],
#             "principal": "authenticated",
#             "effect": "allow",
#             "condition": "is_can_create"
#         },
#         {
#             "action": ["retrieve", "partial_update"],
#             "principal": "authenticated",
#             "effect": "allow",
#             "condition_expression": "is_manager or is_user_relevant"
#         },
#         {
#             "action": ["user_relevant"],
#             "principal": "authenticated",
#             "effect": "allow",
#             # "condition": "is_user_relevant"
#         },
#         {
#             "action": ["destroy"],
#             "principal": "authenticated",
#             "effect": "deny",
#         }
#     ]
#
#     # ?chain = 1 & chain__campaign = & is_creatable = & ranklimits__is_creation_open = & ranklimits__total_limit = & ranklimits__total_limit__lt = & ranklimits__total_limit__gt = & ranklimits__open_limit = & ranklimits__open_limit__lt = & ranklimits__open_limit__gt =
#     def is_manager(self, request, view, action) -> bool:
#         managers = view.get_object().chain.campaign.managers.all()
#
#         return request.user in managers
#
#     def is_can_create(self, request, view, action) -> bool:
#         if request.data.get("chain"):
#             chain = request.data.get("chain")
#             campaign = str(Chain.objects.get(id=chain).campaign_id)
#             users_campaigns = managed_campaigns_id(request)
#             return campaign in users_campaigns
#         else:
#             return False
#
#     def is_manager_campaigns(self, request, view, action) -> bool:
#         if request.query_params:
#             campaign = request.query_params['chain__campaign']
#             users_campaigns = managed_campaigns_id(request)
#             return campaign in users_campaigns
#         else:
#             return False
#
#     def is_chain_of_campaign(self, request, view, action):
#         if request.query_params:
#             chain__campaign = str(Chain.objects.get(id=request.query_params['chain']).campaign_id)
#             users_campaigns = managed_campaigns_id(request)
#             return chain__campaign in users_campaigns
#         else:
#             return False
#
#     def is_user_relevant(self, request, view, action) -> bool:
#         queryset = TaskStage.objects.all()
#         filtered_stages = utils.filter_for_user_creatable_stages(queryset, request)
#
#         return bool(filtered_stages)


class RankAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["list"],
            "principal": "authenticated",
            "effect": "allow",
            # "condition": "is_manager_exist"
        },
        {
            "action": ["create"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_manager_of_any_campaign"
        },
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            # "condition": "is_manager"

        },
        {
            "action": ["partial_update"],
            "principal": "authenticated",
            "effect": "deny",
            # "condition": "is_manager"

        },
        {
            "action": ["destroy"],
            "principal": "authenticated",
            "effect": "deny"
        }
    ]

    def is_manager_of_any_campaign(self, request, view, action) -> bool:
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
            "condition": "is_has_rank"
        },
        {
            "action": ["create", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            # "condition": "is_manager_exist"
        },
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_rank_assigned"

        },
        {
            "action": ["destroy"],
            "principal": "authenticated",
            "effect": "deny"
        }
    ]

    def is_has_rank(self, request, view, action) -> bool:
        rank = request.query_params.get('rank')
        if bool(rank):
            rank__rank_record__user_id = RankRecord.objects.get(id=request.query_params.get('rank')).user_id
            return rank__rank_record__user_id == request.user.id
        else:
            return False

    def is_rank_assigned(self, request, view, action):
        user_ranks = request.user.ranks.all()
        return view.get_object().rank in user_ranks

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
        managed_campaigns = utils.user_managed_campaigns(request)
        task = view.get_object()
        task_campaign = task.stage.chain.campaign
        return task_campaign in managed_campaigns


class RankRecordAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["list", "retrieve", "partial_update", "create"],
            "principal": "authenticated",
            "effect": "allow",
            # "condition": "is_manager_exist"
        },
        {
            "action": ["destroy"],
            "principal": "authenticated",
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
            # "condition": "is_manager_exist"
        },
        {
            "action": ["create"],
            "principal": "authenticated",
            "effect": "allow",
            # "condition": "is_manager_exist"
        },
        {
            "action": ["retrieve", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            # "condition": "is_manager"

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
