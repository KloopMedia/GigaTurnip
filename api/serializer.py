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


base_model_fields = ['id', 'name', 'description']
stage_fields = ['chain', 'in_stages', 'out_stages', 'x_pos', 'y_pos']
schema_provider_fields = ['json_schema', 'ui_schema', 'library']


class TaskStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStage
        fields = base_model_fields + stage_fields + schema_provider_fields + \
                 ['copy_input', 'allow_multiple_files', 'is_creatable',
                  'count_complete', 'displayed_prev_stages']


class WebHookStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebHookStage
        fields = base_model_fields + stage_fields + schema_provider_fields + \
                 ['web_hook_address', ]


class ConditionalStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConditionalStage
        fields = base_model_fields + stage_fields + ['conditions', ]


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
