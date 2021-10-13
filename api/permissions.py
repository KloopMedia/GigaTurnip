from abc import ABCMeta, abstractmethod

from rest_access_policy import AccessPolicy
from api.models import Campaign, TaskStage, Track
from . import utils


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


class CampaignManagementAccessPolicy(ManagersOnlyAccessPolicy):
    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(user=
                               request.user)


class TaskStageAccessPolicy(ManagersOnlyAccessPolicy):
    statements = [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_manager or is_stage_user_creatable",
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
        },
        {
            "action": ["user_relevant"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": ["create_task"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_stage_user_creatable"
        },
    ]


    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(chain__campaign__campaign_managements__user=
                               request.user)

    def is_stage_user_creatable(self, request, view, action) -> bool:
        queryset = TaskStage.objects.filter(id=view.get_object().id)
        print(bool(utils.filter_for_user_creatable_stages(queryset, request)))
        return bool(utils.filter_for_user_creatable_stages(queryset, request))


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
            "effect": "allow"
        },
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_assignee or is_manager"
        },
        {
            "action": ["create"],
            "principal": "*",
            "effect": "deny",
        },
        {
            "action": ["user_selectable", "user_relevant"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": ["release_assignment"],
            "principal": "authenticated",
            "effect": "deny",
            "condition_expression": "is_assignee and is_not_complete"
        },
        {
            "action": ["request_assignment"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "can_user_request_assignment"
        },
        {
            "action": ["update", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_assignee and is_not_complete"
        }
    ]

    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset. \
            filter(stage__chain__campaign__campaign_managements__user=
                   request.user).distinct()

    def is_assignee(self, request, view, action):
        task = view.get_object()
        return request.user == task.assignee

    def is_not_complete(self, request, view, action):
        task = view.get_object()
        return task.complete is False

    def can_user_request_assignment(self, request, view, action):
        return bool(utils.filter_for_user_selectable_tasks(view.queryset,
                                                           request))

    def is_manager(self, request, view, action) -> bool:
        managers = view.get_object().get_campaign().managers.all()
        return request.user in managers


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


class RankLimitAccessPolicy(ManagersOnlyAccessPolicy):

    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(stage__chain__campaign__campaign_managements__user=
                               request.user)


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


class TrackAccessPolicy(ManagersOnlyAccessPolicy):

    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(campaign__campaign_managements__user=
                               request.user)
