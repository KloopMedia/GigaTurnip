from django.db.models import Count
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.models import Campaign, Chain, TaskStage, \
    WebHookStage, ConditionalStage, Case, Task, Rank, \
    RankLimit, Track, RankRecord
from api.serializer import CampaignSerializer, ChainSerializer, \
    TaskStageSerializer, WebHookStageSerializer, ConditionalStageSerializer, \
    CaseSerializer, RankSerializer, RankLimitSerializer, \
    TrackSerializer, RankRecordSerializer, TaskCreateSerializer, TaskEditSerializer, \
    TaskDefaultSerializer
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
        else:
            return TaskDefaultSerializer

    @action(detail=False)
    def user_relevant(self, request):
        tasks = self.filter_queryset(self.get_queryset()) \
            .filter(assignee=request.user)
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)


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
