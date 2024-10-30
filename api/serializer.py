import json
from abc import ABCMeta, ABC
from datetime import datetime

from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from jsonschema import validate
from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from api.api_exceptions import CustomApiException
from api.asyncstuff import process_updating_schema_answers
from api.constans import (
    NotificationConstants, ConditionalStageConstants,
    JSONFilterConstants,
    TaskStageSchemaSourceConstants, ChainConstants, TaskStageConstants,
)
from api.models import Campaign, Chain, TaskStage, \
    ConditionalStage, Case, \
    Task, Rank, RankLimit, Track, RankRecord, CampaignManagement, Notification, \
    NotificationStatus, ResponseFlattener, \
    TaskAward, DynamicJson, TestWebhook, Category, Language, Country, \
    TranslateKey, CustomUser, Volume
from api.permissions import ManagersOnlyAccessPolicy


base_model_fields = ['id', 'name', 'description']
stage_fields = ['chain', 'in_stages', 'out_stages', 'x_pos', 'y_pos']
schema_provider_fields = ['json_schema', 'ui_schema', 'card_json_schema', 'card_ui_schema', 'library', 'filter_fields_schema']


class CampaignSerializer(serializers.ModelSerializer):
    managers = serializers.SerializerMethodField()
    notifications_count = serializers.SerializerMethodField()
    unread_notifications_count = serializers.SerializerMethodField()
    is_manager = serializers.SerializerMethodField()
    is_joined = serializers.SerializerMethodField()
    registration_stage = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = '__all__'

    def get_managers(self, obj):
        if self.context['request'].user.is_anonymous:
            return
        return obj.managers.values_list(flat=True)

    def get_notifications_count(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return 0
        return obj.notifications.filter(
            Q(rank__id__in=user.ranks.values('id'))
            | Q(target_user=user)).count()

    def get_unread_notifications_count(self, obj):
        user = self.context['request'].user

        if user.is_anonymous:
            return 0

        total_notifications_count = obj.notifications.filter(
            Q(rank__id__in=user.ranks.values('id')) | Q(target_user=user)
        ).count()

        read_notifications_count = obj.notifications.filter(
            notification_statuses__user=user
        ).count()

        unread_notifications_count = total_notifications_count - read_notifications_count

        return unread_notifications_count

    def get_is_manager(self, obj):
        user = self.context['request'].user
        managers = obj.get_campaign().managers.all()
        return user in managers

    def get_is_joined(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False

        user_has_rank_record = user.user_ranks.filter(
            rank_id=obj.default_track.default_rank
        ).exists()
        return user_has_rank_record

    def get_registration_stage(self, obj):
        return obj.default_track.registration_stage


class UserDeleteSerializer(serializers.Serializer):
    artifact = serializers.CharField()


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


class TaskStageChainInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    assign_type = serializers.CharField()
    in_stages = serializers.ListField(child=serializers.IntegerField())
    out_stages = serializers.ListField(child=serializers.IntegerField())
    completed = serializers.ListField(child=serializers.IntegerField())
    opened = serializers.ListField(child=serializers.IntegerField())
    reopened = serializers.ListField(child=serializers.IntegerField())
    total_count = serializers.IntegerField()
    complete_count = serializers.IntegerField()


class ChainIndividualsSerializer(serializers.ModelSerializer):
    stages_data = TaskStageChainInfoSerializer(source="data", many=True)

    class Meta:
        model = Chain
        fields = ["id", "name", "stages_data"]


    def find_order(self, node, visited, stack, nodes):
        visited[node["id"]] = True
        for neighbor in node["out_stages"]:
            if neighbor is None:
                continue
            if not visited[neighbor]:
                self.find_order(nodes[neighbor], visited, stack, nodes)

            stack.append(neighbor)

    def next_to_conditionals(self, stage_id, nodes):
        result = []
        for out_stage_id in nodes[stage_id]["out_stages"]:
            if out_stage_id is None:
                continue
            if nodes[out_stage_id].get("type", None) != "COND":
                result.append(out_stage_id)
                continue
            result.extend(self.next_to_conditionals(out_stage_id, nodes))
        return result

    def order_by_graph_flow(self, stages, conditionals):
        nodes = {i["id"]: i for i in stages}
        for node in conditionals:
            nodes[node["id"]] = node
            nodes[node["id"]]["type"] = "COND"

        for key, value in nodes.items():
            result_out_stages = []
            for idx, out_stage_id in enumerate(value["out_stages"]):
                if out_stage_id is None:
                    continue
                if nodes[out_stage_id].get("type", None) != "COND":
                    result_out_stages.append(out_stage_id)
                    continue

                result_out_stages.extend(
                    self.next_to_conditionals(out_stage_id, nodes))
            nodes[key]["out_stages"] = result_out_stages

        ts_nodes = {i["id"]: nodes[i["id"]] for i in stages}
        first_stage = [i for i in nodes.values() if i["in_stages"] == [None]]
        if not first_stage:
            return stages
        first_stage = first_stage[0]

        # Initialize visited dictionary to keep track of visited nodes during DFS
        visited = {node_id: False for node_id in ts_nodes.keys()}

        # Initialize the stack to store the sorted nodes
        stack = []

        self.find_order(first_stage, visited, stack, ts_nodes)

        stack.append(first_stage["id"])

        return [nodes[i] for i in stack[::-1]]

    def order_by_order(self, stages):
        return sorted(stages, key=lambda x: x["order"])

    def filter_stages(self, stages):
        result = []
        for st in stages:
            if st["skip_empty_individual_tasks"] and (not st["total_count"] and not st["complete_count"]):
                continue
            if st["assign_type"] == TaskStageConstants.AUTO_COMPLETE:
                continue
            result.append(st)
        return result

    def to_representation(self, instance):

        user = self.context["request"].user

        data = instance["data"]
        order_type = instance["order_in_individuals"]
        # if order_type == ChainConstants.CHRONOLOGICALLY:
        #     data = self.order_by_created_at(instance["data"])
        if order_type == ChainConstants.GRAPH_FLOW:
            data = self.order_by_graph_flow(instance["data"], instance["conditionals"])
        elif order_type == ChainConstants.ORDER:
            data = self.order_by_order(instance["data"])

        data = self.filter_stages(data)

        instance["data"] = data

        # stages = dict()
        # for i in data:
        #     if i["total_count"] == 0 and i["complete_count"] == 0:
        #         continue
        #
        #     stages[i["id"]] = {
        #         "completed": [],
        #         "reopened": [],
        #         "opened": [],
        #     }
        #
        # tasks = user.tasks.filter(stage__in=list(stages.keys())).values("id", "stage", "reopened", "complete")
        # for task in tasks:
        #     if task["reopened"]:
        #         stages[task["stage"]]["reopened"].append(task["id"])
        #
        #     if task["complete"]:
        #         stages[task["stage"]]["completed"].append(task["id"])
        #     else:
        #         stages[task["stage"]]["opened"].append(task["id"])
        #
        # for st in instance["data"]:
        #     if st["id"] in stages:
        #         st.update(stages[st["id"]])
        #     else:
        #         st.update({"completed": [],"reopened": [],"opened": [],})

        return super(ChainIndividualsSerializer, self).to_representation(instance)


class ConditionalStageSerializer(serializers.ModelSerializer,
                                 CampaignValidationCheck):
    queryset = ConditionalStage.objects.all() \
        .select_related("chain").prefetch_related("in_stages")
    in_stages = serializers.SerializerMethodField()
    out_stages = serializers.SerializerMethodField()


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

    def get_in_stages(self, obj):
        return obj.in_stages.values_list(flat=True)

    def get_out_stages(self, obj):
        return obj.out_stages.values_list(flat=True)


class RankLimitListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    open_limit = serializers.IntegerField()
    total_limit = serializers.IntegerField()


class TaskStageReadSerializer(serializers.ModelSerializer):
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
    campaign = serializers.SerializerMethodField()
    rank_limit = serializers.SerializerMethodField()
    quiz_answers = serializers.SerializerMethodField()

    class Meta:
        model = TaskStage
        fields = base_model_fields + stage_fields + schema_provider_fields + [
            "copy_input", "allow_multiple_files", "is_creatable", "external_metadata",
            "displayed_prev_stages", "assign_user_by", "ranks", "campaign", "stage_type",
            "assign_user_from_stage", "rich_text", "webhook_address", "rank_limit",
            "webhook_payload_field", "webhook_params", "dynamic_jsons_source", "dynamic_jsons_target",
            "webhook_response_field", "allow_go_back", "allow_release",
            "available_from", "available_to", "quiz_answers", "take_task_button_text", "external_renderer_url"
            ]

    def get_campaign(self, obj):
        return obj.get_campaign().id

    def to_representation(self, instance):
        request = self.context.get("request")
        if request:
            instance = TranslateKey.to_representation(instance, request)
        return super().to_representation(instance)

    def get_rank_limit(self, obj):
        if not hasattr(obj, "rank_limits"):
            return {}

        open_limits = sorted([i["open_limit"] for i in obj.rank_limits])
        total_limits = sorted([i["total_limit"] for i in obj.rank_limits])

        max_open = 0 if open_limits and open_limits[0] == 0 else open_limits[-1]
        max_total = 0 if total_limits and total_limits[0] == 0 else total_limits[-1]

        return {
            "open_limit": max_open,
            "total_limit": max_total,
        }

    def get_quiz_answers(self, obj):
        if not hasattr(obj, "quiz") or not obj.quiz.send_answers_with_questions:
            return {}
        return obj.quiz.correct_responses_task.responses

class TaskStageSerializer(serializers.ModelSerializer,
                          CampaignValidationCheck):
    class Meta:
        model = TaskStage
        fields = base_model_fields + stage_fields + schema_provider_fields + \
                 ["copy_input", "allow_multiple_files", "is_creatable", "external_metadata",
                  "displayed_prev_stages", "assign_user_by",
                  "available_from", "available_to",
                  "assign_user_from_stage", "rich_text", "webhook_address",
                  "webhook_payload_field", "webhook_params", "stage_type",
                  "webhook_response_field", "allow_go_back", "allow_release", "take_task_button_text", "external_renderer_url"]

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
        fields = [
            "id", "name", "description", "json_schema", "ui_schema", "external_metadata",
            "stage_type", "library", "rich_text", "created_at", "updated_at",
            "available_from", "available_to", "take_task_button_text", "external_renderer_url"
        ]
        read_only_fields = [
            "id", "name", "description", "json_schema", "ui_schema", "library",
            "rich_text", "created_at", "updated_at",
        ]


class CaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = '__all__'


class TaskPublicSerializer(serializers.ModelSerializer):
    stage = TaskStagePublicSerializer()

    class Meta:
        model = Task
        fields = [
            'id',
            'responses',
            'stage',
            'created_at'
        ]


class TaskStageCreateTaskSerializer(serializers.Serializer):
    responses = serializers.JSONField(required=False, default={})


class TaskListSerializer(serializers.ModelSerializer):
    stage = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id',
            'complete',
            'force_complete',
            'reopened',
            'responses',
            'stage',
            'created_at',
            'updated_at',
        ]

    def get_stage(self, obj):
        return obj['stage_data']


class TaskUserSelectableSerializer(serializers.ModelSerializer):
    stage = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id',
            'complete',
            'force_complete',
            'reopened',
            'responses',
            'stage',
            'created_at'
        ]

    def get_stage(self, obj):
        displayed_prev_tasks = TaskUserSelectableSerializer(obj.in_tasks.filter(stage__in=obj.stage.displayed_prev_stages.all()), many=True)
        result = {
            "id": obj.stage.id,
            "name": obj.stage.name,
            "chain": obj.stage.chain.id,
            "campaign": obj.stage.chain.campaign.id,
            "card_json_schema": obj.stage.card_json_schema,
            "card_ui_schema": obj.stage.card_ui_schema,
            "displayed_prev_stages": displayed_prev_tasks.data,
        }
        return result


