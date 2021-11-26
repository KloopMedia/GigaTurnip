from abc import ABCMeta, abstractmethod

from rest_access_policy import AccessPolicy
from api.models import Campaign, TaskStage, Track, Task
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
        return queryset.filter(
            campaign__campaign_managements__user=request.user
        )


class ConditionalStageAccessPolicy(ManagersOnlyAccessPolicy):
    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(
            chain__campaign__campaign_managements__user=request.user
        )


class CampaignManagementAccessPolicy(ManagersOnlyAccessPolicy):
    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(user=
                               request.user)


class TaskStageAccessPolicy(ManagersOnlyAccessPolicy):
    statements = [
        {
            "action": ["list"],
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
            "action": ["retrieve", "get_integrated_tasks"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_assignee or "
                                    "is_manager or "
                                    "can_user_request_assignment"
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
            #"condition_expression": "is_assignee and is_not_complete"
        },
        {
            "action": ["request_assignment"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "can_user_request_assignment"
        },
        {
            "action": ["update", "partial_update", "open_previous"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_assignee and is_not_complete"
        },
        {
            "action": ["uncomplete"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_assignee and is_complete"
        },
        {
            "action": ["list_displayed_previous"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_assignee or is_manager"
        },
        {
            "action": ["trigger_webhook", ],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_assignee and is_not_complete and is_webhook"
        },
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

    def is_complete(self, request, view, action):
        task = view.get_object()
        return task.complete

    def can_user_request_assignment(self, request, view, action):
        queryset = Task.objects.filter(id=view.get_object().id)
        return bool(utils.filter_for_user_selectable_tasks(
            queryset,
            request))

    def is_manager(self, request, view, action) -> bool:
        managers = view.get_object().get_campaign().managers.all()
        return request.user in managers

    def is_webhook(self, request, view, action):
        return bool(view.get_object().stage.get_webhook())


class RankAccessPolicy(ManagersOnlyAccessPolicy):
    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(
            track__campaign__campaign_managements__user=request.user
        )


class RankLimitAccessPolicy(ManagersOnlyAccessPolicy):

    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(
            stage__chain__campaign__campaign_managements__user=request.user
        )


class RankRecordAccessPolicy(ManagersOnlyAccessPolicy):
    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(
            rank__track__campaign__campaign_managements__user=request.user
        )


class TrackAccessPolicy(ManagersOnlyAccessPolicy):

    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(
            campaign__campaign_managements__user=request.user
        )


class NotificationAccessPolicy(ManagersOnlyAccessPolicy):
    statements = ManagersOnlyAccessPolicy.statements + [
        {
            "action": ["list_user_notifications",
                       "open_notification"],
            "principal": "authenticated",
            "effect": "allow",
        }
    ]

    @classmethod
    def scope_queryset(cls, request, queryset):

        notifications_ranks = queryset.filter(rank__rankrecord__user=request.user)

        notifications_target_user = queryset.filter(target_user=request.user)

        notifications = notifications_ranks | notifications_target_user

        return notifications


class NotificationStatusesAccessPolicy(ManagersOnlyAccessPolicy):
    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(notification__rank__rankrecord__user=
                               request.user)