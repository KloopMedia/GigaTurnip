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

    @action(detail=False, methods=["get"])
    def chained_stages(self, request):
        # Find all stages that don't have any in_stages (root stages)
        root_stages = Stage.objects.filter(in_stages__isnull=True)

        # Function to recursively build the chain
        def build_chain(stage):
            chain = [stage]
            # Get the next stage(s) in the chain
            next_stages = stage.out_stages.all()
            for next_stage in next_stages:
                chain.extend(build_chain(next_stage))
            return chain

        # Build the full chain starting from each root stage
        chained_stages = []
        for root_stage in root_stages:
            chained_stages.extend(build_chain(root_stage))

        # Serialize the stages
        serializer = self.get_serializer(chained_stages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="get-or-create-task")
    def get_or_create_task(self, request, pk=None):
        def create_default_task(user, stage):
            return Task.objects.create(
                assignee=user,
                stage=stage,
                complete=False,
                total_count=0,
                successful_count=0,
                last_score=0,
            )

        try:
            stage = self.get_object()
            user = request.user

            if not user:
                return Response(
                    {"detail": "User is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if the user already has a task for the current stage
            current_task = Task.objects.filter(stage=stage, assignee=user)
            if current_task.exists():
                serializer = TaskSerializer(current_task.first())
                return Response(serializer.data, status=status.HTTP_200_OK)

            # Get all previous stages
            previous_stages = stage.in_stages.all()
            if previous_stages.exists():
                # Get all previous tasks related to these stages
                previous_tasks = Task.objects.filter(
                    stage__in=previous_stages, assignee=user
                )

                if not previous_tasks.exists():
                    return Response(
                        {
                            "detail": "Cannot create a new task until all previous tasks are completed."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Check if any previous tasks are incomplete
                incomplete_tasks = previous_tasks.filter(complete=False)
                if incomplete_tasks.exists():
                    return Response(
                        {
                            "detail": "Cannot create a new task until all previous tasks are completed."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Create a new task if no incomplete tasks
            task = create_default_task(user, stage)
            serializer = TaskSerializer(task)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
