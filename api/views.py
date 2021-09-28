from django.db.models import Count
from django_q.tasks import async_task, result
from rest_framework import generics, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.models import Campaign, Chain, TaskStage, \
    WebHookStage, ConditionalStage, Case, Task, Rank, \
    RankLimit, Track, RankRecord
from api.serializer import CampaignSerializer, ChainSerializer, \
    TaskStageSerializer, WebHookStageSerializer, ConditionalStageSerializer, \
    CaseSerializer, RankSerializer, RankLimitSerializer, \
    TrackSerializer, RankRecordSerializer, TaskCreateSerializer, TaskEditSerializer, \
    TaskDefaultSerializer, TaskRequestAssignmentSerializer, TaskStageReadSerializer
from api.asyncstuff import process_completed_task
#from api.permissions import CampaignAccessPolicy


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
    """

    serializer_class = CampaignSerializer
    queryset = Campaign.objects.all()

    # permission_classes = (CampaignAccessPolicy,)


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
    queryset = Chain.objects.all()


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

    def get_serializer_class(self):
        """
        get_serializer_class:
        Выбирает нужные сериалайзер (для чтения или обычный).
        """

        if self.action == 'create' or self.action == 'update' or self.action == 'partial_update':
            return TaskStageSerializer
        else:
            return TaskStageReadSerializer

    # filterset_fields = ['chain', 'chain__campaign', 'is_creatable', 'ranks',
    #                     'ranks__users', 'ranklimits__open_limit',
    #                     'ranklimits__total_limit',
    #                     'ranklimits__is_creation_open']
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
    queryset = TaskStage.objects.all()
    serializer_class = TaskStageSerializer

    @action(detail=False)
    def user_relevant(self, request):
        stages = self.filter_queryset(self.get_queryset())\
            .filter(is_creatable=True)\
            .filter(ranks__users=request.user.id)\
            .filter(ranklimits__is_creation_open=True)\
            .distinct()
        filtered_stages = TaskStage.objects.none()
        for stage in stages:
            tasks = Task.objects.filter(assignee=request.user.id)\
                .filter(stage=stage).distinct()
            total = len(tasks)
            print(total)
            incomplete = len(tasks.filter(complete=False))
            print(incomplete)
            ranklimits = RankLimit.objects.filter(stage=stage) \
                .filter(rank__rankrecord__user__id=request.user.id)
            for ranklimit in ranklimits:
                print(ranklimit.total_limit)
                print(ranklimit.open_limit)
                if ((ranklimit.open_limit > incomplete and ranklimit.total_limit > total) or
                        (ranklimit.open_limit == 0 and ranklimit.total_limit > total) or
                        (ranklimit.open_limit > incomplete and ranklimit.total_limit == 0) or
                        (ranklimit.open_limit == 0 and ranklimit.total_limit == 0)
                ):
                    filtered_stages |= TaskStage.objects.filter(pk=stage.pk)

        # tasks_count = tasks.values('stage', 'complete')\
        #     .annotate(count=Count('id'))
        # print(tasks_count)
        serializer = self.get_serializer(filtered_stages.distinct(), many=True)
        return Response(serializer.data)


class WebHookStageViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing webhook stages.

    create:
    Create a new chain webhook stage.

    delete:
    Delete webhook stage.

    read:
    Get webhook stage data.

    update:
    Update webhook stage data.

    partial_update:
    Partial update webhook stage data.
    """

    filterset_fields = ['chain', ]
    queryset = WebHookStage.objects.all()
    serializer_class = WebHookStageSerializer


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
    queryset = ConditionalStage.objects.all()
    serializer_class = ConditionalStageSerializer


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
    Create a new task instance. Note: if task is completed, process_completed_task() function will be called.

    delete:
    Delete task.

    read:
    Get task data.

    update:
    Update task data. Note: if task is completed, process_completed_task() function will be called.

    partial_update:
    Partial update task data.

    user_relevant:
    Return a list of tasks where user is task assignee.

    user_selectable:
    Return a list of not assigned uncompleted tasks that are allowed to the user.

    request_assignment:
    Assign user to requested task

    release_assignment:
    Release user from requested task
    """

    filterset_fields = ['stage',
                        'case',
                        'stage__chain__campaign',
                        'assignee',
                        'complete']
    queryset = Task.objects.all()

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
            serializer.save(case=case)
            data = serializer.data
            if data['complete']:
                process_completed_task(self.get_object())
            # if data['complete']:
            #     result(async_task(process_completed_task,
            #                       data['id'],
            #                       task_name='process_completed_task',
            #                       group='follow_chain'))
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance,
                                         data=request.data,
                                         partial=partial)
        if serializer.is_valid():
            serializer.save()
            if getattr(instance, '_prefetched_objects_cache', None):
                # If 'prefetch_related' has been applied to a queryset, we need to
                # forcibly invalidate the prefetch cache on the instance.
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
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=False)
    def user_relevant(self, request):
        tasks = self.filter_queryset(self.get_queryset()) \
            .filter(assignee=request.user)
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False)
    def user_selectable(self, request):
        tasks = self.filter_queryset(self.get_queryset()) \
            .filter(complete=False) \
            .filter(assignee__isnull=True) \
            .filter(stage__ranks__users=request.user.id) \
            .filter(stage__ranklimits__is_selection_open=True) \
            .filter(stage__ranklimits__is_listing_allowed=True) \
            .distinct()
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'get'])
    def request_assignment(self, request, pk=None): # TODO: Add permissions to block changing assignee
        task = self.get_object()
        serializer = self.get_serializer(task, request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'assignment granted', 'id': task.id})
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'get'])
    def release_assignment(self, request, pk=None):  # TODO: Add permissions to block changing assignee
        task = self.get_object()
        task.assignee = None
        task.save()
        return Response({'status': 'assignment released'})


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
    queryset = Rank.objects.all()
    serializer_class = RankSerializer


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
    queryset = RankRecord.objects.all()
    serializer_class = RankRecordSerializer


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
    queryset = RankLimit.objects.all()
    serializer_class = RankLimitSerializer


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

    queryset = Track.objects.all()
    serializer_class = TrackSerializer
