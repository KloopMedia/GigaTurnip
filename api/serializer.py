from rest_framework import serializers
from rest_framework.fields import CurrentUserDefault
from api.models import Campaign, Chain, TaskStage, \
    WebHookStage, ConditionalStage, Case, \
    Task, Rank, RankLimit, Track, RankRecord


class CampaignSerializer(serializers.ModelSerializer):

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
                  'displayed_prev_stages', 'assign_user_by',
                  'assign_user_from_stage']


class WebHookStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebHookStage
        fields = base_model_fields + stage_fields + schema_provider_fields + \
                 ['web_hook_address', ]


class ConditionalStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConditionalStage
        fields = base_model_fields + stage_fields + ['conditions', 'pingpong']


class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = '__all__'


class TaskEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['complete', 'responses']


class TaskDefaultSerializer(serializers.ModelSerializer):
    stage = TaskStageSerializer(read_only=True)

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['case',
                            'in_tasks',
                            'assignee',
                            'stage',
                            'responses',
                            'complete']


class TaskCreateSerializer(serializers.ModelSerializer):
    assignee = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['case',
                            'in_tasks',
                            'assignee']


class TaskRequestAssignmentSerializer(serializers.ModelSerializer):
    assignee = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['case',
                            'in_tasks',
                            'assignee',
                            'stage',
                            'responses',
                            'complete']


class RankSerializer(serializers.ModelSerializer):

    class Meta:
        model = Rank
        fields = '__all__'


class RankRecordSerializer(serializers.ModelSerializer):

    class Meta:
        model = RankRecord
        fields = '__all__'


class RankLimitSerializer(serializers.ModelSerializer):

    class Meta:
        model = RankLimit
        fields = '__all__'


class TrackSerializer(serializers.ModelSerializer):

    class Meta:
        model = Track
        fields = '__all__'