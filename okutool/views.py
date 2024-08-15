from rest_framework import viewsets

from .models import Question, QuestionAttachment, Test
from .serializers import (
    QuestionSerializer,
    QuestionAttachmentSerializer,
    TestSerializer,
)


class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.all()
    serializer_class = TestSerializer


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer


class QuestionAttachmentViewSet(viewsets.ModelViewSet):
    queryset = QuestionAttachment.objects.all()
    serializer_class = QuestionAttachmentSerializer
