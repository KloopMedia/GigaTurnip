from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView

from api.models import Campaign, Chain, Stage, TaskStage, \
    WebHookStage, ConditionalStage, Case, \
    Task
from api.serializer import CampaignSerializer, ChainSerializer, \
    TaskStageSerializer, \
    WebHookStageSerializer, ConditionalStageSerializer, \
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


# class AllStages(ListAPIView):
#
#     queryset = Stage.objects.all()
#     serializer_class = StageSerializer
#
#     def post(self, request, format=None):
#         serializer = StageSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#
#
# class StageView(APIView):
#
#     def get(self, request, pk, format=None):
#         try:
#             item = Stage.objects.get(pk=pk)
#             serializer = StageSerializer(item)
#             return Response(serializer.data)
#         except:
#             return Response(status=status.HTTP_404_NOT_FOUND)
#
#     def delete(self, request, pk, format=None):
#         item = Stage.objects.get(pk=pk)
#         item.delete()
#         return Response(status=status.HTTP_200_OK)


class AllTaskStage(ListAPIView):

    queryset = TaskStage.objects.all()
    serializer_class = TaskStageSerializer

    def post(self, request, format=None):
        serializer = TaskStageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskStageView(APIView):

    def get(self, request, pk, format=None):
        try:
            item = TaskStage.objects.get(pk=pk)
            serializer = TaskStageSerializer(item)
            return Response(serializer.data)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk, format=None):
        item = TaskStage.objects.get(pk=pk)
        item.delete()
        return Response(status=status.HTTP_200_OK)


class AllWebHookStageFillers(ListAPIView):

    queryset = WebHookStage.objects.all()
    serializer_class = WebHookStageSerializer

    def post(self, request, format=None):
        serializer = WebHookStageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WebHookStageFillerView(APIView):

    def get(self, request, pk, format=None):
        try:
            item = WebHookStage.objects.get(pk=pk)
            serializer = WebHookStageSerializer(item)
            return Response(serializer.data)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk, format=None):
        item = WebHookStage.objects.get(pk=pk)
        item.delete()
        return Response(status=status.HTTP_200_OK)


class AllConditionalStageFillers(ListAPIView):

    queryset = ConditionalStage.objects.all()
    serializer_class = ConditionalStageSerializer

    def post(self, request, format=None):
        serializer = ConditionalStageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConditionalStageFillerView(APIView):

    def get(self, request, pk, format=None):
        try:
            item = ConditionalStage.objects.get(pk=pk)
            serializer = ConditionalStageSerializer(item)
            return Response(serializer.data)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk, format=None):
        item = ConditionalStage.objects.get(pk=pk)
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








