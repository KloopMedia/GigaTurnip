from rest_framework import generics, viewsets

from api.models import Campaign, Chain, TaskStage, \
    WebHookStage, ConditionalStage, Case, Task
from api.serializer import CampaignSerializer, ChainSerializer, \
    TaskStageSerializer, WebHookStageSerializer, ConditionalStageSerializer, \
    CaseSerializer, TaskSerializer
from api.permissions import CampaignAccessPolicy


class CampaignViewSet(viewsets.ModelViewSet):

    serializer_class = CampaignSerializer
    queryset = Campaign.objects.all()

    # permission_classes = (CampaignAccessPolicy,)


class ChainViewSet(viewsets.ModelViewSet):
    serializer_class = ChainSerializer
    queryset = Chain.objects.all()


class TaskStageViewSet(viewsets.ModelViewSet):
    queryset = TaskStage.objects.all()
    serializer_class = TaskStageSerializer


class WebHookStageViewSet(viewsets.ModelViewSet):
    queryset = WebHookStage.objects.all()
    serializer_class = WebHookStageSerializer


class ConditionalStageViewSet(viewsets.ModelViewSet):
    queryset = ConditionalStage.objects.all()
    serializer_class = ConditionalStageSerializer


class CaseViewSet(viewsets.ModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
