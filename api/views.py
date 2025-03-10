import csv
import json
from datetime import datetime
from datetime import timedelta

import requests
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import (
    Count, Q, Subquery, F, When, Value, TextField, OuterRef, Case as ExCase,Exists
)
from django.db.models.functions import JSONObject
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from api.models.stage.stage import Stage
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, mixins
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from api.asyncstuff import (
    process_completed_task, process_updating_schema_answers
)
from api.models import (
    Campaign, Chain, TaskStage, ConditionalStage, Case, Task, Rank,
    RankLimit, Track, RankRecord, CampaignManagement,
    Notification, ResponseFlattener, TaskAward,
    DynamicJson, CustomUser, TestWebhook, Webhook, UserDelete, Category,
    Country, Language, Volume
)
from api.permissions import (
    CampaignAccessPolicy, ChainAccessPolicy, TaskStageAccessPolicy,
    TaskAccessPolicy, RankAccessPolicy, RankRecordAccessPolicy,
    TrackAccessPolicy, RankLimitAccessPolicy, ConditionalStageAccessPolicy,
    CampaignManagementAccessPolicy, NotificationAccessPolicy,
    ResponseFlattenerAccessPolicy, TaskAwardAccessPolicy,
    DynamicJsonAccessPolicy, UserAccessPolicy, UserStatisticAccessPolicy,
    CategoryAccessPolicy, CountryAccessPolicy, LanguageAccessPolicy, UserFCMTokenAccessPolicy, VolumeAccessPolicy
)
from api.serializer import (
    CampaignSerializer, ChainSerializer, TaskStageSerializer,
    ConditionalStageSerializer, CaseSerializer, RankSerializer,
    RankLimitSerializer, TextbookChainSerializer, TrackSerializer, RankRecordSerializer,
    TaskEditSerializer, TaskDefaultSerializer, TaskRequestAssignmentSerializer,
    TestWebhookSerializer, TaskStageReadSerializer,
    CampaignManagementSerializer, NotificationListSerializer,
    NotificationSerializer, TaskAutoCreateSerializer,
    TaskStagePublicSerializer,
    ResponseFlattenerCreateSerializer, ResponseFlattenerReadSerializer,
    TaskAwardSerializer, DynamicJsonReadSerializer,
    TaskStageFullRankReadSerializer, TaskUserActivitySerializer,
    NumberRankSerializer, UserDeleteSerializer, TaskListSerializer,
    UserStatisticSerializer, CategoryListSerializer, CountryListSerializer,
    LanguageListSerializer, ChainIndividualsSerializer,
    RankGroupedByTrackSerializer, TaskPublicSerializer,
    TaskUserSelectableSerializer, TaskCreateSerializer,
    TaskStageCreateTaskSerializer, FCMTokenSerializer, VolumeSerializer
)
from api.utils import utils
from .api_exceptions import CustomApiException
from .constans import ErrorConstants, TaskStageConstants
from .filters import (
    ResponsesContainsFilter,
    CategoryInFilter, #IndividualChainCompleteFilter,
)
from api.utils.utils import paginate
from .utils.django_expressions import ArraySubquery


class CategoryViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = (CategoryAccessPolicy,)

    def get_queryset(self):
        return CategoryAccessPolicy.scope_queryset(
            self.request,
            Category.objects.all().prefetch_related("out_categories")
        )

    def get_serializer_class(self):
        return CategoryListSerializer

    @paginate
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        return qs


class CountryViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = (CountryAccessPolicy,)

    def get_queryset(self):
        return CountryAccessPolicy.scope_queryset(
            self.request,
            Country.objects.all()
        )

    def get_serializer_class(self):
        return CountryListSerializer

    @paginate
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        return qs


class LanguageViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = (LanguageAccessPolicy,)

    def get_queryset(self):
        return LanguageAccessPolicy.scope_queryset(
            self.request,
            Language.objects.all()
        )

    def get_serializer_class(self):
        return LanguageListSerializer

    @paginate
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        return qs


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = (UserAccessPolicy,)

    def get_queryset(self):
        return UserAccessPolicy.scope_queryset(
            self.request, CustomUser.objects.all()
        )

    def get_serializer_class(self):
        return UserDeleteSerializer

    @action(detail=False, methods=['get'])
    def delete_init(self, request, *args, **kwargs):
        """
        First step to delete user. Create User Delete
        object that will used in the delete_user endpoint.
        """
        del_obj = UserDelete.objects.create(user=request.user)
        [i.delete() for i in UserDelete.objects.filter(user=request.user)[1:]]
        return Response(
            {"delete_pk": del_obj.pk},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def delete_user(self, request, pk=None):
        """
        Param PK is UserDelete pk that returned by delete_init endpoint.
        User will be deleted if UserDelete obj created less than 5 minutes
        later.
        """
        now_minus_5 = datetime.now() - timedelta(minutes=5)
        obj = UserDelete.objects.filter(
            pk=pk, user=request.user,
            created_at__gt=now_minus_5
        )
        serializer = UserDeleteSerializer(data=request.data)
        if serializer.is_valid() and obj.count() > 0:
            if serializer.data['artifact'] in [request.user.email,
                                               request.user.username]:
                if request.user.rename():
                    return Response(
                        {"message": "Profile deleted successfully!"},
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {
                            "message": "Something went wrong"},
                        status=status.HTTP_409_CONFLICT
                    )
            return Response(
                {"message": "Email or phone number is incorrect."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {"message": "You haven't approve previous step yet."},
            status=status.HTTP_404_NOT_FOUND
        )


class CampaignViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing campaigns.
    create:
    Create a new campaign instance.
    delete:
    Delete campaign.
    read:
    Get campaign data.
    update:
    Update campaign data.
    partial_update:
    Partial update campaign data.
    list_user_campaigns:
    List campaigns where user has rank
    join_campaign:
    Request to join campaign on behalf of current user.
    """

    serializer_class = CampaignSerializer
    permission_classes = (CampaignAccessPolicy,)

    filterset_fields = {
        "languages__code": ["exact"],
        "categories": ["exact"],
        "countries__name": ["exact"],
        "featured": ["exact"],
    }
    filter_backends = (
        DjangoFilterBackend, CategoryInFilter,
    )

    def get_queryset(self):
        qs = CampaignAccessPolicy.scope_queryset(
            self.request, Campaign.objects.all()
        )
        user = self.request.user
        if user.is_authenticated:
            # Prefetch user ranks to avoid N+1 queries
            user_ranks = user.user_ranks.values_list('id', flat=True)
            qs = qs.annotate(is_joined=Exists(
                RankRecord.objects.filter(rank_id=OuterRef('default_track__default_rank'), user=user)
            )).annotate(is_completed=Exists(
                RankRecord.objects.filter(rank_id=OuterRef('course_completetion_rank'), user=user)
            ))
        else:
            qs = qs.annotate(is_joined=Value(False))
            qs = qs.annotate(is_completed=Value(False))
        qs = qs.annotate(registration_stage=Subquery(
                Track.objects.filter(id=OuterRef('default_track')).values('registration_stage')[:1]
        ))
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    @paginate
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(
            self.get_queryset()
        ).filter(visible=True)
        return qs

    @action(detail=True, methods=['post', 'get'])
    def join_campaign(self, request, pk=None):
        campaign = self.get_object()
        if not campaign.open:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        rank_record, created = campaign.join(request)
        rank_record_json = RankRecordSerializer(instance=rank_record).data
        if rank_record and created:
            return Response({"rank_record": rank_record_json}, status=status.HTTP_201_CREATED)
        elif rank_record and not created:
            return Response({"rank_record": rank_record_json})
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @paginate
    @action(detail=False)
    def list_user_campaigns(self, request):
        qs = self.filter_queryset(self.get_queryset())
        return utils.filter_for_user_campaigns(qs, request)

    @paginate
    @action(detail=False)
    def list_user_selectable(self, request):
        qs = self.filter_queryset(self.get_queryset())
        return utils.filter_for_user_selectable_campaigns(qs, request)


class ChainViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing chains.
    create:
    Create a new chain instance.
    delete:
    Delete chain.
    read:
    Get chain data.
    update:
    Update chain data.
    partial_update:
    Partial update chain data.
    """

    serializer_class = ChainSerializer
    permission_classes = (ChainAccessPolicy,)
    filterset_fields = {
        "id": ["exact"],
        "campaign": ["exact"],
        "is_individual": ["exact"],
        "stages__volumes": ["exact"]
    }
    filter_backends = [
        DjangoFilterBackend,
        #IndividualChainCompleteFilter,
    ]
    def get_queryset(self):
        return ChainAccessPolicy.scope_queryset(
            self.request, Chain.objects.all()
        )

    def get_serializer_class(self):
        if self.action == "individuals":
            return ChainIndividualsSerializer
        if self.action == "textbooks":
            return TextbookChainSerializer
        return ChainSerializer

    @action(detail=True)
    def get_graph(self, request, pk=None):
        stages = self.get_object().stages.all()
        graph = stages.values('pk', 'name').annotate(
            in_stages=ArrayAgg('in_stages', distinct=True),
            out_stages=ArrayAgg('out_stages', distinct=True)
        )
        return Response(graph)

    @paginate
    @action(detail=False, methods=["GET"])
    def individuals(self, request):
        qs = self.get_queryset()
        qs = self.filter_queryset(qs)
        qs = qs.filter(is_individual=True).select_related("campaign").prefetch_related("stages")
        user = request.user

        #Filter chains that have stages with rank limits matching user's ranks
        
        # print("chain queryset before filter:")
        # print(qs)

        # print("All stages from the main queryset before filter:")
        # print(qs.values("stages"))

        # user_ranks = user.ranks.all()

        # First get chains that have at least one stage with matching rank
        # chains_with_matching_ranks = qs.filter(
        #     stages__in=TaskStage.objects.filter(
        #         ranklimits__rank__in=user_ranks
        #     )
        # ).values("id")

        # qs = qs.filter(id__in=chains_with_matching_ranks)

        # print("chain queryset after filter:")
        # print(qs)


        rank_limits = RankLimit.objects.filter(rank__in=user.ranks.all())
        all_available_chains = rank_limits.values_list('stage__chain', flat=True).distinct()
        
        qs = qs.filter(id__in=all_available_chains).distinct()

        # filter by highest user ranks
        if request.query_params.get("by_highest_ranks"):
            ranks = request.user.get_highest_ranks_by_track()
            qs = qs.filter(
                id__in=RankLimit.objects.filter(rank__in=ranks).values(
                    "stage__chain")
            )

        
        # print("All stages from the main queryset after filter:")
        # print(qs.values("stages"))

        user_tasks = Task.objects.filter(
            assignee_id=user.id,
            stage__in=qs.values("stages")
        ).select_related("stage")

        # print("All tasks queryset with all fields:")
        # print(Task.objects.all().values("id", "assignee", "stage", "complete", "reopened"))

        # print("user_tasks queryset:")
        # print(user_tasks)

         # Get out_stage IDs in a separate, optimized subquery
        out_stages_subquery = Stage.objects.filter(
            in_stages=OuterRef('id')
        ).values_list('id', flat=True)

        # Get in_stage IDs in a separate, optimized subquery
        # in_stages_subquery = TaskStage.objects.filter(
        #     out_stages=OuterRef('id')
        # ).values_list('id', flat=True)

        task_stages_query = TaskStage.objects.select_related("tasks").filter(chain=OuterRef("id")) \
            .annotate(
                all_out_stages=ArraySubquery(out_stages_subquery),
                #all_in_stages=ArraySubquery(in_stages_subquery),
                #all_out_stages=ArrayAgg("out_stages__id", distinct=True),
                #all_in_stages=ArrayAgg("in_stages", distinct=True),
                completed=ArraySubquery(user_tasks.filter(stage_id=OuterRef("id"), complete=True).values_list("id", flat=True)),
                #not_completed=ArraySubquery(user_tasks.filter(stage_id=OuterRef("id"), complete=False).values_list("id", flat=True)),
                opened=ArraySubquery(user_tasks.filter(stage_id=OuterRef("id"), complete=False).values_list("id", flat=True)),
                reopened=ArraySubquery(user_tasks.filter(stage_id=OuterRef("id"), complete=False, reopened=True).values_list("id", flat=True)),
                #total_count=Count("tasks", filter=Q(tasks__case__in=user_tasks.values("case"))),
                #complete_count=Count("tasks", filter=Q(tasks__case__in=user_tasks.values("case"), tasks__complete=True))
            )
        

         # Check if we need to filter by completion status
        completed_param = request.query_params.get('completed', '').lower()
        if completed_param in ['true', 'false']:
            # Convert string parameter to boolean
            completed_filter = (completed_param == 'true')

            # This subquery finds stages that:
            # 1. Belong to the current chain (chain=OuterRef('id'))
            # 2. Are marked as required for chain completion (complete_individual_chain=True)
            # 3. Don't have a completed task from the current user
            incomplete_required_stages = TaskStage.objects.filter(
                chain=OuterRef('id'),  # Links to the main query's chain
                complete_individual_chain=True  # Only stages required for completion
            ).exclude(
                # Exclude stages where user has completed tasks
                id__in=user_tasks.filter(complete=True).values('stage_id')
            )

            if completed_filter:  # When completed=true
                # Return chains that have NO incomplete required stages
                # ~Q(Exists()) means "does not exist"
                # In other words: all required stages have completed tasks
                qs = qs.filter(~Q(Exists(incomplete_required_stages)))
            else:  # When completed=false
                # Return chains that have AT LEAST ONE incomplete required stage
                # Exists() means "there is at least one"
                # In other words: some required stages don't have completed tasks
                qs = qs.filter(Exists(incomplete_required_stages))

        qs = qs.values("id", "name", "order_in_individuals", "campaign", "new_task_view_mode").annotate(
            data=ArraySubquery(
                task_stages_query.values(
                    info=JSONObject(
                        id="id",
                        name="name",
                        order="order",
                        created_at="created_at",
                        skip_empty_individual_tasks="skip_empty_individual_tasks",
                        completed="completed",
                        #not_completed="not_completed",
                        opened="opened",
                        reopened="reopened",
                        assign_type="assign_user_by",
                        out_stages="all_out_stages",
                        #in_stages="all_in_stages",
                        #total_count="total_count",
                        #complete_count="complete_count"
                    )
                )
            ),
            conditionals=ArraySubquery(
                ConditionalStage.objects.filter(chain=OuterRef("id")).annotate(
                    all_out_stages=ArrayAgg("out_stages", distinct=True),
                    all_in_stages=ArrayAgg("in_stages", distinct=True),
                ).values(
                    info=JSONObject(
                        id="id",
                        name="name",
                        order="order",
                        created_at="created_at",
                        out_stages="all_out_stages",
                        in_stages="all_in_stages",
                    )
                )
            )
        )
        return qs
    
    @paginate
    @action(detail=False, methods=["GET"])
    def textbooks(self, request):
        """Get all textbook chains (accessible to any logged-in user)"""
        qs = self.get_queryset()
        qs = self.filter_queryset(qs)
        qs = qs.filter(is_text_book=True).select_related("campaign").prefetch_related("stages")
        
        # Get stages data without task-related information, only including stages with rich_text
        task_stages_query = TaskStage.objects.filter(
            chain=OuterRef("id"),
            rich_text__isnull=False  # Exclude null rich_text
        ).exclude(
            rich_text=""  # Exclude empty rich_text
        ).annotate(
            all_out_stages=ArraySubquery(
                Stage.objects.filter(
                    in_stages=OuterRef('id')
                ).values_list('id', flat=True)
            )
        )

        qs = qs.values("id", "name", "order_in_individuals", "campaign").annotate(
            data=ArraySubquery(
                task_stages_query.values(
                    info=JSONObject(
                        id="id",
                        name="name",
                        order="order",
                        created_at="created_at",
                        out_stages="all_out_stages",
                        rich_text="rich_text"  # Include rich_text in response
                    )
                )
            )
        )
        return qs



class TaskStageViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing task stages.
    create:
    Create a new task stage instance.
    delete:
    Delete task stage.
    read:
    Get task stage data.
    update:
    Update task stage data.
    partial_update:
    Partial update task stage data.
    user_relevant:
    Return a list of task stages that are relevant to "request" user.
    """

    permission_classes = (TaskStageAccessPolicy,)
    filterset_fields = {
        'stage_type': ['exact'],
        'chain': ['exact'],
        'chain__campaign': ['exact'],
        'is_creatable': ['exact'],
        'ranks': ['exact'],
        'ranks__users': ['exact'],
        'ranklimits__is_creation_open': ['exact'],
        'ranklimits__total_limit': ['exact', 'lt', 'gt'],
        'ranklimits__open_limit': ['exact', 'lt', 'gt'],
        'volumes': ['exact']
    }

    def get_serializer_class(self):
        """
        get_serializer_class:
        Выбирает нужные сериалайзер (для чтения или обычный).
        """

        if self.action in ["create", "update", "partial_update"]:
            return TaskStageSerializer
        elif self.action == "public":
            return TaskStagePublicSerializer
        elif self.action == "create_task":
            return TaskStageCreateTaskSerializer
        else:
            if self.request and self.request.query_params.get("ranks_avatars"):
                return TaskStageFullRankReadSerializer
            return TaskStageReadSerializer

    def get_queryset(self):
        if self.action == 'list':
            return TaskStageAccessPolicy.scope_queryset(
                self.request, TaskStage.objects.all()
                .select_related(
                    "chain",
                    "assign_user_from_stage",
                ).prefetch_related(
                    "displayed_prev_stages",
                    "displayed_following_stages",
                    "dynamic_jsons_source",
                    "dynamic_jsons_target",
                    "in_stages",
                    "out_stages",
                    "ranks"
                )
            )
        else:
            return TaskStage.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    @paginate
    @action(detail=False)
    def user_relevant(self, request):
        # return stages where user can create new task
        q = self.get_queryset()
        q = q.exclude(chain__is_individual=True)

        stages = self.filter_queryset(q)

        # filter by highest user ranks
        ranks = request.user.ranks.all()
        if request.query_params.get("by_highest_ranks"):
            ranks = request.user.get_highest_ranks_by_track()
        ranks = ranks.prefetch_related("ranklimits").filter(
            ranklimits__is_creation_open=True
        )

        stages = utils.filter_for_user_creatable_stages(stages, request, ranks)

        stages = stages.annotate(
            rank_limits=ArraySubquery(
                RankLimit.objects.filter(
                    rank__in=ranks,
                    stage=OuterRef("id"),
                ).values(
                    data=JSONObject(
                        id="rank",
                        name="rank__name",
                        open_limit="open_limit",
                        total_limit="total_limit",
                    )
                )
            )
        )

        return stages

    @paginate
    @action(detail=False)
    def public(self, request):
        stages = self.filter_queryset(self.get_queryset())
        stages = stages.filter(
            Q(is_public=True) | Q(publisher__is_public=True))
        return stages

    @action(detail=True, methods=['post', 'get'])
    def create_task(self, request, pk=None):
        case = Case.objects.create()
        stage = self.get_object()
        responses = dict()
        if request.method == 'POST':
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            responses = serializer.data["responses"]

            #Check fast_track
            if request.data.get('fast_track', False):
                if not RankRecord.objects.filter(rank=stage.fast_track_rank).filter(user=request.user).exists():
                    RankRecord.objects.create(rank=stage.fast_track_rank, user=request.user)


        task = Task(stage=stage, assignee=request.user, case=case, responses=responses)
        for copy_field in stage.copy_fields.all():
            task.responses.update(copy_field.copy_response(task))
        webhook = stage.get_webhook()
        if webhook and webhook.is_triggered:
            webhook.trigger(task)
        task.save()
        serializer = TaskDefaultSerializer(task)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def schema_fields(self, request, pk=None):
        stage = self.get_object()
        fields = [i.split('__', 1)[1] for i in stage.make_columns_ordered()]
        return Response({'fields': fields})

    @action(detail=True, methods=['get'])
    def load_schema_answers(self, request, pk=None):
        """
        We must pass responses for the schema to get primary key and update sub field's answers
        Otherwise we would return response with 400 status code

        :param GET: responses (responses for the task of stage)
        :param pk: stage id (to update schema)
        :return:
        """

        kwargs = dict()
        task_stage = self.get_object()
        kwargs['task_stage'] = task_stage

        responses = request.query_params.get('responses')
        if responses:
            kwargs['responses'] = json.loads(responses)

        task_id = request.query_params.get('current_task')
        if task_id and task_id.isdigit():
            try:
                task = Task.objects.get(id=task_id)
                kwargs['case'] = task.case.id if task.case else None
            except Task.DoesNotExist:
                raise CustomApiException(status.HTTP_400_BAD_REQUEST,
                                         ErrorConstants.ENTITY_DOESNT_EXIST % (
                                         'Task', task_id))

        if task_stage.json_schema:
            schema = process_updating_schema_answers(**kwargs)
            return Response({'status': status.HTTP_200_OK,
                             'schema': schema})
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @paginate
    @action(detail=False, methods=["GET"])
    def selectable(self, request):
        tasks = Task.objects.all().select_related('stage')
        tasks = TaskAccessPolicy.scope_queryset(request, tasks)
        tasks_selectable = utils.filter_for_user_selectable_tasks(tasks,
                                                                  request.user)
        qs = self.filter_queryset(self.get_queryset())
        qs = qs.filter(id__in=tasks_selectable.values("stage").distinct())

        return qs

    @paginate
    @action(detail=False, methods=["GET"])
    def available_stages(self, request, *args, **kwargs):
        """
        Return all available stages that user  can pass in the future.
        """
        qs = self.filter_queryset(self.get_queryset())

        stages_by_ranks = RankLimit.objects.filter(
            rank__in=request.user.ranks.values("id")
        ).values_list('stage', flat=True)

        qs = qs.filter(id__in=stages_by_ranks)

        # used = set()
        # to_parse = set(qs)
        #
        # while to_parse:
        #     current = to_parse.pop()
        #
        #     new = current.assign_user_to_stages.exclude(id__in=used)
        #     qs |= new
        #
        #     used.add(current.id)
        #     to_parse.update(new.exclude(id__in=used))

        return qs#.distinct()

class ConditionalStageViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing conditional stages.
    create:
    Create a new chain conditional stage.
    delete:
    Delete conditional stage.
    read:
    Get conditional stage data.
    update:
    Update conditional stage data.
    partial_update:
    Partial update conditional stage data.
    """
    filterset_fields = ['chain', ]
    serializer_class = ConditionalStageSerializer
    permission_classes = (ConditionalStageAccessPolicy,)

    def get_queryset(self):
        return ConditionalStageAccessPolicy.scope_queryset(
            self.request, ConditionalStage.objects.all()
        )


class CaseViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing cases.
    create:
    Create a new case instance.
    delete:
    Delete case.
    read:
    Get case data.
    update:
    Update case data.
    partial_update:
    Partial update case data.
    """
    queryset = Case.objects.all()
    serializer_class = CaseSerializer

    filterset_fields = {
        'tasks__stage__chain': ['exact'],
        'created_at': ['lte', 'gte', 'lt', 'gt'],
        'updated_at': ['lte', 'gte', 'lt', 'gt']
    }

    @action(detail=True)
    def info_by_case(self, request, pk=None):  # todo: through serializer
        tasks = self.get_object().tasks.all()
        filters_tasks_info = {
            "complete": ArrayAgg('complete'),
            "force_complete": ArrayAgg('force_complete'),
            "id": ArrayAgg('pk'),
        }
        task_info_by_stage = tasks.values('stage', 'stage__name').annotate(
            **filters_tasks_info
        )
        return Response({
            "status": status.HTTP_200_OK,
            "info": list(task_info_by_stage)
        })


# class ResponsesContainFilter(filters.SearchFilter):
#
#     search_param = "responses_contain"
#     search_title = _('Task Responses Filter')
#
#     def to_html(self, request, queryset, view):
#         return ""
#
#     def get_search_terms(self, request):
#         """
#         Search term is set by a ?search=... query parameter.
#         """
#         params = request.query_params.get(self.search_param, '')
#         if not params:
#             return None
#         params = params.split(': ')
#         if len(params) != 2:
#             return None
#         return params
#
#     def filter_queryset(self, request, queryset, view):
#
#         search_fields = self.get_search_fields(view, request)
#         search_term = self.get_search_terms(request)
#
#         if not search_fields or not search_term:
#             return queryset
#
#         tasks = Task.objects.filter(stage__id=search_term[0])
#         tasks = tasks.filter(responses__icontains=search_term[1])
#         cases = Case.objects.filter(tasks__in=tasks).distinct()
#         response = queryset.filter(case__in=cases)
#         return response


class TaskViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing tasks.

    create:
    Create a new task instance. Note: if task is completed,
    process_completed_task() function will be called.

    delete:
    Delete task.

    read:
    Get task data.

    update:
    Update task data. Note: if task is completed,
    process_completed_task() function will be called.

    partial_update:
    Partial update task data.

    user_relevant:
    Return a list of tasks where user is task assignee.

    user_selectable:
    Return a list of not assigned
    uncompleted tasks that are allowed to the user.

    request_assignment:
    Assign user to requested task.

    release_assignment:
    Release user from requested task.

    user_activity_csv:
    Return list of activities on stages. Allow to download csv file.

    csv:
    Return csv file with tasks information. Note: params stage and response_flattener are important.

    get_integrated_tasks:
    Return integrated tasks of requested task.

    """

    filterset_fields = {
        'case': ['exact'],
        'reopened': ['exact'],
        'stage': ['exact'],
        'stage__chain__campaign': ['exact'],
        'stage__chain': ['exact'],
        'stage__chain__is_individual': ['exact'],
        'stage__chain__name': ['exact'],
        'stage__volumes': ['exact'],
        'assignee': ['exact'],
        'assignee__ranks': ['exact'],
        'complete': ['exact'],
        'created_at': ['lte', 'gte', 'lt', 'gt'],
        'updated_at': ['lte', 'gte', 'lt', 'gt']
    }
    search_fields = ('responses',)
    filter_backends = [
        DjangoFilterBackend,
        ResponsesContainsFilter,
        OrderingFilter,
    ]
    ordering_fields = ["created_at", "updated_at"]
    permission_classes = (TaskAccessPolicy,)

    def get_queryset(self):
        qs = Task.objects.all().select_related('stage')
        if self.action in ["list", "csv", "user_activity",
                           "user_activity_csv", "search_by_responses",
                           "user_selectable"]:
            return TaskAccessPolicy.scope_queryset(
                self.request, qs
            )
        else:
            return qs

    def get_serializer_class(self):
        if self.action in ['list', 'user_relevant']:
            return TaskListSerializer
        elif self.action == "user_selectable":
            return TaskUserSelectableSerializer
        elif self.action == 'create':
            return TaskAutoCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TaskEditSerializer
        elif self.action == 'request_assignment':
            return TaskRequestAssignmentSerializer
        elif self.action == 'user_activity':
            return TaskUserActivitySerializer
        else:
            return TaskDefaultSerializer

    @paginate
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        qs = qs.annotate(
            stage_data=JSONObject(
                id='stage__id',
                name="stage__name",
                chain="stage__chain",
                campaign="stage__chain__campaign",
                card_json_schema="stage__card_json_schema",
                card_ui_schema="stage__card_ui_schema",
                test="stage__test",
            )
        ).values('id',
                 'complete',
                 'force_complete',
                 'created_at',
                 'reopened',
                 'responses',
                 'stage_data'
                 )

        return qs

    def create(self, request, *args, **kwargs):
        """
        post:
        Create a new task instance. Note: if task is completed,
        process_completed_task() function will be called.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            case = Case.objects.create()
            task = serializer.save(case=case)
            if task.complete:
                process_completed_task(task)
            # if data['complete']:
            #     result(async_task(process_completed_task,
            #                       data['id'],
            #                       task_name='process_completed_task',
            #                       group='follow_chain'))
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """
        Post:
        Update task data. Note: if task is completed,
        process_completed_task() function will be called.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance,
                                         data=request.data,
                                         partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        data['id'] = instance.id
        next_direct_task = None
        complete = serializer.validated_data.get("complete", False)
        if (complete and not instance.stage.chain.is_individual) \
                and not utils.can_complete(instance, request.user):
            err_message = {
                "detail": f"{ErrorConstants.CANNOT_SUBMIT} {ErrorConstants.TASK_COMPLETED}",
                "id": instance.id
            }
            raise CustomApiException(status.HTTP_403_FORBIDDEN,
                                     err_message)
        try:
            task = instance.set_complete(
                responses=serializer.validated_data.get("responses", {}),
                complete=complete
            )
            if complete:
                next_direct_task = process_completed_task(task)
        except Task.CompletionInProgress:
            err_message = {
                "detail": {
                    "message": f"{ErrorConstants.CANNOT_SUBMIT} {ErrorConstants.TASK_COMPLETED}",
                    "id": instance.id
                }
            }
            raise CustomApiException(status.HTTP_403_FORBIDDEN,
                                     err_message)
        except Task.AlreadyCompleted:
            err_message = {
                "detail": {
                    "message": ErrorConstants.TASK_ALREADY_COMPLETED,
                    "id": instance.id}
            }
            raise CustomApiException(status.HTTP_403_FORBIDDEN,
                                     err_message)
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset,
            # we need to forcibly invalidate the prefetch
            # cache on the instance.
            instance._prefetched_objects_cache = {}
        response = {
            "id": instance.id,
            "message": "Task saved."
        }
        if next_direct_task:
            response["is_new_campaign"] = instance.get_campaign().id != next_direct_task.get_campaign().id
            response["message"] = "Next direct task is available."
            response["next_direct_id"] = next_direct_task.id

        if instance.stage.auto_notification_recipient_stages.all():
            response["notifications"] = list(
                instance.receiver_notifications.values("title", "text")
            )

        return Response(response, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        """
        Post:
        Partial update task data.
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @paginate
    @action(detail=False)
    def user_relevant(self, request):
        """
        Get:
        Return a list of tasks where user is task assignee.
        """
        qs = self.filter_queryset(self.get_queryset())
        qs = qs.filter(assignee=request.user) \
            .exclude(
            stage__assign_user_by=TaskStageConstants.INTEGRATOR,
        ).exclude(stage__chain__is_individual=True)

        tasks = qs.annotate(
            stage_data=JSONObject(
                id='stage__id',
                name="stage__name",
                chain="stage__chain",
                campaign="stage__chain__campaign",
                card_json_schema="stage__card_json_schema",
                card_ui_schema="stage__card_ui_schema",
            )
        ).values('id',
                 'complete',
                 'force_complete',
                 'created_at',
                 'updated_at',
                 'reopened',
                 'responses',
                 'stage_data'
                 )

        return tasks

    @paginate
    @action(detail=False, methods=["GET", "POST"])
    def user_selectable(self, request):
        """
        Get:
        Return a list of not assigned
        uncompleted tasks that are allowed to the user.
        """
        queryset = self.filter_queryset(
            self.get_queryset()
            .select_related('stage')
            .prefetch_related('stage__ranks__users',
                              'out_tasks',
                              'stage__displayed_prev_stages',
                              'stage__ranklimits')
        )
        """
        stage id
        key
        value
        condition
        """

        tasks = queryset
        while request.method == "POST":
            stage = queryset.first().stage if queryset else None
            if not stage or stage and not stage.filter_fields_schema:
                break
            all_tasks = Task.objects.filter(
                case__in=queryset.values("case"),
            ).select_related("case")

            filters = utils.get_task_responses_filters(stage.filter_fields_schema, request.data)

            if not filters:
                break

            cases = Case.objects.none()
            for i, f in enumerate(filters):
                cases = all_tasks.filter(f).values("case")
                all_tasks = Task.objects.filter(case__in=cases)

            tasks = tasks.filter(case__in=cases)
            break

        tasks_selectable = utils.filter_for_user_selectable_tasks(tasks, request.user)
        by_datetime = utils.filter_for_datetime(tasks_selectable)

        return by_datetime

    @paginate
    @action(detail=False)
    def user_activity(self, request):
        tasks = self.filter_queryset(self.get_queryset()) \
            .select_related('stage', ) \
            .prefetch_related('stage__ranks', 'stage__in_stages',
                              'stage__out_stages')
        groups = tasks.values('stage').annotate(
            stage_name=F('stage__name'),
            chain=F('stage__chain'),
            chain_name=F('stage__chain__name'),
            ranks=ArrayAgg('stage__ranks', distinct=True),
            in_stages=ArrayAgg('stage__in_stages', distinct=True),
            out_stages=ArrayAgg('stage__out_stages', distinct=True),
            **utils.task_stage_queries()
        )

        return groups

    @action(detail=False)
    def user_activity_csv(self, request):
        """
        Get:
        Return list of activities on stages. Note: if you want download csv file you have to set 'csv' in params as true

        Also for custom statistics you can use filters. And on top of all that you can use filters in csv using 'task_responses' key in params.
        Params for example:
        ?csv=true&task_responses={"a":"b"}
        """
        tasks = self.filter_queryset(self.get_queryset()) \
            .select_related('stage', 'assignee')
        groups = tasks.values('stage', 'stage__name', 'assignee').annotate(
            chain_id=F('stage__chain'),
            chain=F('stage__chain__name'),
            email=F("assignee__email"),
            rank_ids=ArrayAgg('assignee__ranks__id', distinct=True),
            rank_names=ArrayAgg('assignee__ranks__name', distinct=True),
            **utils.task_stage_queries()
        ).order_by("count_tasks")

        filename = "results"  # utils.request_to_name(request)
        response = HttpResponse(
            content_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}.csv"'
            },
        )

        if request.query_params.get("csv", None):
            fieldnames = ["stage", "stage__name", "chain_id", "chain",
                          "case", "assignee", "email", "rank_ids",
                          "rank_names",
                          "complete_true", "complete_false",
                          "force_complete_false",
                          "force_complete_true", "count_tasks", ]

            writer = csv.DictWriter(response, fieldnames=fieldnames)
            writer.writeheader()
            for group in groups:
                writer.writerow(group)
            return response

        return Response(groups)

    @paginate
    @action(detail=True)
    def get_integrated_tasks(self, request, pk=None):
        """
        Get:
        Return integrated tasks
        """
        tasks = self.filter_queryset(self.get_queryset())
        tasks = tasks.filter(out_tasks=self.get_object())
        return tasks

    @action(detail=True, methods=['post', 'get'])
    def request_assignment(self, request, pk=None):
        """
        Get:
        Request task assignment to user
        """
        task = self.get_object()
        serializer = self.get_serializer(task, request.data)
        if serializer.is_valid():
            serializer.save()
            if task.integrator_group is not None:
                in_tasks = Task.objects.filter(out_tasks=task) \
                    .filter(stage__assign_user_by="IN")
                if in_tasks:
                    in_tasks.update(assignee=request.user)
            return Response({'status': 'assignment granted', 'id': task.id})
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'get'])
    def release_assignment(self, request, pk=None):
        """
        Get:
        Request task release assignment
        """
        task = self.get_object()
        if task.stage.allow_release and not task.complete:
            task.assignee = None
            task.save()
            if task.integrator_group is not None:
                in_tasks = Task.objects.filter(out_tasks=task) \
                    .filter(stage__assign_user_by="IN")
                if in_tasks:
                    in_tasks.update(assignee=None)
            return Response({'status': 'assignment released'})
        raise CustomApiException(status.HTTP_403_FORBIDDEN,
                                 ErrorConstants.IMPOSSIBLE_ACTION % 'release this')

    @action(detail=True, methods=['post', 'get'])
    def uncomplete(self, request, pk=None):
        task = self.get_object()
        try:
            task.set_not_complete()
            return Response(
                {'status': 'Assignment uncompleted', 'id': task.id})
        except Task.ImpossibleToUncomplete:
            raise CustomApiException(status.HTTP_403_FORBIDDEN,
                                     ErrorConstants.IMPOSSIBLE_ACTION % 'uncomplete this')

    @action(detail=True, methods=['post', 'get'])
    def open_previous(self, request, pk=None):
        task = self.get_object()
        try:
            (prev_task, task) = task.open_previous()
            return Response(
                {'status': 'Previous task opened.', 'id': prev_task.id})
        except Task.ImpossibleToOpenPrevious:
            return CustomApiException(status.HTTP_403_FORBIDDEN,
                                      ErrorConstants.IMPOSSIBLE_ACTION % 'open previous')

    # @action(detail=True, methods=['post', 'get'])
    # def open_next(self, request, pk=None):
    #     task = self.get_object()
    #     try:
    #         next_task = task.open_next()
    #         return Response({'status': 'Next task opened.', 'id': next_task.id})
    #     except Task.ImpossibleToOpenNext:
    #         return Response(
    #             {'message': 'It is impossible to open next task.'},
    #             status=status.HTTP_403_FORBIDDEN
    #         )

    @paginate
    @action(detail=True, methods=['get'])
    def list_displayed_previous(self, request, pk=None):
        tasks = self.get_object().get_displayed_prev_tasks()
        return tasks

    @action(detail=True, methods=['get'])
    def trigger_webhook(self, request, pk=None):
        task = self.get_object()
        webhook = task.stage.get_webhook()
        if webhook:
            is_altered, altered_task, response, error_description = webhook.trigger(
                task)
            if is_altered:
                return Response({"status": "Responses overwritten",
                                 "responses": altered_task.responses})
            else:
                err_msg = {"detail": {
                    "message": error_description,
                    "status": response.status_code
                }}
                raise CustomApiException(status.HTTP_400_BAD_REQUEST, err_msg)
        # django_response = HttpResponse(
        #     content=response.content,
        #     status=response.status_code,
        #     content_type=response.headers['Content-Type']
        # )
        return

    @action(detail=False, methods=['get'])
    def statistics(self):
        q = self.filter_queryset(self.get_queryset()).select_related(
            'stage'
        )
        q = q.values('stage', 'stage__name', 'complete',
                     'force_complete').annotate().order_by('stage')
        return q


