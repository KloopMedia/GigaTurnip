from api.models.stage.stage import Stage
from api.models.stage.task_stage import TaskStage
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Question, QuestionAttachment, Test
from .serializers import (
    QuestionSerializer,
    QuestionAttachmentSerializer,
    StageSerializer,
    TestSerializer,
)


class StageViewSet(viewsets.ModelViewSet):
    queryset = TaskStage.objects.all()
    serializer_class = StageSerializer
    pagination_class = None

    def get_queryset(self):
        return StageSerializer.setup_eager_loading(super().get_queryset())

    @action(detail=False, methods=["GET"])
    def chained_stages(self, request):
        volume = request.query_params.get("volume")

        # Find all stages that don't have any in_stages (root stages)
        if (volume is None):
            root_stages = TaskStage.objects.filter(in_stages__isnull=True)
        else:
            root_stages = TaskStage.objects.filter(volumes=volume, in_stages__isnull=True)

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


class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.all()
    serializer_class = TestSerializer

    def get_queryset(self):
        return TestSerializer.setup_eager_loading(super().get_queryset())


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    def get_queryset(self):
        return QuestionSerializer.setup_eager_loading(super().get_queryset())


class QuestionAttachmentViewSet(viewsets.ModelViewSet):
    queryset = QuestionAttachment.objects.all()
    serializer_class = QuestionAttachmentSerializer

    def get_queryset(self):
        return self.queryset.select_related("question")
