from rest_framework import generics

from api.models import Campaign, Chain, TaskStage, \
    WebHookStage, ConditionalStage, Case, Task
from api.serializer import CampaignSerializer, ChainSerializer, \
    TaskStageSerializer, WebHookStageSerializer, ConditionalStageSerializer, \
    CaseSerializer, TaskSerializer


class CampaignList(generics.ListCreateAPIView):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer


class CampaignDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer


class ChainList(generics.ListCreateAPIView):
    queryset = Chain.objects.all()
    serializer_class = ChainSerializer


class ChainDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Chain.objects.all()
    serializer_class = ChainSerializer


class TaskStageList(generics.ListCreateAPIView):
    queryset = TaskStage.objects.all()
    serializer_class = TaskStageSerializer


class TaskStageDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = TaskStage.objects.all()
    serializer_class = TaskStageSerializer


class WebHookStageList(generics.ListCreateAPIView):
    queryset = WebHookStage.objects.all()
    serializer_class = WebHookStageSerializer


class WebHookStageDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = WebHookStage.objects.all()
    serializer_class = WebHookStageSerializer


class ConditionalStageList(generics.ListCreateAPIView):
    queryset = ConditionalStage.objects.all()
    serializer_class = ConditionalStageSerializer


class ConditionalStageDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = ConditionalStage.objects.all()
    serializer_class = ConditionalStageSerializer


class CaseList(generics.ListCreateAPIView):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer


class CaseDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer


class TaskList(generics.ListCreateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer


class TaskDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer








