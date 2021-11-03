from functools import wraps

from django.db.models import QuerySet
from rest_framework.response import Response

from api.models import TaskStage, Task, RankLimit, Campaign, Chain, Notification


def is_user_campaign_manager(user, campaign_id):
    campaigns = Campaign.objects \
        .filter(id=campaign_id) \
        .filter(campaign_managements__user=user)
    return bool(campaigns)


def filter_for_user_creatable_stages(queryset, request):
    stages = queryset \
        .filter(is_creatable=True) \
        .filter(ranks__users=request.user.id) \
        .filter(ranklimits__is_creation_open=True) \
        .distinct()
    filtered_stages = TaskStage.objects.none()
    for stage in stages:
        tasks = Task.objects.filter(assignee=request.user.id) \
            .filter(stage=stage).distinct()
        total = len(tasks)
        incomplete = len(tasks.filter(complete=False))
        ranklimits = RankLimit.objects.filter(stage=stage) \
            .filter(rank__rankrecord__user__id=request.user.id)
        for ranklimit in ranklimits:
            if ((ranklimit.open_limit > incomplete and ranklimit.total_limit > total) or
                    (ranklimit.open_limit == 0 and ranklimit.total_limit > total) or
                    (ranklimit.open_limit > incomplete and ranklimit.total_limit == 0) or
                    (ranklimit.open_limit == 0 and ranklimit.total_limit == 0)
            ):
                filtered_stages |= TaskStage.objects.filter(pk=stage.pk)

    return filtered_stages.distinct()


def filter_for_user_selectable_tasks(queryset, request):
    tasks = queryset \
        .filter(complete=False) \
        .filter(assignee__isnull=True) \
        .filter(stage__ranks__users=request.user.id) \
        .filter(stage__ranklimits__is_selection_open=True) \
        .filter(stage__ranklimits__is_listing_allowed=True) \
        .distinct()
    return tasks


def filter_for_user_campaigns(queryset, request):
    stages = TaskStage.objects.filter(ranks__users=request.user).distinct()
    chains = Chain.objects.filter(stages__in=stages).distinct()
    return queryset.filter(chains__in=chains).distinct()


def filter_for_user_selectable_campaigns(queryset, request):
    return queryset \
        .exclude(id__in=filter_for_user_campaigns(queryset, request)) \
        .exclude(open=False)


def paginate(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        queryset = func(self, *args, **kwargs)
        assert isinstance(queryset, (list, QuerySet)), "apply_pagination expects a List or a QuerySet"

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    return inner


def filter_for_user_notifications(queryset, request):
    '''
    пока простой оооон берееееет и отдает все сообщения у которых ранг совпадает с рангом пользователя
    '''

    notifications = queryset.filter(rank__rankrecord__user__id=request.user.id)

    #campaign
    campaign = request.query_params.get('campaign')
    if campaign:
        notifications = notifications.filter(campaign=campaign)

    # viewed
    viewed = request.query_params.get('viewed')
    if viewed is not None:
        if viewed == 'true':
            notifications = notifications.filter(notification_statuses__viewed=True)
        else:
            notifications = notifications.filter(notification_statuses__viewed=False)

    # assigned
    assigned = request.query_params.get('assigned')
    if assigned is not None:
        if assigned == 'true':
            notifications = notifications.filter(notification_statuses__user=request.user)
        else:
            notifications = notifications.exclude(notification_statuses__user=request.user)

    #importance
    importance = request.query_params.get('importance')
    if importance:
        notifications = notifications.filter(importance=importance)

    return notifications.order_by('-created_at')