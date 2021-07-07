from rest_framework import generics, viewsets

from api.models import Campaign, Chain, TaskStage, \
    WebHookStage, ConditionalStage, Case, Task, Rank, RankLimit, Track
from api.serializer import CampaignSerializer, ChainSerializer, \
    TaskStageSerializer, WebHookStageSerializer, ConditionalStageSerializer, \
    CaseSerializer, TaskSerializer, RankSerializer, RankLimitSerializer, TrackSerializer
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
    filterset_fields = ['chain', 'chain__campaign', 'is_creatable', 'ranks',
                        'ranks__users']
    queryset = TaskStage.objects.all()
    serializer_class = TaskStageSerializer


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
    filterset_fields = ['stage', 'assignee', 'complete']
    queryset = Task.objects.all()
    serializer_class = TaskSerializer


class RankViewSet(viewsets.ModelViewSet):
    queryset = Rank.objects.all()
    serializer_class = RankSerializer


class RankLimitViewSet(viewsets.ModelViewSet):
    filterset_fields = ['rank', ]
    queryset = RankLimit.objects.all()
    serializer_class = RankLimitSerializer


class TrackViewSet(viewsets.ModelViewSet):
    queryset = Track.objects.all()
    serializer_class = TrackSerializer
