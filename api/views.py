import csv
import operator
from functools import reduce
from datetime import datetime, timedelta
from itertools import chain

import django_filters
import requests
from django.core.paginator import Paginator
from django.contrib.postgres.aggregates import ArrayAgg, JSONBAgg
from django.db import models
from django.db.models import Count, Q, Subquery, F, When, Func, Value, TextField, OuterRef, Case as ExCase
from django.db.models.functions import Cast, JSONObject
from django.http import HttpResponse, Http404
from django.template import loader
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _

from django.shortcuts import get_object_or_404

from api.models import Campaign, Chain, TaskStage, \
    ConditionalStage, Case, Task, Rank, \
    RankLimit, Track, RankRecord, CampaignManagement, \
    Notification, NotificationStatus, ResponseFlattener, TaskAward, \
    DynamicJson, CustomUser, TestWebhook, Webhook, UserDelete
from api.serializer import CampaignSerializer, ChainSerializer, \
    TaskStageSerializer, ConditionalStageSerializer, \
    CaseSerializer, RankSerializer, RankLimitSerializer, \
    TrackSerializer, RankRecordSerializer, TaskCreateSerializer, \
    TaskEditSerializer, TaskDefaultSerializer, \
    TaskRequestAssignmentSerializer, TestWebhookSerializer, \
    TaskStageReadSerializer, CampaignManagementSerializer, \
    TaskSelectSerializer, \
    NotificationListSerializer, NotificationSerializer, \
    TaskAutoCreateSerializer, TaskPublicSerializer, \
    TaskStagePublicSerializer, ResponseFlattenerCreateSerializer, \
    ResponseFlattenerReadSerializer, TaskAwardSerializer, \
    DynamicJsonReadSerializer, TaskResponsesFilterSerializer, \
    TaskStageFullRankReadSerializer, TaskUserActivitySerializer, \
    NumberRankSerializer, UserDeleteSerializer, TaskListSerializer
from api.asyncstuff import process_completed_task, update_schema_dynamic_answers, process_updating_schema_answers
from api.permissions import CampaignAccessPolicy, ChainAccessPolicy, \
    TaskStageAccessPolicy, TaskAccessPolicy, RankAccessPolicy, \
    RankRecordAccessPolicy, TrackAccessPolicy, RankLimitAccessPolicy, \
    ConditionalStageAccessPolicy, CampaignManagementAccessPolicy, \
    NotificationAccessPolicy, \
    NotificationStatusesAccessPolicy, ResponseFlattenerAccessPolicy, \
    TaskAwardAccessPolicy, \
    DynamicJsonAccessPolicy, UserAccessPolicy
from . import utils
from .api_exceptions import CustomApiException
from .constans import ErrorConstants, TaskStageConstants
from .filters import ResponsesContainsFilter, TaskResponsesContainsFilter
from .utils import paginate
import json

