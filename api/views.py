from django.db.models import Count
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
    TaskDefaultSerializer, TaskRequestAssignmentSerializer
from api.permissions import CampaignAccessPolicy


class CampaignViewSet(viewsets.ModelViewSet):

    serializer_class = CampaignSerializer
    queryset = Campaign.objects.all()

    # permission_classes = (CampaignAccessPolicy,)


class ChainViewSet(viewsets.ModelViewSet):
    filterset_fields = ['campaign', ]
    serializer_class = ChainSerializer
    queryset = Chain.objects.all()


class TaskStageViewSet(viewsets.ModelViewSet):
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
        tasks = Task.objects.filter(assignee=request.user.id)\
            .filter(stage__in=stages).distinct()
        tasks_count = tasks.values('stage', 'complete')\
            .annotate(count=Count('id'))
        print(tasks_count)
        serializer = self.get_serializer(stages, many=True)
        return Response(serializer.data)


class WebHookStageViewSet(viewsets.ModelViewSet):
    filterset_fields = ['chain', ]
    queryset = WebHookStage.objects.all()
    serializer_class = WebHookStageSerializer


class ConditionalStageViewSet(viewsets.ModelViewSet):
    filterset_fields = ['chain', ]
    queryset = ConditionalStage.objects.all()
    serializer_class = ConditionalStageSerializer


class CaseViewSet(viewsets.ModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer


class TaskViewSet(viewsets.ModelViewSet):
    filterset_fields = ['stage',
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
        elif self.action == 'release_assignment':
            return TaskRequestAssignmentSerializer
        else:
            return TaskDefaultSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            data = serializer.data
            # data.update({'pid': pid})  # attaching key-value to the dictionary
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({'status': 'assignment granted'})
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
    queryset = Rank.objects.all()
    serializer_class = RankSerializer


class RankRecordViewSet(viewsets.ModelViewSet):
    queryset = RankRecord.objects.all()
    serializer_class = RankRecordSerializer


class RankLimitViewSet(viewsets.ModelViewSet):
    filterset_fields = ['rank', ]
    queryset = RankLimit.objects.all()
    serializer_class = RankLimitSerializer


class TrackViewSet(viewsets.ModelViewSet):
    queryset = Track.objects.all()
    serializer_class = TrackSerializer
