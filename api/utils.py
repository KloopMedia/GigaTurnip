import json
from functools import wraps
from json import JSONDecodeError

from django.db.models import QuerySet, Count, Q
from rest_framework.response import Response

from api.constans import TaskStageConstants
from api.models import TaskStage, Task, RankLimit, Campaign, Chain, Notification, RankRecord, AdminPreference, \
    CustomUser
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
        .exclude(stage__assign_user_by=TaskStageConstants.INTEGRATOR) \
        .distinct()
    return tasks


def filter_for_datetime(tasks):
    filtered_tasks = tasks.filter(stage__datetime_sort__isnull=False) \
        .filter(
        (Q(stage__datetime_sort__start_time__lte=datetime.now()) | Q(stage__datetime_sort__start_time__isnull=True))
    ) \
        .filter(
        (Q(stage__datetime_sort__end_time__gte=datetime.now()) | Q(stage__datetime_sort__end_time__isnull=True))
    )
    return filtered_tasks


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
        filter_conditions = {
            "==": "",
            "<=": "__lte",
            "<": "__lt",
            ">=": "__gte",
            ">": "__gt",
            "!=": "__ne",
        }
        if field.get('conditions'):
            for i in field.get('conditions'):
                # value = convert_value_by_type(field_type, i.get('value'))
                value = i.get('value')
                condition = i.get('operator')
                key_for_filter = "responses__" + key
                if filter_conditions.get(condition):
                    key_for_filter += filter_conditions.get(condition)

                filters[key_for_filter] = value

    for attr, val in filterest_fields.items():
        if attr != responses_conditions:
            filters[attr] = val
    return filters


def task_stage_queries():
    return {
            "complete_true": Count('pk', Q(complete=True)),
            "complete_false": Count('pk', Q(complete=False)),
            "force_complete_false": Count('pk', Q(force_complete=False)),
            "force_complete_true": Count('pk', Q(force_complete=True)),
            "count_tasks": Count('pk')
        }


def all_uncompleted_tasks(tasks):
    return tasks.filter(
        complete=False,
        force_complete=False
    )


def find_user(id=None, email=None):
    if email:
        filter_to_find = {"email": email}
    if id:
        filter_to_find = {"id": id}
    elif not id and not email:
        return None

    try:
        user = CustomUser.objects.get(**filter_to_find)
    except CustomUser.DoesNotExist:
        user = None

    return user


def value_from_json(path, js):
    if len(path) >= 2:
        return value_from_json(path[1:], js.get(path[1:], js.get(path[0])))
    else:
        return js.get(path[0])


def reopen_task(task):
    task.complete = False
    task.reopened = True
    task.save()


def create_auto_notifications_by_stage_and_case(stage, case):
    auto_notifications = stage.auto_notification_trigger_stages.all()
    if auto_notifications:
        for auto_notification in auto_notifications:
            recipient_stage = auto_notification.recipient_stage
            recipient_task = case.tasks.get(stage=recipient_stage)

            targeted_notification = auto_notification.notification
            targeted_notification.pk = None
            targeted_notification.target_user = recipient_task.assignee
            targeted_notification.save()


def get_ranks_where_user_have_parent_ranks(user, rank):
    new_available_ranks = []
    list_user_ranks = list(user.ranks.values_list('id', flat=True))
    for r in user.ranks.all():
        prerequisite_ranks = r.postrequisite_ranks.exclude(id__in=new_available_ranks+list_user_ranks)
        for post_requisite_rank in prerequisite_ranks:
            user_ranks = set(new_available_ranks+list_user_ranks)
            if all([r in user_ranks for r in post_requisite_rank.prerequisite_ranks.values_list('id', flat=True)]):
                new_available_ranks.append(post_requisite_rank.id)
    return new_available_ranks


def connect_user_with_ranks(user, ranks_ids):
    for i in ranks_ids:
        RankRecord.objects.create(rank_id=i, user=user)


def give_task_awards(stage, task):
    task_awards = stage.task_stage_verified.all()
    for task_award in task_awards:
        rank_record = task_award.connect_user_with_rank(task)
        if rank_record:
            ranks = get_ranks_where_user_have_parent_ranks(rank_record.user, rank_record.rank)
            connect_user_with_ranks(rank_record.user, ranks)


def process_auto_completed_task(stage, task):
    if stage.assign_user_by == TaskStageConstants.AUTO_COMPLETE:
        task.complete = True
        task.save()


def get_conditional_limit_count(stage, filters):
    return stage.out_stages.get().tasks.count()