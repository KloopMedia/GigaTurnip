from rest_framework import serializers
from rest_framework.fields import CurrentUserDefault
from api.models import Campaign, Chain, TaskStage, \
    WebHookStage, ConditionalStage, Case, \
    Task


class CampaignSerializer(serializers.ModelSerializer):
    user = CurrentUserDefault()

    class Meta:
        model = Campaign
        fields = '__all__'


class ChainSerializer(serializers.ModelSerializer):

    class Meta:
        model = Chain
        fields = '__all__'


class TaskStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStage
        fields = '__all__'


class WebHookStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebHookStage
        fields = '__all__'


class ConditionalStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConditionalStage
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
    stage = TaskStageSerializer(read_only=True)

    class Meta:
        model = Task
        fields = '__all__'
