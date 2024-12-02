from api.models.stage.task_stage import TaskStage
from okutool.constants import StageType
from rest_framework import serializers
from .models import Test, Question, QuestionAttachment
from random import sample, shuffle
from django.db.models import Prefetch
from django.conf import settings


class QuestionAttachmentSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = QuestionAttachment
        fields = ["id", "type", "file", "question"]

    def get_file(self, obj):
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None


class QuestionSerializer(serializers.ModelSerializer):
    attachments = QuestionAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.prefetch_related("attachments")


class TestSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = "__all__"

    def get_questions(self, obj):
        question_limit = obj.question_limit
        order_by = obj.order_by

        questions = obj.questions.all()

        if order_by == "IND":
            questions = questions.order_by("index")
            if question_limit > 0:
                questions = questions[:question_limit]
        else:
            questions = list(questions)
            if question_limit > 0 and question_limit < len(questions):
                questions = sample(questions, question_limit)
            else:
                shuffle(questions)

        return QuestionSerializer(questions, many=True, context=self.context).data

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.prefetch_related(
            Prefetch(
                "questions",
                queryset=QuestionSerializer.setup_eager_loading(Question.objects.all()),
            )
        )


class StageSerializer(serializers.ModelSerializer):
    test = TestSerializer(read_only=True)

    class Meta:
        model = TaskStage
        fields = ["id", "name", "description", "rich_text", "test", "in_stages", "out_stages"]

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("test").prefetch_related(
            Prefetch(
                "test__questions",
                queryset=QuestionSerializer.setup_eager_loading(Question.objects.all()),
            )
        )
