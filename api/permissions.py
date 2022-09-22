from abc import ABCMeta, abstractmethod

from django.db.models import Q
from rest_access_policy import AccessPolicy
from api.models import Campaign, TaskStage, Track, Task, AdminPreference, RankLimit
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

    def __init__(self):
        self.statements += [{
            "action": ["get_graph"],
            "principal": "authenticated",
            "effect": "allow"

        }]

    @classmethod
    def scope_queryset(cls, request, queryset):
        rank_limits = RankLimit.objects.filter(rank__in=request.user.ranks.all())
        all_available_chains = rank_limits.values_list('stage__chain', flat=True).distinct()
        return queryset.filter(
           Q(campaign__campaign_managements__user=request.user) |
           Q(id__in=all_available_chains)
        ).distinct()


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
            "action": ["retrieve", "schema_fields"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_manager or is_stage_user_creatable or is_displayed_prev",
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
        {
            "action": ["public"],
            "principal": "*",
            "effect": "allow",
        },
        {
            "action": ["load_schema_answers"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_available_stage"
        }
    ]

    @classmethod
    def scope_queryset(cls, request, queryset):
        stages_by_ranks = RankLimit.objects.filter(
            rank_id__in=request.user.ranks.values_list('id', flat=True)
        ).values_list('stage', flat=True).distinct()
        stages_by_tasks = request.user.tasks.values_list('stage', flat=True).distinct()

        stages = queryset.filter(Q(chain__campaign__campaign_managements__user=request.user) |
                                 Q(id__in=stages_by_tasks) |
                                 Q(id__in=stages_by_ranks))

        stages |= queryset.filter(id__in=stages.values_list('displayed_prev_stages', flat=True).distinct())
        return stages.distinct()

    def is_stage_user_creatable(self, request, view, action) -> bool:
        queryset = TaskStage.objects.filter(id=view.get_object().id)
        return bool(utils.filter_for_user_creatable_stages(queryset, request))

    def is_available_stage(self, request, view, action) -> bool:

        all_available_tasks = utils.all_uncompleted_tasks(
            request.user.tasks
        )
        tasks_for_current_stage = all_available_tasks.filter(
            stage__id=view.get_object().id
        )

        return tasks_for_current_stage.count() > 0

    def is_displayed_prev(self, request, view, action) -> bool:
        return view.get_object() in view.get_queryset()


class TaskAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["destroy"],
            "principal": "*",
            "effect": "deny",
        },
        {
            "action": ["list", "user_activity"],
            "principal": "authenticated",
            "effect": "allow"
        },
        {
            "action": ["user_activity_csv"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_campaign_manager"
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
            "principal": "group:auto_creator",
            "effect": "allow",
        },
        {
            "action": ["user_selectable", "user_relevant"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": ["release_assignment"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_assignee and is_not_complete"
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
            "condition_expression": "is_assignee or is_manager or (is_selection_open and is_listing_allowed)"
        },
        {
            "action": ["trigger_webhook", ],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_assignee and is_not_complete and is_webhook"
        },
        {
            "action": ["public"],
            "principal": "*",
            "effect": "allow",
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

    def is_manager_by_stage(self, request, view, action) -> bool:
        stage = request.query_params.get('stage')
        response_flattener_id = request.query_params.get('response_flattener')
        if stage and stage.isdigit() and response_flattener_id.isdigit():
            return bool(self.scope_queryset(request, Task.objects.filter(stage=stage)))
        else:
            return False

    def is_campaign_manager(self, request, view, action):
        managed_campaigns = request.user.managed_campaigns.all()
        return bool(managed_campaigns)

    def is_selection_open(self, request, view, action) -> bool:
        rank_limits = RankLimit.objects.filter(
            rank__in=request.user.ranks.all(),
            is_selection_open=True,
            stage=view.get_object().stage
        )
        return bool(rank_limits)

    def is_listing_allowed(self, request, view, action) -> bool:
        rank_limits = RankLimit.objects.filter(
            rank__in=request.user.ranks.all(),
            is_listing_allowed=True,
            stage=view.get_object().stage
        )
        return bool(rank_limits)


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
    statements = [
        {
            "action": ["list"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": ["retrieve", "open_notification"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_manager or is_user_target or is_user_have_rank"
        },
        {
            "action": ["create"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "can_create"

        },
        {
            "action": ["partial_update", "update"], # todo: before the web with admin nobody can update notification.
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
            "action": ["list_user_notifications"],
            "principal": "authenticated",
            "effect": "allow",
        }
    ]

    @classmethod
    def scope_queryset(cls, request, queryset):
        notifications_manager = queryset.filter(campaign__campaign_managements__user=request.user).values_list('id', flat=True)
        notifications_ranks = queryset.filter(rank__rankrecord__user=request.user).values_list('id', flat=True)
        notifications_target_user = queryset.filter(target_user=request.user).values_list('id', flat=True)
        available_ids = set(list(notifications_ranks) + list(notifications_target_user) + list(notifications_manager))

        notifications = queryset.filter(id__in=available_ids)

        return notifications


    @classmethod
    def is_user_campaign_manager(cls, user, value):
        return utils.is_user_campaign_manager(user, value.id)

    def is_manager(self, request, view, action) -> bool:
        managers = view.get_object().get_campaign().managers.all()
        return request.user in managers

    def can_create(self, request, view, action) -> bool:
        return bool(request.user.managed_campaigns.all())

    def is_user_have_rank(self, request, view, action):
        return view.get_object().rank in request.user.ranks.all()

    def is_user_target(self, request, view, action):
        return view.get_object().target_user == request.user

class NotificationStatusesAccessPolicy(ManagersOnlyAccessPolicy):
    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.filter(notification__rank__rankrecord__user=
                               request.user)


class ResponseFlattenerAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["list"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_campaign_manager",
        },
        {
            "action": ["retrieve", "partial_update", "update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_manager",
        },
        {
            "action": ["create", "csv"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_campaign_manager"
        },
        {
            "action": ["destroy"],
            "principal": "*",
            "effect": "deny"
        }

    ]

    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset. \
            filter(task_stage__chain__campaign__campaign_managements__user=request.user) \
            .distinct()

    def is_manager(self, request, view, action) -> bool:
        managers = view.get_object().get_campaign().managers.all()
        return request.user in managers

    def is_campaign_manager(self, request, view, action):
        return bool(request.user.managed_campaigns.all())


class TaskAwardAccessPolicy(ManagersOnlyAccessPolicy):
    @classmethod
    def scope_queryset(cls, request, queryset):
        return queryset.\
            filter(rank__track__campaign__campaign_managements__user=request.user)


class DynamicJsonAccessPolicy(ManagersOnlyAccessPolicy):

    # statements = [
    #     {
    #         "action": ["schema"],
    #         "principal": "authenticated",
    #         "effect": "allow",
    #         "condition_expression": "is_available_stage or is_manager"
    #     }
    # ]

    @classmethod
    def scope_queryset(cls, request, queryset):
        all_available_tasks = utils.all_uncompleted_tasks(
            request.user.tasks
        )
        return queryset \
            .filter(
            task_stage__in=all_available_tasks.values("stage")
        )

    def is_available_stage(self, request, view, action) -> bool:

        all_available_tasks = utils.all_uncompleted_tasks(
            request.user.tasks
        )
        tasks_for_current_stage = all_available_tasks.filter(
            stage__id=view.get_object().task_stage.id
        )

        return tasks_for_current_stage.count() > 0