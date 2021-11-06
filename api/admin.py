from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin

from .models import Campaign, Chain, \
    TaskStage, ConditionalStage, Case, Task, CustomUser, Rank, RankLimit, RankRecord, CampaignManagement, Track, Log, \
    Notification, NotificationStatus
from api.asyncstuff import process_completed_task
from django.contrib import messages
from django.utils.translation import ngettext
from .utils import set_rank_to_user_action


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


class LogsTaskResponsesStatusFilter(TaskResponsesStatusFilter):
    def queryset(self, request, queryset):
        if self.value() == "json_empty":
            return queryset.distinct().filter(task__responses__iexact="{}")
        elif self.value() == "null":
            return queryset.distinct().filter(task__responses__isnull=True)
        elif self.value() == "empty_string":
            return queryset.distinct().filter(task__responses__iexact="")
        elif self.value() == "not_empty":
            return queryset.distinct()\
                .exclude(task__responses__iexact="")\
                .exclude(task__responses__iexact="{}")\
                .exclude(task__responses__isnull=True)


class CustomUserAdmin(UserAdmin):
    model = CustomUser

    def get_actions(self, request):
        actions = super(CustomUserAdmin, self).get_actions(request)
        for rank in Rank.objects.filter(track__campaign_id=request.user.id):  # .filter(admin_preferences=)
            action = set_rank_to_user_action(rank)
            actions[action.__name__] = (action,
                                        action.__name__,
                                        action.short_description)
        return actions


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

    actions = ['make_completed', 'make_completed_force']

    @admin.action(description='Mark selected tasks as completed')
    def make_completed(self, request, queryset):
        updated = queryset.update(complete=True)
        for task in queryset:
            process_completed_task(task)

        self.message_user(request, ngettext(
            '%d task was successfully marked as completed.',
            '%d tasks were successfully marked as completed.',
            updated,
        ) % updated, messages.SUCCESS)

    @admin.action(description='Mark selected tasks as completed force')
    def make_completed_force(self, request, queryset):
        updated = queryset.update(complete=True)
        self.message_user(request, ngettext(
            '%d task was successfully marked as force completed.',
            '%d tasks were successfully marked as force completed.',
            updated,
        ) % updated, messages.SUCCESS)

class LogAdmin(admin.ModelAdmin):
    list_display = ('id',
                    'name',
                    'campaign',
                    'stage',
                    'task',
                    'user',
                    'created_at',
                    'updated_at')
    list_filter = ('campaign',
                   'stage',
                   'created_at',
                   'task__complete',
                   LogsTaskResponsesStatusFilter)
    search_fields = ('id',
                     'name',
                     'stage__name',
                     'task__id'
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
admin.site.register(Notification)
admin.site.register(NotificationStatus)
