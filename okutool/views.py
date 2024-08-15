from api.models.stage.task_stage import TaskStage
from rest_framework import viewsets
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

    def get_queryset(self):
        return StageSerializer.setup_eager_loading(super().get_queryset())


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