#         tasks = self.get_object().tasks.all()
#         filters_tasks_info = {
#             "complete": ArrayAgg('complete'),
#             "force_complete": ArrayAgg('force_complete'),
#             "id": ArrayAgg('pk'),
#         }
#         task_info_by_stage = tasks.values('stage', 'stage__name').annotate(
#             **filters_tasks_info
#         )
#         return Response({
#             "status": status.HTTP_200_OK,
#             "info": list(task_info_by_stage)
#         })

class RankViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing ranks.
    create:
    Create a new rank instance.
    delete:
    Delete rank.
    read:
    Get rank data.
    update:
    Update rank data.
    partial_update:
    Partial update rank data.
    """

    permission_classes = (RankAccessPolicy,)

    def get_serializer_class(self):
        if self.action == "grouped_by_track":
            return RankGroupedByTrackSerializer
        return RankSerializer

    def get_queryset(self):
        return RankAccessPolicy.scope_queryset(
            self.request, Rank.objects.all()
        )

    @paginate
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        qs = qs.select_related('track').prefetch_related(
            'prerequisite_ranks', 'stages'
        )

        return qs

    @paginate
    @action(detail=False, methods=["GET"])
    def grouped_by_track(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        grouped = Track.objects.filter(id__in=qs.values("track").distinct()) \
            .annotate(
            all_ranks=ArraySubquery(
                qs.filter(track_id=OuterRef("id")).values(
                    data=JSONObject(id="id", name="name")
                )
            )
        )

        return grouped


class RankRecordViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing rank records.
    create:
    Create a new rank record instance.
    delete:
    Delete rank record.
    read:
    Get rank record data.
    update:
    Update rank record data.
    partial_update:
    Partial update rank record data.
    """
    serializer_class = RankRecordSerializer
    permission_classes = (RankRecordAccessPolicy,)

    def get_queryset(self):
        return RankRecordAccessPolicy.scope_queryset(
            self.request, RankRecord.objects.all()
        )


class RankLimitViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing rank limits.
    create:
    Create a new rank limit instance.
    delete:
    Delete rank limit.
    read:
    Get rank limit data.
    update:
    Update rank limit data.
    partial_update:
    Partial update rank limit data.
    """

    filterset_fields = ['rank', ]
    serializer_class = RankLimitSerializer

    permission_classes = (RankLimitAccessPolicy,)

    def get_queryset(self):
        return RankLimitAccessPolicy.scope_queryset(
            self.request, RankLimit.objects.all()
        )


class NumberRankViewSet(viewsets.ModelViewSet):
    # serializer_class = NumberRanksSerializer # todo: Add serializer to paginate list

    def get_serializer_class(self):
        return NumberRankSerializer

    def get_queryset(self):
        return RankAccessPolicy.scope_queryset(
            self.request, Rank.objects.all()
        )

    def list(self, request, *args, **kwargs):
        q = self.filter_queryset(self.get_queryset()) \
            .prefetch_related('track') \
            .select_related('users')

        main_keys = {
            'campaign_id': F('track__campaign__id'),
            'campaign_name': F('track__campaign__name')
        }
        q = q.values(**main_keys) \
            .annotate(
            ranks=ArrayAgg(Subquery(
                q.filter(
                    id=OuterRef('id')
                ).annotate(
                    count=Count('users'),
                    rank_id=F('id'),
                    rank_name=F('name'),
                    condition=ExCase(
                        When(Q(prerequisite_ranks__isnull=False),
                             then=Value('prerequisite_ranks')),
                        When(Q(taskaward__isnull=False),
                             then=Value('task_awards')),
                        default=Value('default'),
                        output_field=TextField()
                    )
                ).values(
                    json=JSONObject(id='rank_id',
                                    count='count',
                                    name='rank_name',
                                    condition='condition')
                )
            ))
        )

        return Response(q)


class TrackViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing tracks.
    create:
    Create a new track instance.
    delete:
    Delete track.
    read:
    Get track data.
    update:
    Update track data.
    partial_update:
    Partial update track data.
    """

    serializer_class = TrackSerializer

    permission_classes = (TrackAccessPolicy,)

    def get_queryset(self):
        return TrackAccessPolicy.scope_queryset(
            self.request, Track.objects.all()
        )


class CampaignManagementViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing campaign management.
    create:
    Create a new campaign management instance.
    delete:
    Delete campaign management.
    read:
    Get campaign management data.
    update:
    Update campaign management data.
    partial_update:
    Partial update campaign management data.
    """

    serializer_class = CampaignManagementSerializer

    permission_classes = (CampaignManagementAccessPolicy,)

    def get_queryset(self):
        return CampaignManagementAccessPolicy.scope_queryset(
            self.request, CampaignManagement.objects.all()
        )


class NotificationViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing messages.
    create:
    Create a new campaign notification.
    delete:
    Delete notification.
    read:
    Get notification data.
    update:
    Update notification data.
    partial_update:
    Partial update notification data.
    """

    # filterset_fields = {
    #     'importance': ['exact'],
    #     'campaign': ['exact'],
    #     'rank': ['exact'],
    #     'receiver_task': ['exact'],
    #     'sender_task': ['exact'],
    #     'trigger_go': ['exact'],
    #     'created_at': ['lte', 'gte'],
    #     'updated_at': ['lte', 'gte']
    # }
    permission_classes = (NotificationAccessPolicy,)
    filterset_fields = {
        "campaign": ["exact"],
        "rank": ["exact"],
        "title": ["icontains"],
        "text": ["icontains"],
        "importance": ["exact"],
        "trigger_go": ["exact"],
        "target_user": ["exact"],
        "sender_task": ["exact"],
        "receiver_task": ["exact"],
        'created_at': ['lte', 'gte', 'lt', 'gt'],
    }

    def get_serializer_class(self):
        if self.action in ['create', 'partial_update', 'update', 'retrieve']:
            return NotificationSerializer
        if self.action in ['list']:
            return NotificationListSerializer
        return NotificationListSerializer

    def get_queryset(self):
        return NotificationAccessPolicy.scope_queryset(
            self.request, Notification.objects.all().order_by('-created_at')
        )

    @paginate
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        qs = qs.select_related(
            'campaign',
            'rank',
            'target_user',
            'sender_task',
            'receiver_task'
        )

        return qs

    def retrieve(self, request, pk=None):
        queryset = Notification.objects.all()
        notification = get_object_or_404(queryset, pk=pk)

        notification.open(request.user)

        serializer = NotificationSerializer(notification)
        return Response(serializer.data)

    @paginate
    @action(detail=False)
    def list_user_notifications(self, request, pk=None):
        notifications = utils.filter_for_user_notifications(
            self.filter_queryset(self.get_queryset()), request)
        return notifications

    @action(detail=True)
    def open_notification(self, request, pk):
        notification_status, created = self.get_object().open(request.user)
        return Response(
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @paginate
    @action(detail=False)
    def last_task_notifications(self, request, pk=None):
        q = self.filter_queryset(self.get_queryset()) \
            .exclude(Q(receiver_task__isnull=True) &
                     Q(sender_task__isnull=True)) \
            .select_related('receiver_task') \
            .order_by('receiver_task', '-created_at') \
            .distinct('receiver_task')
        return q

    @action(detail=False)
    def read_all_notifications(self, request, pk=None):

        campaign = request.GET.get('campaign')

        if campaign:
            notifications = utils.filter_for_user_notifications(
                self.filter_queryset(self.get_queryset()), request)

            notifications = notifications.filter(campaign=campaign)
        else:
            notifications = utils.filter_for_user_notifications(
                self.filter_queryset(self.get_queryset()), request)

        # notifications = utils.filter_for_user_notifications(
        #     self.filter_queryset(self.get_queryset()), request)

        for notification in notifications:
            notification.open(request.user)
        return HttpResponse("Notifications marked as read successfully", status=200)


class ResponseFlattenerViewSet(viewsets.ModelViewSet):
    filterset_fields = {
        'task_stage': ['exact'],
        'task_stage__chain__campaign': ['exact'],
        'task_stage__chain': ['exact'],
        'created_at': ['lte', 'gte', 'lt', 'gt'],
        'updated_at': ['lte', 'gte', 'lt', 'gt']
    }
    permission_classes = (ResponseFlattenerAccessPolicy,)

    def get_queryset(self):
        return ResponseFlattenerAccessPolicy.scope_queryset(
            self.request, ResponseFlattener.objects.all()
        )

    def get_serializer_class(self):
        if self.action in ['create', 'partial_update', 'update']:
            return ResponseFlattenerCreateSerializer
        if self.action in ['retrieve', 'list']:
            return ResponseFlattenerReadSerializer

    @action(detail=True)
    def csv(self, request, pk=None):
        response_flattener = self.get_object()
        tasks = response_flattener.task_stage.tasks.all()
        filename = 'results'
        response = HttpResponse(
            content_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}.csv"'
            },
        )
        items = []
        columns = set()
        for task in tasks:
            row = response_flattener.flatten_response(task)
            items.append(row)
            [columns.add(i) for i in row.keys()]
        ordered_columns = response_flattener.ordered_columns()

        columns_not_in_main_schema = utils.array_difference(columns,
                                                            ordered_columns + response_flattener.columns)
        if columns_not_in_main_schema:
            for i in items:
                for column in columns_not_in_main_schema:
                    if column in i.keys():
                        del i[column]
            col = ["description"]
            ordered_columns += col
            items[0][col[0]] = ", ".join(columns_not_in_main_schema)

        writer = csv.DictWriter(response, fieldnames=ordered_columns)
        writer.writeheader()
        writer.writerows(items)
        return response


