from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.models import Campaign, Chain, TaskStage, \
    ConditionalStage, Case, Task, Rank, \
    RankLimit, Track, RankRecord, CampaignManagement
from api.serializer import CampaignSerializer, ChainSerializer, \
    TaskStageSerializer, ConditionalStageSerializer, \
    CaseSerializer, RankSerializer, RankLimitSerializer, \
    TrackSerializer, RankRecordSerializer, TaskCreateSerializer, \
    TaskEditSerializer, TaskDefaultSerializer,\
    TaskRequestAssignmentSerializer, \
    TaskStageReadSerializer, CampaignManagementSerializer
from api.asyncstuff import process_completed_task
from api.permissions import CampaignAccessPolicy, ChainAccessPolicy, \
    TaskStageAccessPolicy, TaskAccessPolicy, RankAccessPolicy, \
    RankRecordAccessPolicy, TrackAccessPolicy, RankLimitAccessPolicy, \
    ConditionalStageAccessPolicy, CampaignManagementAccessPolicy
from . import utils


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
        campaigns = utils\
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

    @action(detail=True, methods=['post', 'get'])
    def create_task(self, request, pk=None):
        case = Case.objects.create()
        task = Task(stage=self.get_object(), assignee=request.user, case=case)
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
    Assign user to requested task
    release_assignment:
    Release user from requested task
    """

    filterset_fields = ['case',
                        'stage',
                        'stage__chain__campaign',
                        'assignee',
                        'complete']
    permission_classes = (TaskAccessPolicy,)

    def get_queryset(self):
        if self.action == 'list':
            return TaskAccessPolicy.scope_queryset(
                self.request, Task.objects.all()
            )
        else:
            return Task.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return TaskCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return TaskEditSerializer
        elif self.action == 'request_assignment':
            return TaskRequestAssignmentSerializer
        else:
            return TaskDefaultSerializer

    def create(self, request, *args, **kwargs):
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
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance,
                                         data=request.data,
                                         partial=partial)
        if serializer.is_valid():
            serializer.save()
            if getattr(instance, '_prefetched_objects_cache', None):
                # If 'prefetch_related' has been applied to a queryset,
                # we need to forcibly invalidate the prefetch
                # cache on the instance.
                instance._prefetched_objects_cache = {}
            data = serializer.data
            data['id'] = instance.id
            if data['complete']:
                process_completed_task(instance)
            # if data['complete']:
            #     result(async_task(process_completed_task,
            #                data['id'],
            #                task_name='process_completed_task',
            #                group='follow_chain'))
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=False)
    def user_relevant(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        tasks = queryset.filter(assignee=request.user)
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False)
    def user_selectable(self, request):
        queryset_tasks = self.filter_queryset(self.get_queryset())
        tasks = utils.filter_for_user_selectable_tasks(
            queryset_tasks,
            request)
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'get'])
    def request_assignment(self, request, pk=None):
        task = self.get_object()
        serializer = self.get_serializer(task, request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'assignment granted', 'id': task.id})
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'get'])
    def release_assignment(self, request, pk=None):
        task = self.get_object()
        task.assignee = None
        task.save()
        return Response({'status': 'assignment released'})

    @action(detail=True, methods=['get'])
    def list_displayed_previous(self, request, pk=None):
        tasks = self.get_object().get_displayed_prev_tasks()
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)


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