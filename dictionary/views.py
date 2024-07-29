from rest_framework import filters, generics, permissions, viewsets
from django.db.models import Count

from dictionary.models import Category, ProficiencyLevel, Word
from dictionary.serializers import (
    CategorySerializer,
    ProficiencyLevel,
    ProficiencyLevelSerializer,
    WordSerializer,
)


class WordViewSet(viewsets.ModelViewSet):
    queryset = Word.objects.all().order_by("text")
    serializer_class = WordSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.annotate(word_count=Count("word"))
    serializer_class = CategorySerializer


class ProficiencyLevelViewSet(viewsets.ModelViewSet):
    queryset = ProficiencyLevel.objects.all()
    serializer_class = ProficiencyLevelSerializer