class TaskAwardViewSet(viewsets.ModelViewSet):
    filterset_fields = {
        'task_stage_completion': ['exact'],
        'task_stage_verified': ['exact'],
        'rank': ['exact'],
        'count': ['lte', 'gte', 'lt', 'gt'],
        'created_at': ['lte', 'gte', 'lt', 'gt'],
        'updated_at': ['lte', 'gte', 'lt', 'gt']
    }

    permission_classes = (TaskAwardAccessPolicy,)

    def get_queryset(self):
        return TaskAwardAccessPolicy.scope_queryset(
            self.request, TaskAward.objects.all()
        )

    def get_serializer_class(self):
        return TaskAwardSerializer


class DynamicJsonViewSet(viewsets.ModelViewSet):
    filterset_fields = {
   #     'task_stage': ['exact'],
    }

    permission_classes = (DynamicJsonAccessPolicy,)

    def get_queryset(self):
        return DynamicJsonAccessPolicy.scope_queryset(
            self.request, DynamicJson.objects.all()
        )

    def get_serializer_class(self):
        return DynamicJsonReadSerializer


class TestWebhookViewSet(viewsets.ModelViewSet):
    serializer_class = TestWebhookSerializer
    queryset = TestWebhook.objects.all()

    @action(detail=True, methods=['get'])
    def check_result(self, request, pk=None):
        test_webhook = TestWebhook.objects.get(pk=pk)
        expected_task = test_webhook.expected_task
        sent_task = test_webhook.sent_task
        webhook = Webhook.objects.filter(
            task_stage=expected_task.stage.pk).get()
        if webhook:
            response = requests.post(webhook.url, json=sent_task.responses,
                                     headers={}).json()
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if response == expected_task.responses:
            return Response({'equals': True,
                             'response': response})
        return Response({'equals': False,
                         'expected_response': expected_task.responses,
                         'actual_response': response})


