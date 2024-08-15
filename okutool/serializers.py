from okutool.constants import StageType
from rest_framework import serializers
from .models import Test, Question, QuestionAttachment
from random import sample


class QuestionSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = "__all__"

    def get_attachments(self, obj):
        try:
            # Check if request context is available
            request = self.context.get("request")
            if request is None:
                print("Request context is missing")
                return []

            # Check if attachments exist
            attachments = obj.attachments.all()
            if not attachments.exists():
                print(f"No attachments found for Question ID: {obj.id}")
                return []

            # Process attachments
            attachment_list = []
            for attachment in attachments:
                # Debug each attachment
                print(
                    f"Processing attachment ID: {attachment.id}, Type: {attachment.type}"
                )
                attachment_data = {
                    "id": attachment.id,
                    "type": attachment.type,
                    "file": request.build_absolute_uri(attachment.file.url),
                }
                attachment_list.append(attachment_data)

            return attachment_list

        except Exception as e:
            print(f"Error in get_attachments: {e}")
            return []


class QuestionAttachmentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(use_url=True)

    class Meta:
        model = QuestionAttachment
        fields = "__all__"


class TestSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = "__all__"

    def get_questions(self, obj):
        question_limit = obj.question_limit
        enable_sampling = self.context.get("enable_sampling", False)

        if enable_sampling and question_limit > 0:
            questions = list(obj.questions.all())
            if question_limit < len(questions):
                questions = sample(questions, question_limit)
        else:
            # Order questions by index when sampling is off
            questions = obj.questions.order_by("index")

        return QuestionSerializer(questions, many=True).data
