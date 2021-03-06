import json
from abc import ABCMeta

from django.core.exceptions import ObjectDoesNotExist
from jsonschema import validate
from rest_framework import serializers

from api.asyncstuff import process_updating_schema_answers
from api.models import Campaign, Chain, TaskStage, \
    ConditionalStage, Case, \
    Task, Rank, RankLimit, Track, RankRecord, CampaignManagement, Notification, NotificationStatus, ResponseFlattener, \
    TaskAward, DynamicJson
from api.permissions import ManagersOnlyAccessPolicy

base_model_fields = ['id', 'name', 'description']
stage_fields = ['chain', 'in_stages', 'out_stages', 'x_pos', 'y_pos']
schema_provider_fields = ['json_schema', 'ui_schema', 'library']


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = '__all__'


class CampaignValidationCheck:
    __metaclass__ = ABCMeta

    context = None

    def is_campaign_valid(self, value):
        request = self.context.get("request")
        if request and \
                hasattr(request, "user") and \
                ManagersOnlyAccessPolicy.is_user_campaign_manager(
                    request.user,
                    value.get_campaign()):
            return True
        else:
            return False


class ChainSerializer(serializers.ModelSerializer,
                      CampaignValidationCheck):
    class Meta:
        model = Chain
        fields = base_model_fields + ['campaign']

    def validate_campaign(self, value):
        """
        Check that the created chain belongs to a campaign that user manages.
        """
        if self.is_campaign_valid(value):
            return value
        raise serializers.ValidationError("User may not add chain "
                                          "to this campaign")


class ConditionalStageSerializer(serializers.ModelSerializer,
                                 CampaignValidationCheck):
    class Meta:
        model = ConditionalStage
        fields = base_model_fields + stage_fields + ['conditions', 'pingpong']

    def validate_chain(self, value):
        """
        Check that the created stage belongs to a campaign that user manages.
        """
        if self.is_campaign_valid(value):
            return value
        raise serializers.ValidationError("User may not add stage "
                                          "to this chain")


class TaskStageReadSerializer(serializers.ModelSerializer):
    chain = ChainSerializer(read_only=True)
    dynamic_jsons = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='dynamic_fields'
    )

    class Meta:
        model = TaskStage
        fields = base_model_fields + stage_fields + schema_provider_fields + \
                 ['copy_input', 'allow_multiple_files', 'is_creatable', 'external_metadata',
                  'displayed_prev_stages', 'assign_user_by', 'ranks',
                  'assign_user_from_stage', 'rich_text', 'webhook_address',
                  'webhook_payload_field', 'webhook_params', 'dynamic_jsons',
                  'webhook_response_field', 'allow_go_back', 'allow_release']


class TaskStageSerializer(serializers.ModelSerializer,
                          CampaignValidationCheck):
    class Meta:
        model = TaskStage
        fields = base_model_fields + stage_fields + schema_provider_fields + \
                 ['copy_input', 'allow_multiple_files', 'is_creatable', 'external_metadata',
                  'displayed_prev_stages', 'assign_user_by',
                  'assign_user_from_stage', 'rich_text', 'webhook_address',
                  'webhook_payload_field', 'webhook_params',
                  'webhook_response_field', 'allow_go_back', 'allow_release']

    def validate_chain(self, value):
        """
        Check that the created stage belongs
        to a campaign that user manages.
        """
        if self.is_campaign_valid(value):
            return value
        raise serializers.ValidationError("User may not add stage "
                                          "to this chain")


class TaskStagePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStage
        fields = ['id', 'name', 'description', 'json_schema', 'ui_schema', 'external_metadata',
                  'library', 'rich_text', 'created_at', 'updated_at']
        read_only_fields = ['id', 'name', 'description', 'json_schema', 'ui_schema',
                            'library', 'rich_text', 'created_at', 'updated_at']


class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = '__all__'


class TaskEditSerializer(serializers.ModelSerializer):

    def validate(self, attrs):
        if attrs.get('complete') == True:
            instance = self.root.instance
            stage = instance.stage
            try:
                old_responses = instance.responses
                if not old_responses:
                    old_responses = {}

                update_responses = attrs.get('responses')
                if not update_responses:
                    update_responses = {}

                old_responses.update(update_responses)

                schema = process_updating_schema_answers(stage, update_responses)

                validate(instance=old_responses, schema=schema)
                return attrs
            except Exception as exc:
                raise serializers.ValidationError({
                    "message": "Your answers are non-compliance with the standard",
                    "pass": list(exc.schema_path)
                })
        return attrs

    class Meta:
        model = Task
        fields = ['complete', 'responses']


class TaskDefaultSerializer(serializers.ModelSerializer):
    stage = TaskStageReadSerializer(read_only=True)

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['case',
                            'in_tasks',
                            'assignee',
                            'stage',
                            'responses',
                            'reopened',
                            'force_complete',
                            'complete']


class TaskAutoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'


