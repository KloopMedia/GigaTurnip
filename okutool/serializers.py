from okutool.constants import StageType
from rest_framework import serializers
from .models import Volume, Stage, Task, Question, QuestionAttachment
from django.db.models import Q, Count


class VolumeSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Volume
        fields = "__all__"

    def get_progress(self, obj):
        # Filter stages based on volume and type, and annotate with complete task count
        stages_with_progress = Stage.objects.filter(
            volume=obj, type__in=[StageType.THEORY, StageType.TEST]
        ).annotate(complete_task_count=Count("tasks", filter=Q(tasks__complete=True)))

        # Calculate total and completed tasks
        total_tasks = stages_with_progress.count()
        completed_tasks = stages_with_progress.filter(complete_task_count__gt=0).count()

        # Calculate progress as a percentage
        if total_tasks > 0:
            progress = (completed_tasks / total_tasks) * 100
        else:
            progress = 0

        return progress


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"


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


class StageSerializer(serializers.ModelSerializer):
    task = serializers.SerializerMethodField()
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Stage
        fields = "__all__"

    def get_task(self, obj):
        user = self.context["request"].user
        task = Task.objects.filter(stage=obj, assignee=user).first()
        if task:
            return TaskSerializer(task).data
        return None
