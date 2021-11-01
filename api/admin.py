from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin

from .models import Campaign, Chain, \
    TaskStage, ConditionalStage, Case, Task, CustomUser, Rank, RankLimit, RankRecord, CampaignManagement, Track, Log


class TaskResponsesStatusFilter(SimpleListFilter):
    title = "Responses JSON Status"
    parameter_name = "Responses"

    def lookups(self, request, model_admin):
        return [
            ("not_empty", "Filled Responses"),
            ("json_empty", "Empty JSON Responses ({})"),
            ("empty_string", "Empty String Responses()"),
            ("null", "Null Responses (__isnull==True)")
        ]

    def queryset(self, request, queryset):
        if self.value() == "json_empty":
            return queryset.distinct().filter(responses__iexact="{}")
        elif self.value() == "null":
            return queryset.distinct().filter(responses__isnull=True)
        elif self.value() == "empty_string":
            return queryset.distinct().filter(responses__iexact="")
        elif self.value() == "not_empty":
            return queryset.distinct()\
                .exclude(responses__iexact="")\
                .exclude(responses__iexact="{}")\
                .exclude(responses__isnull=True)


class CustomUserAdmin(UserAdmin):
    model = CustomUser


class ChainAdmin(admin.ModelAdmin):
    list_display = ('name', 'campaign', )
    list_filter = ('campaign',)
    search_fields = ('name',)


class StageAdmin(admin.ModelAdmin):
    list_display = ('name', 'chain',)
    list_filter = ('chain__campaign', 'chain')
    search_fields = ('name',
                     'chain__name',
                     'chain__campaign__name', )


class CaseAdmin(admin.ModelAdmin):
    search_fields = ('pk', )


class TaskAdmin(admin.ModelAdmin):
    list_display = ('id',
                    'case',
                    'stage',
                    'assignee',
                    'created_at',
                    'updated_at')
    list_filter = ('stage__chain__campaign',
                   'stage__chain',
                   'stage',
                   'complete',
                   TaskResponsesStatusFilter,
                   'created_at',
                   'updated_at')
    search_fields = ('id',
                     'case__id',
                     'stage__name',
                     'assignee__email',
                     'stage__chain__name',
                     'stage__chain__campaign__name')
    autocomplete_fields = ('in_tasks', )
    raw_id_fields = ('stage', 'assignee', 'case', )
    readonly_fields = ('created_at', 'updated_at')

class LogAdmin(admin.ModelAdmin):
    list_display = ('id',
                    'name',
                    'campaign',
                    'stage',
                    'user',
                    'created_at',
                    'updated_at')
    list_filter = ('campaign',
                   'stage',
                   'stage',
                   'created_at')
    search_fields = ('id',
                     'name',
                     'stage__name'
                     )
    raw_id_fields = ('stage', 'user', 'case', 'task')
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Campaign)
admin.site.register(Chain, ChainAdmin)
admin.site.register(TaskStage, StageAdmin)
admin.site.register(ConditionalStage, StageAdmin)
admin.site.register(Case, CaseAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(Rank)
admin.site.register(RankLimit)
admin.site.register(RankRecord)
admin.site.register(CampaignManagement)
admin.site.register(Track)
admin.site.register(Log, LogAdmin)