from datetime import datetime


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = (UserAccessPolicy,)

    def get_queryset(self):
        return UserAccessPolicy.scope_queryset(
            self.request, CustomUser.objects.all()
        )

    @action(detail=False, methods=['get'])
    def delete_init(self, request, *args, **kwargs):
        """
        First step to delete user. Create User Delete
        object that will used in the delete_user endpoint.
        """
        del_obj = UserDelete.objects.create(user=request.user)
        [i.delete() for i in UserDelete.objects.filter(user=request.user)[1:]]
        return Response(
            {"delete_pk": del_obj.pk},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def delete_user(self, request, pk=None):
        """
        Param PK is UserDelete pk that returned by delete_init endpoint.
        User will be deleted if UserDelete obj created less than 5 minutes
        later.
        """
        now_minus_5 = datetime.now() - timedelta(minutes=5)
        obj = UserDelete.objects.filter(
            pk=pk, user =request.user,
            created_at__gt=now_minus_5
        )
        serializer = UserDeleteSerializer(data=request.data)
        if serializer.is_valid() and obj.count() > 0:
            if serializer.data['artifact'] in [request.user.email,
                                               request.user.username]:
                if request.user.rename():
                    return Response(
                        {"message": "Profile deleted successfully!"},
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {
                         "message": "Something went wrong"},
                        status=status.HTTP_409_CONFLICT
                    )
            return Response(
                {"message": "Email or phone number is incorrect."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {"message": "You haven't approve previous step yet."},
            status=status.HTTP_404_NOT_FOUND
        )


class CampaignViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing campaigns.
    create:
    Create a new campaign instance.
    delete:
    Delete campaign.
    read:
    Get campaign data.
    update:
    Update campaign data.
    partial_update:
    Partial update campaign data.
    list_user_campaigns:
    List campaigns where user has rank
    join_campaign:
    Request to join campaign on behalf of current user.
    """

    serializer_class = CampaignSerializer
    queryset = Campaign.objects.all()

    permission_classes = (CampaignAccessPolicy,)

    @action(detail=True, methods=['post', 'get'])
    def join_campaign(self, request, pk=None):
        rank_record, created = self.get_object().join(request)
        rank_record_json = RankRecordSerializer(instance=rank_record).data
        if rank_record and created:
            return Response({'status': status.HTTP_201_CREATED,
                             'rank_record': rank_record_json})
        elif rank_record and not created:
            return Response({'status': status.HTTP_200_OK,
                             'rank_record': rank_record_json})
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @paginate
    @action(detail=False)
    def list_user_campaigns(self, request):
        campaigns = utils.filter_for_user_campaigns(self.get_queryset(),
                                                    request)
        return campaigns

    @paginate
    @action(detail=False)
    def list_user_selectable(self, request):
        campaigns = utils \
            .filter_for_user_selectable_campaigns(self.get_queryset(), request)
        return campaigns


class ChainViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing chains.
    create:
    Create a new chain instance.
    delete:
    Delete chain.
    read:
    Get chain data.
    update:
    Update chain data.
    partial_update:
    Partial update chain data.
    """

    filterset_fields = ['campaign', ]
    serializer_class = ChainSerializer
    permission_classes = (ChainAccessPolicy,)

    def get_queryset(self):
        return ChainAccessPolicy.scope_queryset(
            self.request, Chain.objects.all()
        )

    @action(detail=True)
    def get_graph(self, request, pk=None):
        stages = self.get_object().stages.all()
        graph = stages.values('pk', 'name').annotate(
            in_stages=ArrayAgg('in_stages', distinct=True),
            out_stages=ArrayAgg('out_stages', distinct=True)
        )
        return Response(graph)


class TaskStageViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing task stages.
    create:
    Create a new task stage instance.
    delete:
    Delete task stage.
    read:
    Get task stage data.
    update:
    Update task stage data.
    partial_update:
    Partial update task stage data.
    user_relevant:
    Return a list of task stages that are relevant to "request" user.
    """

    permission_classes = (TaskStageAccessPolicy,)
    filterset_fields = {
        'chain': ['exact'],
        'chain__campaign': ['exact'],
        'is_creatable': ['exact'],
        'ranks': ['exact'],
        'ranks__users': ['exact'],
        'ranklimits__is_creation_open': ['exact'],
        'ranklimits__total_limit': ['exact', 'lt', 'gt'],
        'ranklimits__open_limit': ['exact', 'lt', 'gt']
    }

    def get_serializer_class(self):
        """
        get_serializer_class:
        Выбирает нужные сериалайзер (для чтения или обычный).
        """

        if self.action in ['create', 'update', 'partial_update']:
            return TaskStageSerializer
        elif self.action == 'public':
            return TaskStagePublicSerializer
        else:
            if self.request.query_params.get('ranks_avatars'):
                return TaskStageFullRankReadSerializer
            return TaskStageReadSerializer

    def get_queryset(self):
        if self.action == 'list':
            return TaskStageAccessPolicy.scope_queryset(
                self.request, TaskStage.objects.all()
                .select_related(
                    "chain",
                    "assign_user_from_stage",
                ).prefetch_related(
                    "displayed_prev_stages",
                    "displayed_following_stages",
                    "dynamic_jsons_source",
                    "dynamic_jsons_target",
                    "in_stages",
                    "out_stages",
                    "ranks"
                )
            )
        else:
            return TaskStage.objects.all()

    @paginate
    @action(detail=False)
    def user_relevant(self, request):
        stages = self.filter_queryset(self.get_queryset())
        stages = utils.filter_for_user_creatable_stages(stages, request)
        return stages

    @paginate
    @action(detail=False)
    def public(self, request):
        stages = self.filter_queryset(self.get_queryset())
        stages = stages.filter(
            Q(is_public=True) | Q(publisher__is_public=True))
        return stages

    @action(detail=True, methods=['post', 'get'])
    def create_task(self, request, pk=None):
        case = Case.objects.create()
        stage = self.get_object()
        task = Task(stage=stage, assignee=request.user, case=case)
        for copy_field in stage.copy_fields.all():
            task.responses = copy_field.copy_response(task)
        task.save()
        return Response({'status': 'New task created', 'id': task.id})

    @action(detail=True, methods=['get'])
    def schema_fields(self, request, pk=None):
        stage = self.get_object()
        fields = [i.split('__', 1)[1] for i in stage.make_columns_ordered()]
        return Response({'fields': fields})

    @action(detail=True, methods=['get'])
    def load_schema_answers(self, request, pk=None):
        """
        We must pass responses for the schema to get primary key and update sub field's answers
        Otherwise we would return response with 400 status code

        :param GET: responses (responses for the task of stage)
        :param pk: stage id (to update schema)
        :return:
        """

        kwargs = dict()
        task_stage = self.get_object()
        kwargs['task_stage'] = task_stage

        responses = request.query_params.get('responses')
        if responses:
            kwargs['responses'] = json.loads(responses)

        task_id = request.query_params.get('current_task')
        if task_id and task_id.isdigit():
            try:
                task = Task.objects.get(id=task_id)
                kwargs['case'] = task.case.id if task.case else None
            except Task.DoesNotExist:
                raise CustomApiException(status.HTTP_400_BAD_REQUEST,
                                         ErrorConstants.ENTITY_DOESNT_EXIST % ('Task', task_id))

        if task_stage.json_schema:
            schema = process_updating_schema_answers(**kwargs)
            return Response({'status': status.HTTP_200_OK,
                             'schema': schema})
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class ConditionalStageViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing conditional stages.
    create:
    Create a new chain conditional stage.
    delete:
    Delete conditional stage.
    read:
    Get conditional stage data.
    update:
    Update conditional stage data.
    partial_update:
    Partial update conditional stage data.
    """
    filterset_fields = ['chain', ]
    serializer_class = ConditionalStageSerializer
    permission_classes = (ConditionalStageAccessPolicy,)

    def get_queryset(self):
        return ConditionalStageAccessPolicy.scope_queryset(
            self.request, ConditionalStage.objects.all()
        )


class CaseViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing cases.
    create:
    Create a new case instance.
    delete:
    Delete case.
    read:
    Get case data.
    update:
    Update case data.
    partial_update:
    Partial update case data.
    """
    queryset = Case.objects.all()
    serializer_class = CaseSerializer

    filterset_fields = {
        'tasks__stage__chain': ['exact'],
        'created_at': ['lte', 'gte', 'lt', 'gt'],
        'updated_at': ['lte', 'gte', 'lt', 'gt']
    }

    @action(detail=True)
    def info_by_case(self, request, pk=None):
        tasks = self.get_object().tasks.all()
        filters_tasks_info = {
            "complete": ArrayAgg('complete'),
            "force_complete": ArrayAgg('force_complete'),
            "id": ArrayAgg('pk'),
        }
        task_info_by_stage = tasks.values('stage', 'stage__name').annotate(
            **filters_tasks_info
        )
        return Response({
            "status": status.HTTP_200_OK,
            "info": list(task_info_by_stage)
        })


# class ResponsesContainFilter(filters.SearchFilter):
#
#     search_param = "responses_contain"
#     search_title = _('Task Responses Filter')
#
#     def to_html(self, request, queryset, view):
#         return ""
#
#     def get_search_terms(self, request):
#         """
#         Search term is set by a ?search=... query parameter.
#         """
#         params = request.query_params.get(self.search_param, '')
#         if not params:
#             return None
#         params = params.split(': ')
#         if len(params) != 2:
#             return None
#         return params
#
#     def filter_queryset(self, request, queryset, view):
#
#         search_fields = self.get_search_fields(view, request)
#         search_term = self.get_search_terms(request)
#
#         if not search_fields or not search_term:
#             return queryset
#
#         tasks = Task.objects.filter(stage__id=search_term[0])
#         tasks = tasks.filter(responses__icontains=search_term[1])
#         cases = Case.objects.filter(tasks__in=tasks).distinct()
#         response = queryset.filter(case__in=cases)
#         return response


class TaskViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing tasks.

    create:
    Create a new task instance. Note: if task is completed,
    process_completed_task() function will be called.

    delete:
    Delete task.

    read:
    Get task data.

    update:
    Update task data. Note: if task is completed,
    process_completed_task() function will be called.

    partial_update:
    Partial update task data.

    user_relevant:
    Return a list of tasks where user is task assignee.

    user_selectable:
    Return a list of not assigned
    uncompleted tasks that are allowed to the user.

    request_assignment:
    Assign user to requested task.

    release_assignment:
    Release user from requested task.

    user_activity_csv:
    Return list of activities on stages. Allow to download csv file.

    csv:
    Return csv file with tasks information. Note: params stage and response_flattener are important.

    get_integrated_tasks:
    Return integrated tasks of requested task.

    """

    filterset_fields = {
        'case': ['exact'],
        'stage': ['exact'],
        'stage__chain__campaign': ['exact'],
        'stage__chain': ['exact'],
        'stage__chain__name': ['exact'],
        'assignee': ['exact'],
        'assignee__ranks': ['exact'],
        'complete': ['exact'],
        'created_at': ['lte', 'gte', 'lt', 'gt'],
        'updated_at': ['lte', 'gte', 'lt', 'gt']
    }
    search_fields = ('responses', )
    filter_backends = [
        DjangoFilterBackend,
        ResponsesContainsFilter,
        TaskResponsesContainsFilter]
    permission_classes = (TaskAccessPolicy,)

    def get_queryset(self):
        qs = Task.objects.all().select_related('stage')
        if self.action in ['list', 'csv', 'user_activity',
                           'user_activity_csv', 'search_by_responses']:
            return TaskAccessPolicy.scope_queryset(
                self.request, qs
            )
        else:
            return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        elif self.action == 'create':
            return TaskAutoCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TaskEditSerializer
        elif self.action == 'request_assignment':
            return TaskRequestAssignmentSerializer
        elif self.action == 'user_selectable':
            return TaskSelectSerializer
        elif self.action == 'public':
            return TaskListSerializer
        elif self.action == 'user_activity':
            return TaskUserActivitySerializer
        else:
            return TaskDefaultSerializer

    @paginate
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        qs = qs.values('id',
                       'complete',
                       'force_complete',
                       'created_at',
                       'reopened',
                       'stage__name',
                       'stage__description')

        return qs

    def create(self, request, *args, **kwargs):
        """
        post:
        Create a new task instance. Note: if task is completed,
        process_completed_task() function will be called.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            case = Case.objects.create()
            task = serializer.save(case=case)
            if task.complete:
                process_completed_task(task)
            # if data['complete']:
            #     result(async_task(process_completed_task,
            #                       data['id'],
            #                       task_name='process_completed_task',
            #                       group='follow_chain'))
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """
        Post:
        Update task data. Note: if task is completed,
        process_completed_task() function will be called.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance,
                                         data=request.data,
                                         partial=partial)
        if serializer.is_valid():
            data = serializer.validated_data
            data['id'] = instance.id
            next_direct_task = None
            complete = serializer.validated_data.get("complete", False)
            if complete and not utils.can_complete(instance, request.user):
                err_message = {
                    "detail": f"{ErrorConstants.CANNOT_SUBMIT} {ErrorConstants.TASK_COMPLETED}",
                    "id": instance.id
                }
                raise CustomApiException(status.HTTP_403_FORBIDDEN, err_message)
            try:
                task = instance.set_complete(
                    responses=serializer.validated_data.get("responses", {}),
                    complete=complete
                )
                if complete:
                    next_direct_task = process_completed_task(task)
            except Task.CompletionInProgress:
                err_message = {
                    "detail": {
                        "message": f"{ErrorConstants.CANNOT_SUBMIT} {ErrorConstants.TASK_COMPLETED}",
                        "id": instance.id
                    }
                }
                raise CustomApiException(status.HTTP_403_FORBIDDEN, err_message)
            except Task.AlreadyCompleted:
                err_message = {
                    "detail": {
                        "message": ErrorConstants.TASK_ALREADY_COMPLETED,
                        "id": instance.id}
                }
                raise CustomApiException(status.HTTP_403_FORBIDDEN, err_message)
            if getattr(instance, '_prefetched_objects_cache', None):
                # If 'prefetch_related' has been applied to a queryset,
                # we need to forcibly invalidate the prefetch
                # cache on the instance.
                instance._prefetched_objects_cache = {}
            if next_direct_task:
                return Response(
                    {"message": "Next direct task is available.",
                     "id": instance.id,
                     "next_direct_id": next_direct_task.id},
                    status=status.HTTP_200_OK)
            return Response(
                {"message": "Task saved.",
                 "id": instance.id},
                status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        """
        Post:
        Partial update task data.
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @paginate
    @action(detail=False)
    def user_relevant(self, request):
        """
        Get:
        Return a list of tasks where user is task assignee.
        """
        queryset = self.filter_queryset(self.get_queryset())
        tasks = queryset.filter(assignee=request.user) \
            .exclude(stage__assign_user_by=TaskStageConstants.INTEGRATOR)
        return tasks

    @paginate
    @action(detail=False, methods=["GET", "POST"])
    def user_selectable(self, request):
        """
        Get:
        Return a list of not assigned
        uncompleted tasks that are allowed to the user.
        """
        queryset = self.filter_queryset(
            self.get_queryset()
            .select_related('stage')
            .prefetch_related('stage__ranks__users',
                              'out_tasks',
                              'stage__displayed_prev_stages',
                              'stage__ranklimits')
        )

        tasks = queryset
        if request.query_params.get('responses_contains') or request.method == "POST":
            tasks = Task.objects.filter(id__in=Subquery(queryset.filter(out_tasks__isnull=False).values('out_tasks')))
        tasks_selectable = utils.filter_for_user_selectable_tasks(tasks, request)
        by_datetime = utils.filter_for_datetime(tasks_selectable)
        result_tasks = by_datetime.values(
            'id',
            'case',
            'stage__name',
            'stage__description',
            'stage__json_schema',
            'stage__ui_schema',
            'responses',
            'complete',
        ).annotate(
            displayed_prev_stages=ArrayAgg('stage__displayed_prev_stages',
                                           distinct=True)
        )
        return result_tasks

    @paginate
    @action(detail=False)
    def public(self, request):
        tasks = self.filter_queryset(self.get_queryset())
        tasks = tasks.values('id',
                             'complete',
                             'force_complete',
                             'reopened',
                             'stage__publisher__is_public',
                             'stage__name',
                             'stage__description')
        is_public = tasks.filter(stage__is_public=True)
        is_public_publisher = tasks.filter(complete=True).filter(
            stage__publisher__is_public=True
        )
        tasks = list(chain(is_public, is_public_publisher))
        return tasks

    @paginate
    @action(detail=False)
    def user_activity(self, request):
        tasks = self.filter_queryset(self.get_queryset()) \
            .select_related('stage',) \
            .prefetch_related('stage__ranks', 'stage__in_stages',
                              'stage__out_stages')

        groups = tasks.values('stage').annotate(
            chain=F('stage__chain'),
            chain_name=F('stage__chain__name'),
            ranks=ArrayAgg('stage__ranks', distinct=True),
            in_stages=ArrayAgg('stage__in_stages', distinct=True),
            out_stages=ArrayAgg('stage__out_stages', distinct=True),
            stage_name=F('stage__name'),
            **utils.task_stage_queries()
        )

        return groups

    @action(detail=False)
    def user_activity_csv(self, request):
        """
        Get:
        Return list of activities on stages. Note: if you want download csv file you have to set 'csv' in params as true

        Also for custom statistics you can use filters. And on top of all that you can use filters in csv using 'task_responses' key in params.
        Params for example:
        ?csv=true&task_responses={"a":"b"}
        """
        tasks = self.filter_queryset(self.get_queryset()) \
            .select_related('stage', 'assignee')
        groups = tasks.values('stage', 'stage__name', 'assignee').annotate(
            chain_id=F('stage__chain'),
            chain=F('stage__chain__name'),
            email=F("assignee__email"),
            rank_ids=ArrayAgg('assignee__ranks__id', distinct=True),
            rank_names=ArrayAgg('assignee__ranks__name', distinct=True),
            **utils.task_stage_queries()
        ).order_by("count_tasks")

        filename = "results"  # utils.request_to_name(request)
        response = HttpResponse(
            content_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}.csv"'
            },
        )

        if request.query_params.get("csv", None):
            fieldnames = ["stage", "stage__name", "chain_id", "chain",
                          "case", "assignee", "email", "rank_ids", "rank_names",
                          "complete_true", "complete_false", "force_complete_false",
                          "force_complete_true", "count_tasks", ]

            writer = csv.DictWriter(response, fieldnames=fieldnames)
            writer.writeheader()
            for group in groups:
                writer.writerow(group)
            return response

        return Response(groups)

    @paginate
    @action(detail=True)
    def get_integrated_tasks(self, request, pk=None):
        """
        Get:
        Return integrated tasks
        """
        tasks = self.filter_queryset(self.get_queryset())
        tasks = tasks.filter(out_tasks=self.get_object())
        return tasks

    @action(detail=True, methods=['post', 'get'])
    def request_assignment(self, request, pk=None):
        """
        Get:
        Request task assignment to user
        """
        task = self.get_object()
        serializer = self.get_serializer(task, request.data)
        if serializer.is_valid():
            serializer.save()
            if task.integrator_group is not None:
                in_tasks = Task.objects.filter(out_tasks=task) \
                    .filter(stage__assign_user_by="IN")
                if in_tasks:
                    in_tasks.update(assignee=request.user)
            return Response({'status': 'assignment granted', 'id': task.id})
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'get'])
    def release_assignment(self, request, pk=None):
        """
        Get:
        Request task release assignment
        """
        task = self.get_object()
        if task.stage.allow_release and not task.complete:
            task.assignee = None
            task.save()
            if task.integrator_group is not None:
                in_tasks = Task.objects.filter(out_tasks=task) \
                    .filter(stage__assign_user_by="IN")
                if in_tasks:
                    in_tasks.update(assignee=None)
            return Response({'status': 'assignment released'})
        raise CustomApiException(status.HTTP_403_FORBIDDEN, ErrorConstants.IMPOSSIBLE_ACTION % 'release this')

    @action(detail=True, methods=['post', 'get'])
    def uncomplete(self, request, pk=None):
        task = self.get_object()
        try:
            task.set_not_complete()
            return Response({'status': 'Assignment uncompleted', 'id': task.id})
        except Task.ImpossibleToUncomplete:
            raise CustomApiException(status.HTTP_403_FORBIDDEN, ErrorConstants.IMPOSSIBLE_ACTION % 'uncomplete this')

    @action(detail=True, methods=['post', 'get'])
    def open_previous(self, request, pk=None):
        task = self.get_object()
        try:
            (prev_task, task) = task.open_previous()
            return Response({'status': 'Previous task opened.', 'id': prev_task.id})
        except Task.ImpossibleToOpenPrevious:
            return CustomApiException(status.HTTP_403_FORBIDDEN, ErrorConstants.IMPOSSIBLE_ACTION % 'open previous')

    # @action(detail=True, methods=['post', 'get'])
    # def open_next(self, request, pk=None):
    #     task = self.get_object()
    #     try:
    #         next_task = task.open_next()
    #         return Response({'status': 'Next task opened.', 'id': next_task.id})
    #     except Task.ImpossibleToOpenNext:
    #         return Response(
    #             {'message': 'It is impossible to open next task.'},
    #             status=status.HTTP_403_FORBIDDEN
    #         )

    @paginate
    @action(detail=True, methods=['get'])
    def list_displayed_previous(self, request, pk=None):
        tasks = self.get_object().get_displayed_prev_tasks()
        return tasks

    @action(detail=True, methods=['get'])
    def trigger_webhook(self, request, pk=None):
        task = self.get_object()
        webhook = task.stage.get_webhook()
        if webhook:
            is_altered, altered_task, response, error_description = webhook.trigger(task)
            if is_altered:
                return Response({"status": "Responses overwritten",
                                 "responses": altered_task.responses})
            else:
                err_msg = {"detail": {
                    "message": error_description,
                    "status": response.status_code
                }}
                raise CustomApiException(status.HTTP_400_BAD_REQUEST, err_msg)
        # django_response = HttpResponse(
        #     content=response.content,
        #     status=response.status_code,
        #     content_type=response.headers['Content-Type']
        # )
        return

    @action(detail=False, methods=['get'])
    def statistics(self):
        q = self.filter_queryset(self.get_queryset()).select_related(
            'stage'
        )
        q = q.values('stage', 'stage__name', 'complete',
                     'force_complete').annotate().order_by('stage')
        return q


