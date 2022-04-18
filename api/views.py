import csv

from django.db.models import Count, Q
from django.http import HttpResponse, Http404
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
    Notification, NotificationStatus, ResponseFlattener
from api.serializer import CampaignSerializer, ChainSerializer, \
    TaskStageSerializer, ConditionalStageSerializer, \
    CaseSerializer, RankSerializer, RankLimitSerializer, \
    TrackSerializer, RankRecordSerializer, TaskCreateSerializer, \
    TaskEditSerializer, TaskDefaultSerializer, \
    TaskRequestAssignmentSerializer, \
    TaskStageReadSerializer, CampaignManagementSerializer, TaskSelectSerializer, \
    NotificationSerializer, NotificationStatusSerializer, TaskAutoCreateSerializer, TaskPublicSerializer, \
    TaskStagePublicSerializer, ResponseFlattenerCreateSerializer, ResponseFlattenerReadSerializer
from api.asyncstuff import process_completed_task
from api.permissions import CampaignAccessPolicy, ChainAccessPolicy, \
    TaskStageAccessPolicy, TaskAccessPolicy, RankAccessPolicy, \
    RankRecordAccessPolicy, TrackAccessPolicy, RankLimitAccessPolicy, \
    ConditionalStageAccessPolicy, CampaignManagementAccessPolicy, NotificationAccessPolicy, \
    NotificationStatusesAccessPolicy, PublicCSVAccessPolicy, ResponseFlattenerAccessPolicy
from . import utils
from .utils import paginate

from datetime import datetime


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

    @action(detail=False)
    def list_user_campaigns(self, request):
        campaigns = utils.filter_for_user_campaigns(self.get_queryset(),
                                                    request)
        serializer = self.get_serializer(campaigns, many=True)
        return Response(serializer.data)

    @action(detail=False)
    def list_user_selectable(self, request):
        campaigns = utils \
            .filter_for_user_selectable_campaigns(self.get_queryset(), request)
        serializer = self.get_serializer(campaigns, many=True)
        return Response(serializer.data)


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

        if self.action == 'create' or \
                self.action == 'update' or \
                self.action == 'partial_update':
            return TaskStageSerializer
        elif self.action == 'public':
            return TaskStagePublicSerializer
        else:
            return TaskStageReadSerializer

    def get_queryset(self):
        if self.action == 'list':
            return TaskStageAccessPolicy.scope_queryset(
                self.request, TaskStage.objects.all()
            )
        else:
            return TaskStage.objects.all()

    @action(detail=False)
    def user_relevant(self, request):
        stages = self.filter_queryset(self.get_queryset())
        stages = utils.filter_for_user_creatable_stages(stages, request)
        serializer = self.get_serializer(stages, many=True)
        return Response(serializer.data)

    @action(detail=False)
    def public(self, request):
        stages = self.filter_queryset(self.get_queryset())
        stages = stages.filter(
            Q(is_public=True) | Q(publisher__is_public=True))
        serializer = self.get_serializer(stages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'get'])
    def create_task(self, request, pk=None):
        case = Case.objects.create()
        stage = self.get_object()
        task = Task(stage=stage, assignee=request.user, case=case)
        for copy_field in stage.copy_fields.all():
            task = copy_field.copy_response(task)
        task.save()
        return Response({'status': 'New task created', 'id': task.id})


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


class ResponsesFilter(filters.SearchFilter):
    search_param = "task_responses"
    search_title = _('Task Responses Filter')

    def to_html(self, request, queryset, view):
        return ""

    def get_search_terms(self, request):
        """
        Search term is set by a ?search=... query parameter.
        """
        params = request.query_params.get(self.search_param, '')
        if not params:
            return None
        params = utils.str_to_responses_dict(params)
        return params

    def filter_queryset(self, request, queryset, view):

        search_fields = self.get_search_fields(view, request)
        search_term = self.get_search_terms(request)

        if not search_fields or not search_term:
            return queryset

        tasks = Task.objects.filter(stage__id=search_term["stage"])
        tasks = tasks.filter(**search_term["responses"])
        cases = Case.objects.filter(tasks__in=tasks).distinct()
        response = queryset.filter(case__in=cases)
        return response


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