class TaskEditSerializer(serializers.ModelSerializer):

    # def validate(self, attrs):
    #     if attrs.get('complete') == True:
    #         instance = self.root.instance
    #         stage = instance.stage
    #         try:
    #             old_responses = instance.responses
    #             if not old_responses:
    #                 old_responses = {}
    #
    #             update_responses = attrs.get('responses')
    #             if not update_responses:
    #                 update_responses = {}
    #
    #             old_responses.update(update_responses)
    #             schema = process_updating_schema_answers(stage, instance.case.id, update_responses)
    #
    #             validate(instance=old_responses, schema=schema)
    #             return attrs
    #         except Exception as exc:
    #             raise serializers.ValidationError({
    #                 "message": "Your answers are non-compliance with the standard",
    #                 "pass": list(exc.schema_path)
    #             })
    #     return attrs

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

    def to_representation(self, instance):
        """Replace stage schema with schema from task stage if so configured."""
        if instance.stage.schema_source == TaskStageSchemaSourceConstants.TASK:
            instance.stage.json_schema = instance.schema
            instance.stage.ui_schema = instance.ui_schema
        request = self.context.get("request", None)
        if request:
            instance.stage = TranslateKey.to_representation(instance.stage,
                                                            request)
        return super().to_representation(instance)


class TaskUserActivitySerializer(serializers.Serializer):
    stage = serializers.IntegerField()
    stage_name = serializers.CharField()
    chain = serializers.IntegerField()
    chain_name = serializers.CharField()
    ranks = serializers.ListField(child=serializers.IntegerField())
    in_stages = serializers.ListField(child=serializers.IntegerField())
    out_stages = serializers.ListField(child=serializers.IntegerField())
    complete_true = serializers.IntegerField()
    complete_false = serializers.IntegerField()
    force_complete_true = serializers.IntegerField()
    force_complete_false = serializers.IntegerField()
    count_tasks = serializers.IntegerField()


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
    stage = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id',
                  'stage',
                  'responses',
                  'complete',
                  'displayed_prev_tasks']
        read_only_fields = ['id',
                            'stage',
                            'responses',
                            'complete']

    def get_displayed_prev_tasks(self, obj):
        tasks = Task.objects.filter(case=obj['case'], stage__in=obj[
            'displayed_prev_stages']).exclude(
            id=obj['id'])
        tasks = tasks.prefetch_related(
            'stage__displayed_prev_stages').values('id',
                                                   'case',
                                                   'stage__name',
                                                   'stage__description',
                                                   'stage__json_schema',
                                                   'stage__ui_schema',
                                                   'responses',
                                                   'complete', ).annotate(
            displayed_prev_stages=ArrayAgg('stage__displayed_prev_stages',
                                           distinct=True)
        )

        serializer = TaskSelectSerializer(tasks, many=True)
        return serializer.data

    def get_stage(self, obj):
        return {
            "name": obj['stage__name'],
            "description": obj['stage__description'],
            "json_schema": obj['stage__json_schema'],
            "ui_schema":obj['stage__ui_schema']
        }


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


