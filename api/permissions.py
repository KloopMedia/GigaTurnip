from abc import ABCMeta, abstractmethod

from django.db import transaction, OperationalError
from django.db.models import Q
from rest_access_policy import AccessPolicy
from api.models import (
    TaskStage, Task, RankLimit, CampaignManagement,
    CustomUser, Campaign,
)
from api.utils import utils

def available_campaigns(user, queryset):
    return queryset.filter(
            Q(id__in=user.ranks.values("track__campaign"))
            | Q(open=True)
            | Q(id__in=user.managed_campaigns.all())
        )

class CampaignAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["list"],
            "principal": ["*"],
            "effect": "allow",
        },
        {
            "action": ["retrieve"],
            "principal": ["*"],
            "effect": "allow",
            "condition": "is_accessible",
        },
        {
            "action": ["list_user_campaigns",
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
        }
    ]

    @classmethod
    def scope_queryset(cls, request, qs):
        if request.user.is_anonymous:
            return qs.filter(open=True)


        return available_campaigns(request.user, qs).distinct()

    def is_manager(self, request, view, action) -> bool:
        campaign = view.get_object()
        managers = campaign.managers.all()

        return request.user in managers

    def is_accessible(self, request, view, action) -> bool:
        qs = Campaign.objects.filter(id=view.get_object().id)

        if qs.first().open:
            return True

        return bool(available_campaigns(request.user, qs).distinct())

class UserAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ['delete_init', 'delete_user'],
            "principal": "authenticated",
            "effect": "allow",
        }
    ]

    @classmethod
    def scope_queryset(cls, request, qs):
        return qs.filter(pk=request.user.id)


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
            "action": ["get_graph", "individuals"],
            "principal": "authenticated",
            "effect": "allow"

        }]

    @classmethod
    def scope_queryset(cls, request, queryset):
         # Get the action from the request
        action = request.parser_context['view'].action
        if action == "individuals":
             # Filter chains that have stages with rank limits matching user's ranks
            # user_ranks = request.user.ranks.all()
            # queryset = queryset.filter(
            #     stages__in=TaskStage.objects.filter(
            #         ranklimits__rank__in=user_ranks
            #     )
            # ).distinct()
            return queryset
        
        rank_limits = RankLimit.objects.filter(rank__in=request.user.ranks.all())
        all_available_chains = rank_limits.values_list('stage__chain', flat=True).distinct()
        return queryset.filter(
           Q(campaign__campaign_managements__user=request.user) |
           Q(id__in=all_available_chains)
        ).distinct()
    
    # @classmethod
    # def scope_queryset(cls, request, queryset):
    #      # Get the action from the request
    #     action = request.parser_context['view'].action
        
    #     rank_limits = RankLimit.objects.filter(rank__in=request.user.ranks.all())
    #     all_available_chains = rank_limits.values_list('stage__chain', flat=True).distinct()
        
    #     if action == "individuals":
    #         return queryset.filter(id__in=all_available_chains).distinct()
        
    #     return queryset.filter(
    #        Q(campaign__campaign_managements__user=request.user) |
    #        Q(id__in=all_available_chains)
    #     ).distinct()

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
            "action": ["list", "selectable", "available_stages"],
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
            "condition_expression": "is_stage_user_creatable or is_stage_fast_track"
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
            rank__in=request.user.ranks.values("id")
        ).values_list('stage', flat=True).distinct()

        stages = queryset.filter(Q(chain__campaign__campaign_managements__user=request.user) |
                                 Q(id__in=stages_by_ranks))

        stages |= queryset.filter(id__in=stages.values_list('displayed_prev_stages', flat=True).distinct())
        return queryset.distinct()

    def is_stage_user_creatable(self, request, view, action) -> bool:
        stage = view.get_object()
        with transaction.atomic():
            try:
                task = Task.objects.select_for_update(nowait=True).filter(stage_id=stage, id=request.user.id).first()
            except OperationalError:
                raise Exception("already creating")
        queryset = TaskStage.objects.filter(id=stage.id)
        return bool(utils.filter_for_user_creatable_stages(queryset, request))

    def is_available_stage(self, request, view, action) -> bool:

        all_available_tasks = utils.all_uncompleted_tasks(
            request.user.tasks.select_related('stage')
        )
        tasks_for_current_stage = all_available_tasks.filter(
            stage__id=view.get_object().id
        )

        return tasks_for_current_stage.count() > 0

    def is_displayed_prev(self, request, view, action) -> bool:
        return view.get_object() in view.get_queryset()

    def is_manager(self, request, view, action) -> bool:
        managers = view.get_object().get_campaign().managers.all()
        return request.user in managers

    def is_stage_fast_track(self, request, view, action) -> bool:
        stage = view.get_object()

        return stage.fast_track_rank is not None


class TaskAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["destroy"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_manager"
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
            "principal": "*",
            "effect": "allow",
            "condition_expression": "is_assignee or is_stage_public "
                                    "or is_manager or can_user_request_assignment"
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
            "condition_expression": "is_superuser or (is_assignee and ( is_not_complete or is_task_from_individual_chain ) )"
        },
        {
            "action": ["uncomplete"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_assignee and is_complete"
        },
        {
            "action": ["list_displayed_previous"],
            "principal": "*",
            "effect": "allow",
            "condition_expression": "is_stage_public "
                                    "or (is_assignee or is_manager "
                                    "or (is_selection_open and is_listing_allowed))"
        },
        {
            "action": ["trigger_webhook", ],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_assignee and is_not_complete and is_webhook"
        }
    ]

    @classmethod
    def scope_queryset(cls, request, queryset):
        user = request.user
        user_campaigns = CampaignManagement.objects.filter(
            user=user).values('campaign')
        tasks = request.user.tasks.all()
        tasks |= queryset.filter(stage__chain__campaign__in=user_campaigns)
        tasks |= queryset.filter(
            Q(id__in=user.ranks.values("ranklimits__stage__tasks"))
            & (Q(assignee=user) | Q(assignee__isnull=True) )
        )

        return tasks.distinct()

    def is_assignee(self, request, view, action):
        task = view.get_object()
        return request.user == task.assignee

    def is_superuser(self, request, view, action):
        return request.user.is_superuser

    def is_stage_public(self, request, view, action):
        return view.get_object().stage.is_public

    def is_not_complete(self, request, view, action):
        task = view.get_object()
        return task.complete is False

    def is_task_from_individual_chain(self, request, view, action):
        task = view.get_object()
        return task.stage.chain.is_individual

    def is_complete(self, request, view, action):
        task = view.get_object()
        return task.complete

    def can_user_request_assignment(self, request, view, action):
        queryset = Task.objects.filter(id=view.get_object().id)
        return bool(utils.filter_for_user_selectable_tasks(
            queryset,
            request.user))

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
    statements = [
        {
            "action": ["list", "retrieve", "grouped_by_track"],
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
    def scope_queryset(cls, request, queryset):
        qs = queryset.filter(
            track__campaign__campaign_managements__user=request.user
        )
        qs |= request.user.ranks.all()
        return qs.distinct()


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
            "action": ["list",
                       "last_task_notifications",
                       "read_all_notifications"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": ["retrieve",
                       "open_notification"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_manager or "
                                    "is_user_target or "
                                    "is_user_have_rank"
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
        user_campaigns = CampaignManagement.objects.filter(
            user=request.user).values('campaign')
        qs = queryset.filter(
            Q(campaign__in=user_campaigns) |
            Q(rank__id__in=request.user.ranks.values('id')) |
            Q(target_user=request.user)
        ).distinct()

        return qs


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
            target__in=all_available_tasks.values("stage")
        )

    def is_available_stage(self, request, view, action) -> bool:

        all_available_tasks = utils.all_uncompleted_tasks(
            request.user.tasks.select_related('stage')
        )
        tasks_for_current_stage = all_available_tasks.filter(
            stage__id=view.get_object().target.id
        )

        return tasks_for_current_stage.count() > 0


class UserStatisticAccessPolicy(ManagersOnlyAccessPolicy):
    statements = [
        {
            "action": ["total_count", "new_users", "unique_users"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_user_campaign_manager"
        }
    ]

    @classmethod
    def scope_queryset(cls, request, qs):
        # get users that have any rank of admin preference campaign
        result = qs.filter(
            ranks__in=request.user.managed_campaigns.values("tracks__ranks")
        ).distinct()

        return result

    def is_user_campaign_manager(self, request, view, action):
        return request.user.managed_campaigns.exists()


class CategoryAccessPolicy(ManagersOnlyAccessPolicy):
    statements = [
        {
            "action": ["list"],
            "principal": "authenticated",
            "effect": "allow"
        }
    ]

    @classmethod
    def scope_queryset(cls, request, qs):
        return qs


class LanguageAccessPolicy(ManagersOnlyAccessPolicy):
    statements = [
        {
            "action": ["list"],
            "principal": ["*"],
            "effect": "allow"
        }
    ]

    @classmethod
    def scope_queryset(cls, request, qs):
        return qs


class CountryAccessPolicy(ManagersOnlyAccessPolicy):
    statements = [
        {
            "action": ["list"],
            "principal": ["*"],
            "effect": "allow"
        }
    ]

    @classmethod
    def scope_queryset(cls, request, qs):
        return qs


class UserFCMTokenAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ['update_fcm_token'],
            "principal": "authenticated",
            "effect": "allow",
        }
    ]

    @classmethod
    def scope_queryset(cls, request, qs):
        return qs.filter(pk=request.user.id)


class VolumeAccessPolicy(AccessPolicy):

    statements = [
        {
            "action": ["list", "retrieve"],
            "principal": ["authenticated"],
            "effect": "allow"
        },
    ]

    @classmethod
    def scope_queryset(cls, request, queryset):
        # This method is used for list action to filter the queryset
        if request.user.is_authenticated:
            return queryset.filter(track_fk__default_rank__in=request.user.ranks.all())
        return queryset.none()
