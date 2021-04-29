from rest_framework import serializers

from journalAPI.models import Campaign, Chain, Stage, TaskStageFiller, \
    WebHookStageFiller, ConditionalStageFiller, Case, \
    Task


class CampaignSerializer(serializers.ModelSerializer):

    class Meta:
        model = Campaign
        fields = '__all__'


class ChainSerializer(serializers.ModelSerializer):

    class Meta:
        model = Chain
        fields = '__all__'


class StageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stage
        fields = '__all__'


class TaskStageFillerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStageFiller
        fields = '__all__'


class WebHookStageFillerSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebHookStageFiller
        fields = '__all__'


class ConditionalStageFillerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConditionalStageFiller
        fields = '__all__'


class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = '__all__'


class TaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task
        fields = '__all__'


class TaskWithSchemaSerializer(serializers.ModelSerializer):
    stage = StageSerializer(read_only=True)

    class Meta:
        model = Task
        fields = '__all__'