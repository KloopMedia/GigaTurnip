import json
from functools import wraps
from json import JSONDecodeError

from django.db.models import QuerySet
from rest_framework.response import Response

from api.models import TaskStage, Task, RankLimit, Campaign, Chain, Notification, RankRecord, AdminPreference
from django.contrib import messages
from django.utils.translation import ngettext
from datetime import datetime

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
        .exclude(stage__assign_user_by="IN") \
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
    все сообщения у которых ранг совпадает с рангом пользователя и целевой пользователь

    '''

    # notifications_ranks = queryset.filter(rank__rankrecord__user__id=request.user.id)
    #
    # notifications_target_user = queryset.filter(target_user__id=request.user.id)
    #
    # notifications = notifications_ranks | notifications_target_user

    notifications = queryset

    # campaign
    campaign = request.query_params.get('campaign')
    if campaign:
        notifications = notifications.filter(campaign=campaign)

    # viewed
    viewed = request.query_params.get('viewed')
    if viewed is not None:
        if viewed == 'true':
            notifications = notifications.filter(notification_statuses__user=request.user)
        else:
            notifications = notifications.exclude(notification_statuses__user=request.user)

    # importance
    importance = request.query_params.get('importance')
    if importance:
        notifications = notifications.filter(importance=importance)

    return notifications.order_by('-created_at')


def set_rank_to_user_action(rank):  # todo: rename it
    def set_rank_to_user(modeladmin, request, queryset):
        for user in queryset:
            if not RankRecord.objects.filter(rank=rank).filter(user=user).exists():
                RankRecord.objects.create(rank=rank, user=user)
                messages.info(request, "Set {0} rank {1}".format(user.id, rank.name))
            else:
                messages.info(request, "Exist {0} rank {1}".format(user.id, rank.name))

    set_rank_to_user.short_description = "Assign {0}".format(rank.name)
    set_rank_to_user.__name__ = 'set_rank_{0}'.format(rank.id)

    return set_rank_to_user


def filter_by_admin_preference(queryset, request, path):
    admin_preference = AdminPreference.objects.filter(user=request.user)
    if path is None:
        dynamic_filter = {"managers": request.user}
    else:
        dynamic_filter = {path + "campaign__managers": request.user}
    if admin_preference:
        if admin_preference[0].campaign is not None:
            if path is None:
                dynamic_filter = {"id": admin_preference[0].campaign}
            else:
                dynamic_filter[path + "campaign"] = admin_preference[0].campaign
    return queryset.filter(**dynamic_filter)


# Copied from https://stackoverflow.com/questions/6027558/flatten-nested-dictionaries-compressing-keys
def flatten(d, parent_key='', sep='__'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def str_to_responses_dict(params):
    result = {"stage": "", "responses": {}}
    try:
        data = json.loads(params)
    except JSONDecodeError:
        return None
    if not data.get("stage", None) or \
            not isinstance(data.get("responses", None), dict):
        return None
    result["stage"] = data["stage"]
    result["responses"] = flatten(data["responses"], "responses", "__")
    return result


def can_complete(task, user):
    rank_limits = RankLimit.objects \
        .filter(stage=task.stage)\
        .filter(rank__users=user)\
        .filter(is_submission_open=False)
    if rank_limits:
        return False
    return True

def array_difference(source, target):
    return [i for i in source if i not in target]

def convert_value_by_type(type, value):
    if type == 'string':
        value = str(value)
    elif type == 'int':
        value = int(value)
    elif type == 'float':
        value = float(value)
    return value


def conditions_to_dj_filters(filterest_fields):
    filters = {}
    responses_conditions = 'all_conditions'
    for field in filterest_fields.get(responses_conditions):
        key = field.get('field')
        field_type = field.get('type')
        if field.get('conditions'):
            for i in field.get('conditions'):
                value = convert_value_by_type(field_type, i.get('value'))
                condition = i.get('operator')
                key_for_filter = "responses__" + key
                if condition == '==':
                    key_for_filter += ''
                elif condition == '<=':
                    key_for_filter += '__lte'
                elif condition == '<':
                    key_for_filter += '__lt'
                elif condition == '>=':
                    key_for_filter += '__gte'
                elif condition == '>':
                    key_for_filter += '__gt'
                elif condition == '!=':
                    key_for_filter += '__ne'
                filters[key_for_filter] = value
    for attr, val in filterest_fields.items():
        if attr != responses_conditions:
            filters[attr] = val
    return filters
