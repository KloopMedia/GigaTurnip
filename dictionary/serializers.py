from rest_framework import serializers

from dictionary.models import Category, Word, ProficiencyLevel


class WordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Word
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    word_count = serializers.IntegerField()

    class Meta:
        model = Category
        fields = "__all__"


class ProficiencyLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProficiencyLevel
        fields = "__all__"