class TaskPublicBasicSerializer(serializers.ModelSerializer):
    stage = TaskStagePublicSerializer(read_only=True)
    responses = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'responses', 'created_at', 'updated_at', 'stage']
        read_only_fields = ['id', 'responses', 'created_at',
                            'updated_at', 'stage']

    def get_responses(self, task):
        try:
            return task.stage.publisher.prepare_responses(task)
        except ObjectDoesNotExist:
            return task.responses


class TaskPublicSerializer(serializers.ModelSerializer):
    stage = TaskStagePublicSerializer(read_only=True)
    displayed_prev_tasks = serializers.SerializerMethodField()
    responses = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'responses', 'created_at', 'updated_at', 'stage', 'displayed_prev_tasks']
        read_only_fields = ['id', 'responses', 'created_at',
                            'updated_at', 'stage', 'displayed_prev_tasks']

    def get_displayed_prev_tasks(self, obj):
        tasks = obj.get_displayed_prev_tasks(public=True)
        serializer = TaskPublicBasicSerializer(tasks, many=True)
        return serializer.data

    def get_responses(self, task):
        try:
            return task.stage.publisher.prepare_responses(task)
        except ObjectDoesNotExist:
            return task.responses


class TaskCreateSerializer(serializers.ModelSerializer):
    assignee = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['case',
                            'in_tasks',
                            'assignee',
                            'reopened',
                            'force_complete']


class TaskRequestAssignmentSerializer(serializers.ModelSerializer):
    assignee = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['case',
                            'in_tasks',
                            'assignee',
                            'stage',
                            'responses',
                            'complete',
                            'reopened',
                            'force_complete']


class TaskSelectSerializer(serializers.ModelSerializer):
    displayed_prev_tasks = serializers.SerializerMethodField()
    stage = TaskStageReadSerializer(read_only=True)

    class Meta:
        model = Task
        fields = ['id',
                  'case',
                  'in_tasks',
                  'assignee',
                  'stage',
                  'responses',
                  'complete',
                  'displayed_prev_tasks']
        read_only_fields = ['id',
                            'case',
                            'in_tasks',
                            'assignee',
                            'stage',
                            'responses',
                            'complete']

    def get_displayed_prev_tasks(self, obj):
        tasks = obj.get_displayed_prev_tasks()
        serializer = TaskDefaultSerializer(tasks, many=True)
        return serializer.data


class RankSerializer(serializers.ModelSerializer, CampaignValidationCheck):
    class Meta:
        model = Rank
        fields = '__all__'

    def validate_track(self, value):
        """
        Check that the created rank belongs to a track that user manages.
        """
        if self.is_campaign_valid(value):
            return value
        raise serializers.ValidationError("User may not add rank "
                                          "to this track")


class RankRecordSerializer(serializers.ModelSerializer,
                           CampaignValidationCheck):
    class Meta:
        model = RankRecord
        fields = '__all__'

    def validate_rank(self, value):
        """
        Check that the created RankRecord belongs to a Rank that user manages.
        """
        if self.is_campaign_valid(value):
            return value
        raise serializers.ValidationError("User may not add RankRecord "
                                          "to this rank")


class RankLimitSerializer(serializers.ModelSerializer,
                          CampaignValidationCheck):
    class Meta:
        model = RankLimit
        fields = '__all__'

    def validate_stage(self, value):
        """
        Check that the created rank limit belongs
        to a stage that user manages.
        """
        if self.is_campaign_valid(value):
            return value
        raise serializers.ValidationError("User may not add rank limit "
                                          "to this campaign")


class TaskAwardSerializer(serializers.ModelSerializer):

    class Meta:
        model = TaskAward
        fields = '__all__'


class TrackSerializer(serializers.ModelSerializer,
                      CampaignValidationCheck):
    class Meta:
        model = Track
        fields = '__all__'

    def validate_campaign(self, value):
        """
        Check that the created track belongs
        to a campaign that user manages.
        """
        if self.is_campaign_valid(value):
            return value
        raise serializers.ValidationError("User may not add track "
                                          "to this campaign")


class CampaignManagementSerializer(serializers.ModelSerializer,
                                   CampaignValidationCheck):
    class Meta:
        model = CampaignManagement
        fields = '__all__'

    def validate_campaign(self, value):
        """
        Check that the created chain belongs
        to a campaign that user manages.
        """
        if self.is_campaign_valid(value):
            return value
        raise serializers.ValidationError(
            "User may not add campaign management to this campaign")


class NotificationSerializer(serializers.ModelSerializer,
                             CampaignValidationCheck):
    class Meta:
        model = Notification
        fields = '__all__'


class NotificationStatusSerializer(serializers.ModelSerializer,
                                   CampaignValidationCheck):
    class Meta:
        model = NotificationStatus
        fields = '__all__'


class ResponseFlattenerCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResponseFlattener
        fields = '__all__'


class ResponseFlattenerReadSerializer(serializers.ModelSerializer):
    task_stage = TaskStageReadSerializer(read_only=True)

    class Meta:
        model = ResponseFlattener
        fields = '__all__'


class DynamicJsonReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = DynamicJson
        fields = '__all__'
        editable = False
