from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Volume, Stage, Task, Question, QuestionAttachment
from .serializers import (
    VolumeSerializer,
    StageSerializer,
    TaskSerializer,
    QuestionSerializer,
    QuestionAttachmentSerializer,
)


class VolumeViewSet(viewsets.ModelViewSet):
    queryset = Volume.objects.all()
    serializer_class = VolumeSerializer


class StageViewSet(viewsets.ModelViewSet):
    queryset = Stage.objects.all()
    serializer_class = StageSerializer

    @action(detail=True, methods=["get"], url_path="get-or-create-task")
    def get_or_create_task(self, request, pk=None):
        try:
            stage = self.get_object()
            user = request.user

            if not user:
                return Response(
                    {"detail": "user is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if a task for this stage and user already exists
            task, created = Task.objects.get_or_create(
                assignee=user,
                stage=stage,
                defaults={
                    "complete": False,
                    "total_count": 0,
                    "successful_count": 0,
                    "last_score": 0,
                },
            )

            serializer = TaskSerializer(task)
            if created:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        task = self.get_object()
        new_score = request.data.get("new_score", None)

        if task.assignee != request.user:
            return Response(
                {"detail": "Not allowed to submit this task."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if new_score is None:
            return Response(
                {"detail": "new_score is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_score = int(new_score)
        except ValueError:
            return Response(
                {"detail": "new_score must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not task.complete:
            task.total_count += 1
            task.last_score = new_score
            if new_score > 80:
                task.successful_count += 1
                task.complete = True
            task.save()
            serializer = self.get_serializer(task)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"status": "task-already-submitted"})


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer


class QuestionAttachmentViewSet(viewsets.ModelViewSet):
    queryset = QuestionAttachment.objects.all()
    serializer_class = QuestionAttachmentSerializer
