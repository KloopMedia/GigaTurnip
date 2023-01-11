import json
from abc import ABCMeta, ABC

from django.core.exceptions import ObjectDoesNotExist
from jsonschema import validate
from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from api.api_exceptions import CustomApiException
from api.asyncstuff import process_updating_schema_answers
from api.constans import NotificationConstants, ConditionalStageConstants, JSONFilterConstants
from api.models import Campaign, Chain, TaskStage, \
    ConditionalStage, Case, \
    Task, Rank, RankLimit, Track, RankRecord, CampaignManagement, Notification, NotificationStatus, ResponseFlattener, \
    TaskAward, DynamicJson, TestWebhook
from api.permissions import ManagersOnlyAccessPolicy

base_model_fields = ['id', 'name', 'description']
stage_fields = ['chain', 'in_stages', 'out_stages', 'x_pos', 'y_pos']
schema_provider_fields = ['json_schema', 'ui_schema', 'card_json_schema', 'card_ui_schema', 'library']


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

    def is_valid(self, raise_exception=False):
        # if not self.initial_data.get('conditions'):
        #     raise CustomApiException(400, "You must pass conditions.")
        return super(ConditionalStageSerializer, self).is_valid(raise_exception=raise_exception)

    def validate_conditions(self, value):
        TYPES_TO_CONVERT = {
            'boolean': bool,
            'string': str,
            'number': float,
            'integer': int
        }
        AVAILABLE_CONDITIONS = ['==', '!=', '>', '<', '>=', '<=', 'ARRAY-CONTAINS', 'ARRAY-CONTAINS-NOT']
        VALIDATION_SCHEMA = {
            "type": "object",
            "properties": {
                "field": {"type": "string"},
                "value": {"type": "string"},
                "condition": {"type": "string", "enum": AVAILABLE_CONDITIONS},
                "type": {"type": "string", "enum": list(TYPES_TO_CONVERT.keys())},
                "system": {"type": "boolean", "default": False }
            },
            "required": ["field", "value", "condition", "type"]
        }
        for cond_id, condition in enumerate(value):
            try:
                current_schema = VALIDATION_SCHEMA


                if not condition.get('type'):
                    raise Exception('type is absent')
                elif condition.get('type') and condition['type'] not in list(TYPES_TO_CONVERT.keys()):
                    raise Exception('type is undefined')

                if not condition.get('value'):
                    raise Exception('value is absent')

                if condition['type'] == 'boolean':
                    val = condition['value'].lower()
                    condition['value'] = True if val in ['1', 'true'] else False
                else:
                    try:
                        condition['value'] = TYPES_TO_CONVERT[condition['type']](condition['value'])
                        current_schema['properties']['value']['type'] = condition['type']
                    except ValueError:
                        raise ValueError(
                            f'\'{condition["value"]}\' is not of type \'{condition["type"]}\''
                        )

                validate(instance=condition, schema=current_schema)
                return value
            except ValueError as exc:
                msg = f"Invalid data in {cond_id + 1} index. " + str(exc)
                raise CustomApiException(400, msg)
            except Exception as exc:
                if exc.args and exc.args[0] == 'type is absent':
                    msg = f"Invalid data in {cond_id + 1} index. Please, provide 'type' field"
                elif exc.args and exc.args[0] == 'type is undefined':
                    msg = f"Invalid data in {cond_id + 1} index. Please, provide valid type"
                elif exc.args and exc.args[0] == 'value is absent':
                    msg = f"Invalid data in {cond_id + 1} index. Please, provide 'value' field"
                else:
                    msg = f"Invalid data in {cond_id + 1} index. " + exc.message
                raise CustomApiException(400, msg)


class TaskStageReadSerializer(serializers.ModelSerializer):
    chain = ChainSerializer(read_only=True)
    dynamic_jsons_target = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='dynamic_fields'
    )
    dynamic_jsons_source = serializers.SlugRelatedField(
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
                  'webhook_payload_field', 'webhook_params', 'dynamic_jsons_source', 'dynamic_jsons_target',
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
                schema = process_updating_schema_answers(stage, instance.case.id, update_responses)

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


class PostJSONFilterSerializer(serializers.Serializer):
    items_conditions = serializers.ListField(child=serializers.JSONField()) # filters

    def _validate_filter_conditions(self, items):
        SCHEMA = JSONFilterConstants.JSON_Filter_Validation_Schema
        SCHEMA['items']['properties']['field']['enum'] = self.get_columns()
        validate(instance=items, schema=SCHEMA)
        for item in items:
            current_type = ConditionalStageConstants.SUPPORTED_TYPES.get(item['type'])
            for condition in item['conditions']:
                try:
                    current_type(condition['value'])
                except:
                    raise CustomApiException(400, f"Value '{condition['value']}' is not {item['type']}")
        return items

    def get_columns(self):
        raise NotImplementedError('Post JSON filter can not get fields to validate data')

    def get_object(self):
        raise NotImplementedError('Can not get serialized instance')

    def validate(self, data):
        self._validate_filter_conditions(data['items_conditions'])
        return data


class TaskResponsesFilterSerializer(PostJSONFilterSerializer):
    stage = serializers.IntegerField(min_value=1)  # из этого стейджа берутся поля
    search_stage = serializers.IntegerField(min_value=1)  # возвращаются таски с этого стейджа

    def validate_stage(self, value):
        return get_object_or_404(TaskStage.objects.filter(id=value), **{})

    def validate_search_stage(self, value):
        return get_object_or_404(TaskStage.objects.filter(id=value), **{})

    def validate(self, data):
        if data['stage'].chain.id != data['search_stage'].chain.id:
            raise serializers.ValidationError("Stages must be relate to the same chain.")
        super(TaskResponsesFilterSerializer, self).validate(data)
        return data

    def get_columns(self):
        columns = self.validate_stage(self.initial_data['stage']).make_columns_ordered()
        return [i.split('__', 1)[1] for i in columns]

    def get_object(self):
        item = self.validated_data
        return {
            "items_conditions": item.get('items_conditions', None),
            'stage': item.get('stage', None),
            'search_stage': item.get('search_stage', None)
        }

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


class TaskStageFullRankReadSerializer(TaskStageReadSerializer):
    ranks = RankSerializer(many=True)


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


class TestWebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestWebhook
        fields = '__all__'


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


class NotificationListSerializer(serializers.ModelSerializer, CampaignValidationCheck):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'text', 'created_at', 'importance']
        read_only_fields = NotificationConstants.READ_ONLY_FIELDS


class NotificationStatusListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'text', 'created_at', 'receiver_task',
                  'sender_task', 'receiver_task', 'importance']


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