class ResponsesContainFilter(filters.SearchFilter):
    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        search_term = self.get_search_terms(request)

        if not search_fields or not search_term:
            return queryset

        queryset = super().filter_queryset(request, queryset, view)
        cases = Case.objects.filter(tasks__in=queryset).distinct()
        response = Task.objects.filter(case__in=cases)
        return response


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

    # filterset_fields = ['case',
    #                     'stage',
    #                     'stage__chain__campaign',
    #                     'stage__chain',
    #                     'assignee',
    #                     'complete',
    #                     'created_at',
    #                     'created_at',
    #                     'updated_at',
    #                     'updated_at']
    filterset_fields = {
        'case': ['exact'],
        'stage': ['exact'],
        'stage__chain__campaign': ['exact'],
        'stage__chain': ['exact'],
        'assignee': ['exact'],
        'assignee__ranks': ['exact'],
        'complete': ['exact'],
        'created_at': ['lte', 'gte', 'lt', 'gt'],
        'updated_at': ['lte', 'gte', 'lt', 'gt']
    }
    search_fields = ['responses']
    filter_backends = [DjangoFilterBackend, ResponsesFilter, ResponsesContainFilter]
    permission_classes = (TaskAccessPolicy,)

    def get_queryset(self):
        if self.action in ['list', 'csv', 'user_activity_csv']:
            return TaskAccessPolicy.scope_queryset(
                self.request, Task.objects.all()
            )
        else:
            return Task.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return TaskAutoCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return TaskEditSerializer
        elif self.action == 'request_assignment':
            return TaskRequestAssignmentSerializer
        elif self.action == 'user_selectable':
            return TaskSelectSerializer
        elif self.action == 'public':
            return TaskPublicSerializer
        else:
            return TaskDefaultSerializer

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
                return Response(
                    {"message": "You may not submit this task!",
                     "id": instance.id},
                    status=status.HTTP_403_FORBIDDEN)
            try:
                task = instance.set_complete(
                    responses=serializer.validated_data.get("responses", {}),
                    complete=complete
                )
                if complete:
                    next_direct_task = process_completed_task(task)
            except Task.CompletionInProgress:
                return Response(
                    {"message": "Task is being completed!",
                     "id": instance.id},
                    status=status.HTTP_403_FORBIDDEN)
            except Task.AlreadyCompleted:
                return Response(
                    {"message": "Task is already complete!",
                     "id": instance.id},
                    status=status.HTTP_403_FORBIDDEN)
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

    @action(detail=False)
    def user_relevant(self, request):
        """
        Get:
        Return a list of tasks where user is task assignee.
        """
        queryset = self.filter_queryset(self.get_queryset())
        tasks = queryset.filter(assignee=request.user) \
            .exclude(stage__assign_user_by="IN")
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @paginate
    @action(detail=False)
    def user_selectable(self, request):
        """
        Get:
        Return a list of not assigned
        uncompleted tasks that are allowed to the user.
        """
        tasks = self.filter_queryset(self.get_queryset())
        return utils.filter_for_user_selectable_tasks(tasks, request)

    @paginate
    @action(detail=False)
    def public(self, request):
        tasks = self.filter_queryset(self.get_queryset())
        tasks = tasks.filter(
            Q(stage__is_public=True) |
            (Q(stage__publisher__is_public=True) & Q(complete=True)))
        return tasks

    @action(detail=False)
    def user_activity_csv(self, request):
        """
        Get:
        Return list of activities on stages. Note: if you want download csv file you have to set 'csv' in params as true

        Also for custom statistics you can use filters. And on top of all that you can use filters in csv using 'task_responses' key in params.
        Params for example:
        ?csv=true&task_responses={"a":"b"}
        """
        groups = []
        if request.query_params.get("csv", None):
            tasks = self.filter_queryset(self.get_queryset())
            groups = tasks.values('stage__name', 'assignee').annotate(Count('pk'))
            filename = "results"  # utils.request_to_name(request)
            response = HttpResponse(
                content_type='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}.csv"'
                },
            )
            fieldnames = ["assignee",
                          "stage__name",
                          "pk__count"]
            writer = csv.DictWriter(response, fieldnames=fieldnames)
            writer.writeheader()
            for group in groups:
                writer.writerow(group)
            return response
        return Response(groups)

    @action(detail=False, )  # pk is stage id
    def csv(self, request):
        """
        Get:
        Return csv file with tasks information. Note: params stage and response_flattener are important

        Also for custom statistics you can use filters. And on top of all that you can use filters in csv using 'task_responses' key in params.
        Params for example:
        ?stage=1&response_flattener=1&task_responses={"a":"b"}
        """
        response_flattener_id = request.query_params.get('response_flattener')
        items = []
        if response_flattener_id and response_flattener_id.isdigit():
            tasks = []
            try:
                response_flattener = ResponseFlattener.objects.get(id=response_flattener_id)
                tasks = self.filter_queryset(self.get_queryset()).filter(stage=response_flattener.task_stage)
            except ResponseFlattener.DoesNotExist:
                response_flattener = None
            if tasks and response_flattener:
                filename = "results"  # utils.request_to_name(request)
                response = HttpResponse(
                    content_type='text/csv',
                    headers={
                        'Content-Disposition': f'attachment; filename="{filename}.csv"'
                    },
                )
                columns = set()
                for task in tasks:
                    row = response_flattener.flatten_response(task)
                    items.append(row)
                    [columns.add(i) for i in row.keys()]
                ordered_columns = response_flattener.ordered_columns()

                columns_not_in_main_schema = utils.array_difference(columns, ordered_columns+response_flattener.columns)
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
        if items:
            return Response(items)
        else:
            raise Http404

    @action(detail=True)
    def get_integrated_tasks(self, request, pk=None):
        """
        Get:
        Return integrated tasks
        """
        tasks = self.filter_queryset(self.get_queryset())
        tasks = tasks.filter(out_tasks=self.get_object())
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'get'])
    def request_assignment(self, request, pk=None):
        # todo: ask about post and get requests
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
        return Response(
            {'message': 'It is impossible to release this task.'},
            status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post', 'get'])
    def uncomplete(self, request, pk=None):
        task = self.get_object()
        try:
            task.set_not_complete()
            return Response({'status': 'Assignment uncompleted', 'id': task.id})
        except Task.ImpossibleToUncomplete:
            return Response(
                {'message': 'It is impossible to uncomplete this task.'},
                status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=True, methods=['post', 'get'])
    def open_previous(self, request, pk=None):
        task = self.get_object()
        try:
            (prev_task, task) = task.open_previous()
            return Response({'status': 'Previous task opened.', 'id': prev_task.id})
        except Task.ImpossibleToOpenPrevious:
            return Response(
                {'message': 'It is impossible to open previous task.'},
                status=status.HTTP_403_FORBIDDEN
            )

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

    @action(detail=True, methods=['get'])
    def list_displayed_previous(self, request, pk=None):
        tasks = self.get_object().get_displayed_prev_tasks()
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

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
                return Response({"error_message": error_description,
                                 "status": response.status_code},
                                status=status.HTTP_400_BAD_REQUEST)
        # django_response = HttpResponse(
        #     content=response.content,
        #     status=response.status_code,
        #     content_type=response.headers['Content-Type']
        # )
        return


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

    filterset_fields = ['importance', 'campaign', 'rank']
    serializer_class = NotificationSerializer

    permission_classes = (NotificationAccessPolicy,)

    def get_queryset(self):
        return NotificationAccessPolicy.scope_queryset(
            self.request, Notification.objects.all().order_by('-created_at')
        )

    def retrieve(self, request, pk=None):
        queryset = Notification.objects.all()
        notification = get_object_or_404(queryset, pk=pk)

        notification.open(request)

        serializer = NotificationSerializer(notification)
        return Response(serializer.data)

    @paginate
    @action(detail=False)
    def list_user_notifications(self, request, pk=None):
        notifications = utils.filter_for_user_notifications(self.get_queryset(),
                                                            request)
        return notifications

    @action(detail=True)
    def open_notification(self, request, pk):
        notification_status, created = self.get_object().open(request)
        notification_status_json = NotificationStatusSerializer(instance=notification_status).data
        if notification_status and created:
            return Response({'status': status.HTTP_201_CREATED,
                             'notification_status': notification_status_json})
        elif notification_status and not created:
            return Response({'status': status.HTTP_200_OK,
                             'notification_status': notification_status_json})
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class NotificationStatusViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing notification statuses.
    create:
    Create a new campaign management notification status.
    delete:
    Delete notification status.
    read:
    Get notification status data.
    update:
    Update notification status data.
    partial_update:
    Partial update notification status data.
    """

    serializer_class = NotificationStatusSerializer

    permission_classes = (NotificationStatusesAccessPolicy,)

    def get_queryset(self):
        return NotificationStatusesAccessPolicy.scope_queryset(
            self.request, NotificationStatus.objects.all()
        )


class PublicCSVViewSet(viewsets.ViewSet):
    """
    A view that returns the count of active users, in JSON or YAML.
    """

    permission_classes = (PublicCSVAccessPolicy,)

    # renderer_classes = (JSONRenderer, YAMLRenderer)

    def list(self, request, format=None):
        tasks = Task.objects.filter(stage__is_public=True, stage__id=871)
        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename="results.csv"'},
        )
        fieldnames = ["uik",
                      "text",
                      "time",
                      "files",
                      "violation_type",
                      "violation_subtype",
                      "complaint",
                      "location"]
        writer = csv.DictWriter(response, fieldnames=fieldnames)
        writer.writeheader()

        for task in tasks:
            uik = task.responses.get("uik", "")
            text = task.responses.get("text", "")
            time = task.responses.get("time", "")
            location = task.responses.get("uiks_location", "")
            files = " ".join(task.responses.get("youtube", []))
            violations = task.responses.get("violations", {})
            violation_type = ""
            violation_subtype = ""
            complaint = ""
            for key in violations:
                if "type_violation" in key:
                    violation_type = violations[key]
                elif "subtype_violation" in key:
                    violation_subtype = violations[key]
                elif "complaint" in key:
                    complaint = violations[key]
            writer.writerow({"uik": uik,
                             "text": text,
                             "time": time,
                             "files": files,
                             "violation_type": violation_type,
                             "violation_subtype": violation_subtype,
                             "complaint": complaint,
                             "location": location})
        return response


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