class UserStatisticViewSet(GenericViewSet):
    permission_classes = (UserStatisticAccessPolicy,)

    def get_queryset(self):
        return UserStatisticAccessPolicy.scope_queryset(
            self.request, CustomUser.objects.values('id')
        )

    def get_serializer_class(self):
        return UserStatisticSerializer

    @action(methods=["GET"], detail=False)
    def total_count(self, request, *args, **kwargs):
        """
        Returns total count of users in one campaign.
        To exclude managers from calculation add filter ?exclude_managers=true.
        """
        managed_campaigns = request.user.managed_campaigns.all()
        user_campaigns = self.get_campaigns_by_query_params(request,
                                                            managed_campaigns)

        qs = self.get_queryset()
        qs = self.filter_managers(request, CampaignManagement.objects.filter(
            campaign__in=user_campaigns).values("user"), qs)

        return Response({"total": qs.values('id').count()})

    @paginate
    @action(methods=["GET"], detail=False)
    def new_users(self, request, *args, **kwargs):
        """
        Returns list of all users that have joined to the system during some period.
        In query params provide start and end dates for filter by period.
        Example: ?start=2020-01-16&end=2021-01-16

        To exclude managers from calculation add filter ?exclude_managers=true.
        """
        date_range_filter = self.range_date_filter(*self.get_range(request),
                               key="tracks__ranks__users__created_at")
        filters = [
            Q(**date_range_filter),
        ]

        managed_campaigns = request.user.managed_campaigns.all()
        user_campaigns = self.get_campaigns_by_query_params(request,
                                                            managed_campaigns)
        if request.query_params.get("exclude_managers", None) == "true":
            managers = CampaignManagement.objects.filter(
                campaign__in=user_campaigns)
            filters.append(~Q(tracks__ranks__users__in=managers.values("user")))

        user_campaigns = user_campaigns.values("id", "name").annotate(
            count=Count("tracks__ranks__users",
                        filter=Q(*filters),
                        distinct=True)
        )

        return user_campaigns

    @paginate
    @action(methods=["GET"], detail=False)
    def unique_users(self, request, *args, **kwargs):
        """
        Returns list of users that have any activity during some period of time.
        Activity means that users has new tasks during some period.
        To filter by some period use filters start and end.
        Example: ?start=2020-01-16&end=2021-01-16

        To filter by campaign id use "campaign" query param and provide id:
        ?campaign=123

        To exclude managers from calculation add filter ?exclude_managers=true.
        """
        date_range_filter = self.range_date_filter(*self.get_range(request),
                                                   key="created_at")

        qs_users = self.filter_queryset(self.get_queryset())

        managed_campaigns = request.user.managed_campaigns.all()
        user_campaigns = self.get_campaigns_by_query_params(request,
                                                            managed_campaigns)
        managers_by_campaign = CampaignManagement.objects.none()
        if request.query_params.get("exclude_managers", None) == "true":
            managers = CampaignManagement.objects.filter(
                campaign__in=user_campaigns)
            managers_by_campaign = managers.filter(
                campaign_id=OuterRef(OuterRef(OuterRef("id"))))

        campaign_info = user_campaigns.values("id", "name").annotate(
            count=Subquery(
                Task.objects.filter(
                    stage__chain__campaign_id=OuterRef("id"),
                    assignee__isnull=False,
                    assignee__in=qs_users.exclude(
                        id__in=managers_by_campaign.values("user")),
                    **date_range_filter
                ).values("stage__chain__campaign").annotate(
                    count=Count("assignee", distinct=True)
                ).values("count")
            )
        )

        return campaign_info

    date_format = "%Y-%m-%d"  # "2013-11-30"
    query_params = ['start', 'end']

    def get_range(self, request):
        start = self.get_date(
            request.query_params.get(self.query_params[0], None))
        end = self.get_date(
            request.query_params.get(self.query_params[1], None))

        return start, end

    # converts date to DateTime object
    def get_date(self, date):
        if date:
            try:
                date = date[:10]
                return datetime.strptime(date, self.date_format)
            except:
                raise ValidationError(
                    f"Invalid key format: {date}. "
                    f"Properly format: {self.date_format}")
        return None

    # generate filter schema to filter by datetime
    def range_date_filter(self, start, end, key):
        greater_key = key + "__gte"
        less_key = key + "__lte"
        if start and end:
            return {greater_key: start, less_key: end}
        elif start and not end:
            return {greater_key: start}
        elif not start and end:
            return {less_key: end}
        elif not start and not end:
            return {}

    # return managed campaign with filter
    def get_campaigns_by_query_params(self, request, campaigns):
        campaign_filter = request.query_params.get("campaign", None)
        if campaign_filter and campaign_filter.isdigit():
            campaigns = campaigns.filter(id=int(campaign_filter))
        return campaigns

    def filter_managers(self, request, managers, qs):
        exclude_managers = request.query_params.get("exclude_managers", None)
        if exclude_managers == "true":
            return qs.exclude(id__in=managers)
        return qs


