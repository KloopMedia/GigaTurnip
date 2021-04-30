from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView

from api.models import Campaign, Chain, Stage, TaskStageFiller, \
    WebHookStageFiller, ConditionalStageFiller, Case, \
    Task
from api.serializer import CampaignSerializer, ChainSerializer, \
    StageSerializer, TaskStageFillerSerializer, \
    WebHookStageFillerSerializer, ConditionalStageFillerSerializer, \
    CaseSerializer, TaskSerializer, TaskWithSchemaSerializer


# Create your views here.


class AllCampaigns(ListAPIView):

    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer

    def post(self, request, format=None):
        serializer = CampaignSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CampaignView(APIView):

    def get(self, request, pk, format=None):
        try:
            item = Campaign.objects.get(pk=pk)
            serializer = CampaignSerializer(item)
            return Response(serializer.data)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk, format=None):
        item = Campaign.objects.get(pk=pk)
        item.delete()
        return Response(status=status.HTTP_200_OK)


class AllChains(ListAPIView):

    queryset = Chain.objects.all()
    serializer_class = ChainSerializer

    def post(self, request, format=None):
        serializer = ChainSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChainView(APIView):

    def get(self, request, pk, format=None):
        try:
            item = Chain.objects.get(pk=pk)
            serializer = ChainSerializer(item)
            return Response(serializer.data)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk, format=None):
        item = Chain.objects.get(pk=pk)
        item.delete()
        return Response(status=status.HTTP_200_OK)


class AllStages(ListAPIView):

    queryset = Stage.objects.all()
    serializer_class = StageSerializer

    def post(self, request, format=None):
        serializer = StageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StageView(APIView):

    def get(self, request, pk, format=None):
        try:
            item = Stage.objects.get(pk=pk)
            serializer = StageSerializer(item)
            return Response(serializer.data)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk, format=None):
        item = Stage.objects.get(pk=pk)
        item.delete()
        return Response(status=status.HTTP_200_OK)


class AllTaskStageFillers(ListAPIView):

    queryset = TaskStageFiller.objects.all()
    serializer_class = TaskStageFillerSerializer

    def post(self, request, format=None):
        serializer = TaskStageFillerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskStageFillerView(APIView):

    def get(self, request, pk, format=None):
        try:
            item = TaskStageFiller.objects.get(pk=pk)
            serializer = TaskStageFillerSerializer(item)
            return Response(serializer.data)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk, format=None):
        item = TaskStageFiller.objects.get(pk=pk)
        item.delete()
        return Response(status=status.HTTP_200_OK)


class AllWebHookStageFillers(ListAPIView):

    queryset = WebHookStageFiller.objects.all()
    serializer_class = WebHookStageFillerSerializer

    def post(self, request, format=None):
        serializer = WebHookStageFillerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WebHookStageFillerView(APIView):

    def get(self, request, pk, format=None):
        try:
            item = WebHookStageFiller.objects.get(pk=pk)
            serializer = WebHookStageFillerSerializer(item)
            return Response(serializer.data)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk, format=None):
        item = WebHookStageFiller.objects.get(pk=pk)
        item.delete()
        return Response(status=status.HTTP_200_OK)


class AllConditionalStageFillers(ListAPIView):

    queryset = ConditionalStageFiller.objects.all()
    serializer_class = ConditionalStageFillerSerializer

    def post(self, request, format=None):
        serializer = ConditionalStageFillerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConditionalStageFillerView(APIView):

    def get(self, request, pk, format=None):
        try:
            item = ConditionalStageFiller.objects.get(pk=pk)
            serializer = ConditionalStageFillerSerializer(item)
            return Response(serializer.data)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk, format=None):
        item = ConditionalStageFiller.objects.get(pk=pk)
        item.delete()
        return Response(status=status.HTTP_200_OK)


class AllCases(ListAPIView):

    queryset = Case.objects.all()
    serializer_class = CaseSerializer

    def post(self, request, format=None):
        serializer = CaseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CaseView(APIView):

    def get(self, request, pk, format=None):
        try:
            item = Case.objects.get(pk=pk)
            serializer = CaseSerializer(item)
            return Response(serializer.data)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk, format=None):
        item = Case.objects.get(pk=pk)
        item.delete()
        return Response(status=status.HTTP_200_OK)


class AllTasks(ListAPIView):

    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    def post(self, request, format=None):
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskView(APIView):

    def get(self, request, pk, format=None):

        item = Task.objects.get(pk=pk)
        serializer = TaskWithSchemaSerializer(item)
        return Response(serializer.data)

        #return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk, format=None):
        item = Task.objects.get(pk=pk)
        item.delete()
        return Response(status=status.HTTP_200_OK)