#         tasks = self.get_object().tasks.all()
#         filters_tasks_info = {
#             "complete": ArrayAgg('complete'),
#             "force_complete": ArrayAgg('force_complete'),
#             "id": ArrayAgg('pk'),
#         }
#         task_info_by_stage = tasks.values('stage', 'stage__name').annotate(
#             **filters_tasks_info
#         )
#         return Response({
#             "status": status.HTTP_200_OK,
#             "info": list(task_info_by_stage)
#         })

class RankViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing ranks.
    create:
    Create a new rank instance.
    delete:
    Delete rank.
    read:
    Get rank data.
    update:
    Update rank data.
    partial_update:
    Partial update rank data.
    """

    serializer_class = RankSerializer
    permission_classes = (RankAccessPolicy,)

    def get_queryset(self):
        return RankAccessPolicy.scope_queryset(
            self.request, Rank.objects.all()
        )


class RankRecordViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing rank records.
    create:
    Create a new rank record instance.
    delete:
    Delete rank record.
    read:
    Get rank record data.
    update:
    Update rank record data.
    partial_update:
    Partial update rank record data.
    """
    serializer_class = RankRecordSerializer
    permission_classes = (RankRecordAccessPolicy,)

    def get_queryset(self):
        return RankRecordAccessPolicy.scope_queryset(
            self.request, RankRecord.objects.all()
        )


class RankLimitViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing rank limits.
    create:
    Create a new rank limit instance.
    delete:
    Delete rank limit.
    read:
    Get rank limit data.
    update:
    Update rank limit data.
    partial_update:
    Partial update rank limit data.
    """

    filterset_fields = ['rank', ]
    serializer_class = RankLimitSerializer

    permission_classes = (RankLimitAccessPolicy,)

    def get_queryset(self):
        return RankLimitAccessPolicy.scope_queryset(
            self.request, RankLimit.objects.all()
        )


class NumberRankViewSet(viewsets.ModelViewSet):
    # serializer_class = NumberRanksSerializer

    def get_serializer_class(self):
        return NumberRankSerializer

    def get_queryset(self):
        return RankAccessPolicy.scope_queryset(
            self.request, Rank.objects.all()
        )

    def list(self, request, *args, **kwargs):
        q = self.filter_queryset(self.get_queryset()) \
            .prefetch_related('track') \
            .select_related('users')

        main_keys = {
            'campaign_id': F('track__campaign__id'),
            'campaign_name': F('track__campaign__name')
        }
        q = q.values(**main_keys) \
            .annotate(
            ranks=ArrayAgg(Subquery(
                q.filter(
                    id=OuterRef('id')
                ).annotate(
                    count=Count('users'),
                    rank_id=F('id'),
                    rank_name=F('name'),
                    condition=ExCase(
                        When(Q(prerequisite_ranks__isnull=False),
                             then=Value('prerequisite_ranks')),
                        When(Q(taskaward__isnull=False),
                             then=Value('task_awards')),
                        default=Value('default'),
                        output_field=TextField()
                    )
                ).values(
                    json=JSONObject(id='rank_id',
                                    count='count',
                                    name='rank_name',
                                    condition='condition')
                )
            ))
        )

        return Response(q)


class TrackViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing tracks.
    create:
    Create a new track instance.
    delete:
    Delete track.
    read:
    Get track data.
    update:
    Update track data.
    partial_update:
    Partial update track data.
    """

    serializer_class = TrackSerializer

    permission_classes = (TrackAccessPolicy,)

    def get_queryset(self):
        return TrackAccessPolicy.scope_queryset(
            self.request, Track.objects.all()
        )


class CampaignManagementViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing campaign management.
    create:
    Create a new campaign management instance.
    delete:
    Delete campaign management.
    read:
    Get campaign management data.
    update:
    Update campaign management data.
    partial_update:
    Partial update campaign management data.
    """

    serializer_class = CampaignManagementSerializer

    permission_classes = (CampaignManagementAccessPolicy,)

    def get_queryset(self):
        return CampaignManagementAccessPolicy.scope_queryset(
            self.request, CampaignManagement.objects.all()
        )


class NotificationViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing messages.
    create:
    Create a new campaign notification.
    delete:
    Delete notification.
    read:
    Get notification data.
    update:
    Update notification data.
    partial_update:
    Partial update notification data.
    """

    filterset_fields = {
        'importance': ['exact'],
        'campaign': ['exact'],
        'rank': ['exact'],
        'receiver_task': ['exact'],
        'sender_task': ['exact'],
        'trigger_go': ['exact'],
        'created_at': ['lte', 'gte'],
        'updated_at': ['lte', 'gte']
    }
    permission_classes = (NotificationAccessPolicy,)

    def get_serializer_class(self):
        if self.action in ['create', 'partial_update', 'update', 'retrieve']:
            return NotificationSerializer
        if self.action in ['list']:
            return NotificationListSerializer
        return NotificationListSerializer

    def get_queryset(self):
        return NotificationAccessPolicy.scope_queryset(
            self.request, Notification.objects.all().order_by('-created_at')
        )

    def retrieve(self, request, pk=None):
        queryset = Notification.objects.all()
        notification = get_object_or_404(queryset, pk=pk)

        notification.open(request.user)

        serializer = NotificationSerializer(notification)
        return Response(serializer.data)

    @paginate
    @action(detail=False)
    def list_user_notifications(self, request, pk=None):
        notifications = utils.filter_for_user_notifications(
            self.filter_queryset(self.get_queryset()), request)
        return notifications

    @action(detail=True)
    def open_notification(self, request, pk):
        notification_status, created = self.get_object().open(request.user)
        return Response(status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @paginate
    @action(detail=False)
    def last_task_notifications(self, request, pk=None):
        q = self.filter_queryset(self.get_queryset()) \
            .exclude(Q(receiver_task__isnull=True) &
                     Q(sender_task__isnull=True)) \
            .select_related('receiver_task') \
            .order_by('receiver_task', '-created_at') \
            .distinct('receiver_task')
        return q


class ResponseFlattenerViewSet(viewsets.ModelViewSet):
    filterset_fields = {
        'task_stage': ['exact'],
        'task_stage__chain__campaign': ['exact'],
        'task_stage__chain': ['exact'],
        'created_at': ['lte', 'gte', 'lt', 'gt'],
        'updated_at': ['lte', 'gte', 'lt', 'gt']
    }
    permission_classes = (ResponseFlattenerAccessPolicy,)

    def get_queryset(self):
        return ResponseFlattenerAccessPolicy.scope_queryset(
            self.request, ResponseFlattener.objects.all()
        )

    def get_serializer_class(self):
        if self.action in ['create', 'partial_update', 'update']:
            return ResponseFlattenerCreateSerializer
        if self.action in ['retrieve', 'list']:
            return ResponseFlattenerReadSerializer

    @action(detail=True)
    def csv(self, request, pk=None):
        response_flattener = self.get_object()
        tasks = response_flattener.task_stage.tasks.all()
        filename = 'results'
        response = HttpResponse(
            content_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}.csv"'
            },
        )
        items = []
        columns = set()
        for task in tasks:
            row = response_flattener.flatten_response(task)
            items.append(row)
            [columns.add(i) for i in row.keys()]
        ordered_columns = response_flattener.ordered_columns()

        columns_not_in_main_schema = utils.array_difference(columns,
                                                            ordered_columns + response_flattener.columns)
        if columns_not_in_main_schema:
            for i in items:
                for column in columns_not_in_main_schema:
                    if column in i.keys():
                        del i[column]
            col = ["description"]
            ordered_columns += col
            items[0][col[0]] = ", ".join(columns_not_in_main_schema)

        writer = csv.DictWriter(response, fieldnames=ordered_columns)
        writer.writeheader()
        writer.writerows(items)
        return response


class TaskAwardViewSet(viewsets.ModelViewSet):
    filterset_fields = {
        'task_stage_completion': ['exact'],
        'task_stage_verified': ['exact'],
        'rank': ['exact'],
        'count': ['lte', 'gte', 'lt', 'gt'],
        'created_at': ['lte', 'gte', 'lt', 'gt'],
        'updated_at': ['lte', 'gte', 'lt', 'gt']
    }

    permission_classes = (TaskAwardAccessPolicy,)

    def get_queryset(self):
        return TaskAwardAccessPolicy.scope_queryset(
            self.request, TaskAward.objects.all()
        )

    def get_serializer_class(self):
        return TaskAwardSerializer


class DynamicJsonViewSet(viewsets.ModelViewSet):
    filterset_fields = {
        'task_stage': ['exact'],
    }

    permission_classes = (DynamicJsonAccessPolicy,)

    def get_queryset(self):
        return DynamicJsonAccessPolicy.scope_queryset(
            self.request, DynamicJson.objects.all()
        )

    def get_serializer_class(self):
        return DynamicJsonReadSerializer


class TestWebhookViewSet(viewsets.ModelViewSet):
    serializer_class = TestWebhookSerializer
    queryset = TestWebhook.objects.all()

    @action(detail=True, methods=['get'])
    def check_result(self, request, pk=None):
        test_webhook = TestWebhook.objects.get(pk=pk)
        expected_task = test_webhook.expected_task
        sent_task = test_webhook.sent_task
        webhook = Webhook.objects.filter(task_stage=expected_task.stage.pk).get()
        if webhook:
            response = requests.post(webhook.url, json=sent_task.responses, headers={}).json()
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if response == expected_task.responses:
            return Response({'equals': True,
                             'response': response})
        return Response({'equals': False,
                         'expected_response': expected_task.responses,
                         'actual_response': response})