# Custom view to generate a new token or return an existing one
class AuthViewSet(viewsets.GenericViewSet):
    @action(detail=False, methods=["GET"])
    def my_token(self, request, *args, **kwargs):
        user = request.user

        # Check if a token already exists for the user
        token, created = Token.objects.get_or_create(user=user)

        # If token doesn't exist, generate a new one
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        return Response({'token': token.key}, status=status_code)


class FCMTokenViewSet(viewsets.ModelViewSet):
    permission_classes = (UserFCMTokenAccessPolicy,)

    @action(detail=True, methods=['post'])
    def update_fcm_token(self, request, *args, **kwargs):
        serializer = FCMTokenSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            user = request.user

            user.fcm_token = serializer.validated_data['fcm_token']
            user.save()

            return Response({'detail': 'FCM token updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VolumeViewSet(viewsets.ModelViewSet):
    """
    list:
    Return a list of all the existing Volumes.
    create:
    Create a new Volume instance.
    delete:
    Delete Volume.
    read:
    Get Volume data.
    update:
    Update Volume data.
    partial_update:
    Partial update Volume data.
    """

    filterset_fields = {
        'track_fk': ['exact'],
        'track_fk__campaign': ['exact']
    }

    serializer_class = VolumeSerializer

    permission_classes = (VolumeAccessPolicy,)

    def get_queryset(self):
        user = self.request.user

        qs = Volume.objects.filter(closed=False)
        qs = VolumeAccessPolicy.scope_queryset(self.request, qs)

        if user.is_authenticated:
            # Annotate default rank check
            # qs = qs.annotate(
            #     user_has_default_rank=Exists(
            #         RankRecord.objects.filter(
            #             user=user,
            #             rank_id=OuterRef('track_fk__default_rank')
            #         )
            #     )
            # )
            
            # According to the access policy, user will only see volumes with matching default rank
            qs = qs.annotate(user_has_default_rank=Value(True))
            
            # Annotate opening ranks check - check if user has AT LEAST ONE matching rank
            qs = qs.annotate(
                user_has_opening_ranks=Exists(
                    RankRecord.objects.filter(
                        user=user,
                        rank__opened_volumes=OuterRef('pk')
                    )
                )
            )
            
            # Similar logic for closing ranks
            qs = qs.annotate(
                user_has_closing_ranks=Exists(
                    RankRecord.objects.filter(
                        user=user,
                        rank__closed_volumes=OuterRef('pk')
                    )
                )
            )
        else:
            # For anonymous users, all rank checks are False
            qs = qs.annotate(
                user_has_default_rank=Value(False),
                user_has_opening_ranks=Value(False),
                user_has_closing_ranks=Value(False)
            )

        return qs