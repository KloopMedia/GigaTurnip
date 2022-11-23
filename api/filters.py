from rest_framework import filters

from api.api_exceptions import CustomApiException
from api.constans import DjangoORMConstants, ConditionalStageConstants
from api.serializer import PostJSONFilterSerializer, TaskResponsesFilterSerializer


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
    search_param = "responses_contains"
    template = 'rest_framework/filters/search.html'
    search_title = 'Task Responses Filter if responses contains'
    search_description = "Find tasks by their responses if task contains"


class TaskResponsesContainsFilter(BasePostJSONFilter):
    serializer = TaskResponsesFilterSerializer
    search_param = "responses_filter_values"
    field_name = 'responses'

    def prefilter_queryset(self, queryset, data):
        return queryset.filter(stage=data.get('stage'))