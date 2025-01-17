from django.apps import apps
from django.db.models import Subquery, OuterRef, Q, TextField
from django.db.models.functions import Cast
from rest_framework import filters
from rest_framework.filters import BaseFilterBackend

from api.api_exceptions import CustomApiException
from api.constans import DjangoORMConstants, ConditionalStageConstants
from api.serializer import PostJSONFilterSerializer, TaskResponsesFilterSerializer
from api.utils.django_expressions import ArraySubquery


class BasePostJSONFilter(filters.BaseFilterBackend):
    search_param = None
    serializer = PostJSONFilterSerializer
    field_name = ''

    def is_post_request(self, request) -> bool:
        return request.method == 'POST'

    def get_search_terms(self, request):
        """
        Search terms are set by a ?search=... query parameter,
        and may be comma and/or whitespace delimited.
        """
        params = request.query_params.get(self.search_param, '')
        params = params.replace('\x00', '')  # strip null characters
        params = params.replace(',', ' ')
        return params.split()

    def filter_queryset(self, request, queryset, view):
        if not self.is_post_request(request) or not self.get_search_terms(request):
            return queryset

        data = self.serializer(data=request.data)
        if data.is_valid():
            data = data.get_object()
            base = self.prefilter_queryset(queryset, data)
            for item in data['items_conditions']:
                searched_field = self.field_name + DjangoORMConstants.LOOKUP_SEP + item.get('field')
                val_type = ConditionalStageConstants.SUPPORTED_TYPES.get(item.get('type'), None)
                base = base.filter(**{searched_field + '__isnull': False})
                for condition in item.get('conditions'):
                    filter_field = self.construct_search(searched_field, condition.get('operator'))
                    val = condition.get('value')
                    try:
                        base = base.filter(**{filter_field: val_type(val)})
                    except Exception as e:
                        raise CustomApiException(400, f'Can not convert "{val}" to the {val_type}')
            return base
        return queryset

    def construct_search(self, field_name, op):
        lookup = DjangoORMConstants.LOOKUP_PREFIXES.get(op)
        if not lookup:
            lookup = 'icontains'
        return DjangoORMConstants.LOOKUP_SEP.join([field_name, lookup])

    def prefilter_queryset(self, queryset, data):
        return queryset


class ResponsesContainsFilter(filters.SearchFilter):
    search_param = "responses__icontains"
    field = "responses"
    template = 'rest_framework/filters/search.html'
    search_title = 'Task Responses Filter if responses contains'
    search_description = "Find tasks by their responses if task contains"


    def filter_queryset(self, request, queryset, view):
        term = self.get_search_terms(request)
        if not term:
            return queryset

        Task = apps.get_model(app_label="api", model_name="Task")

        all_tasks = Task.objects.filter(
            case__in=queryset.values("case"),
        ).select_related("case")
        available_cases = all_tasks.annotate(
            r=Cast(self.field, output_field=TextField())
        ).filter(r__icontains=term)
        return queryset.filter(case__in=available_cases.values("case"))

    def get_search_terms(self, request):
        params = request.query_params.get(self.search_param, '')
        params = params.replace('\x00', '')  # strip null characters
        params = params.replace(',', ' ')
        return params

class CategoryInFilter(BaseFilterBackend):
    search_param = "category_in"
    search_title = "All campaigns with categories eaquals or below selected category."

    def filter_queryset(self, request, queryset, view):
        """
        Return a filtered queryset.
        """
        term = self.get_search_terms(request)

        if not term or not term.isdigit():
            return queryset

        model_Category = apps.get_model(app_label="api", model_name="Category")
        categories = model_Category.objects.get(
            id=int(term)).get_all_subcategories(
            recursively=True
        )

        return queryset.filter(categories__in=categories).distinct()

    def get_search_terms(self, request):
        """
        Search terms are set by a ?search=... query parameter,
        and may be comma and/or whitespace delimited.
        """
        params = request.query_params.get(self.search_param, '')
        params = params.replace('\x00', '')  # strip null characters
        params = params.replace(',', ' ')
        return params


# class IndividualChainCompleteFilter(BaseFilterBackend):
#     search_param = "completed"

#     def filter_queryset(self, request, queryset, view):
#         completed_param = request.query_params.get(self.search_param, '').lower()
#         if completed_param not in ['true', 'false']:
#             return queryset

#         completed_filter_param = (completed_param == 'true')

#         # Get all relevant stages first
#         stages_with_completion = queryset.filter(
#             stages__taskstage__complete_individual_chain=True
#         ).values_list('id', 'stages__taskstage__id')

#         if not stages_with_completion:
#             return queryset

#         # Get chain IDs and their stage IDs
#         chain_stages = {}
#         for chain_id, stage_id in stages_with_completion:
#             if stage_id:  # Ensure stage_id is not None
#                 chain_stages.setdefault(chain_id, set()).add(stage_id)

#         # Get completion status for all relevant stages in one query
#         Task = apps.get_model(app_label="api", model_name="Task")
#         completed_stages = set(
#             Task.objects.filter(
#                 assignee=request.user,
#                 stage_id__in={stage_id for stages in chain_stages.values() for stage_id in stages},
#                 complete=True
#             ).values_list('stage_id', flat=True).distinct()
#         )

#         # Filter chains based on completion status
#         completed_chain_ids = {
#             chain_id 
#             for chain_id, stage_ids in chain_stages.items()
#             if completed_filter_param == (all(stage_id in completed_stages for stage_id in stage_ids))
#         }

#         return queryset.filter(id__in=completed_chain_ids)
    
class IndividualChainCompleteFilter(BaseFilterBackend):
    search_param = "completed"

    def filter_queryset(self, request, queryset, view):
        completed_param = request.query_params.get(self.search_param, '').lower()

        if completed_param not in ['true', 'false']:
            return queryset

        completed_filter_param = (completed_param == 'true')

        Task = apps.get_model(app_label="api", model_name="Task")
        user_task_for_stage = Task.objects.filter(assignee=request.user,
                stage_id=OuterRef("stages__taskstage"),
            ).order_by("-created_at").values("complete")

        annotated_chains = queryset.values("id", "stages__taskstage").filter(stages__taskstage__complete_individual_chain=True).annotate(
            completed=Subquery(user_task_for_stage)
        )

        if completed_filter_param:
            queryset = queryset.filter(id__in=annotated_chains.filter(completed=True).values("id"))
        else:
            queryset = queryset.filter(id__in=annotated_chains.filter(Q(completed=False) | Q(completed__isnull=True)).values("id"))

        return queryset