class RankGroupedByTrackSerializer(serializers.ModelSerializer):
    all_ranks = serializers.ListSerializer(child=serializers.JSONField())

    class Meta:
        model = Track
        fields = ["id", "name", "all_ranks"]


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


class NotificationListSerializer(serializers.ModelSerializer,
                                 CampaignValidationCheck):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'text', 'created_at',
                  'sender_task', 'receiver_task', 'importance']
        read_only_fields = NotificationConstants.READ_ONLY_FIELDS


class ResponseFlattenerCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResponseFlattener
        fields = '__all__'


class ResponseFlattenerReadSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResponseFlattener
        fields = '__all__'


class DynamicJsonReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = DynamicJson
        fields = '__all__'
        editable = False


class NumberRankSerializer(serializers.Serializer):
    campaign_id = serializers.IntegerField()
    campaign_name = serializers.CharField()
    ranks = serializers.JSONField()


class UserStatisticSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True, help_text="Campaign id.")
    name = serializers.CharField(read_only=True, help_text="Campaign title.")
    count = serializers.IntegerField(read_only=True, help_text="Count of users.")


class CategoryListSerializer(serializers.ModelSerializer):
    out_categories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "out_categories"]

    def get_out_categories(self, obj):
        return obj.out_categories.values_list("id", flat=True)


class LanguageListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Language
        fields = ["id", "name", "code"]


class CountryListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Country
        fields = ["id", "name"]


class FCMTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['fcm_token']


class VolumeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Volume
        fields = '__all__'
