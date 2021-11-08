from abc import ABC

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django import forms

from .models import Campaign, Chain, \
    TaskStage, ConditionalStage, Case, Task, CustomUser, Rank, RankLimit, RankRecord, CampaignManagement, Track, Log, \
    Notification, NotificationStatus, AdminPreference
from api.asyncstuff import process_completed_task
from django.contrib import messages
from django.utils.translation import ngettext
from .utils import set_rank_to_user_action


class InputFilter(admin.SimpleListFilter, ABC):
    template = 'admin/input_filter.html'

    def lookups(self, request, model_admin):
        # Dummy, required to show the filter.
        return ((),)

    def choices(self, changelist):
        # Grab only the "all" option.
        all_choice = next(super().choices(changelist))
        all_choice['query_parts'] = (
            (k, v)
            for k, v in changelist.get_filters_params().items()
            if k != self.parameter_name
        )
        yield all_choice


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

class UserNoRankFilter(SimpleListFilter):
    title = "Users who do not have rank below"
    parameter_name = "Responses"

    def lookups(self, request, model_admin):
        rank_lookups = []
        for rank in list(Rank.objects.all()):
            rank_lookups.append((rank.id, rank.name))
        return rank_lookups

    def queryset(self, request, queryset):
        return queryset.exclude(ranks__id=self.value())

class UserTaskCompleteFilter(InputFilter):
    parameter_name = 'completed_stages'
    title = 'Completed Tasks (enter list of task stages separated by whitespace). Force completed will not be included.'

    def queryset(self, request, queryset):
        terms = self.value()

        if terms is None or terms == '':
            return queryset

        for term in terms.split():
            tasks = Task.objects.filter(stage__id=term,
                                        complete=True,
                                        force_complete=False)
            queryset = queryset.filter(tasks__in=tasks)

        return queryset


class StageFilter(InputFilter):
    parameter_name = 'json'
    title = 'Search by json (<key>, <value>). Example: title, Hello!'

    def queryset(self, request, queryset):
        terms = self.value()


        if terms is None or terms == '':
            return queryset

        terms = [i.strip() for i in terms.split(',')]

        return queryset.all().filter(stage__json_schema__contains=f'"{terms[0]}": "{terms[1]}')

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_filter = (UserTaskCompleteFilter, 'ranks', UserNoRankFilter)

    def get_actions(self, request):
        actions = super(CustomUserAdmin, self).get_actions(request)
        campaign = AdminPreference.objects.filter(campaign__managers=request.user)
        if list(campaign):
            queryset = Rank.objects.filter(track__campaign=campaign[0].campaign)
            for rank in queryset:
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
    list_filter = (StageFilter,
                   'stage__chain__campaign',
                   'stage__chain',
                   'stage',
                   'complete',
                   'force_complete',
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
            process_completed_task(task) # ToDo: put complete=True inside cycle, account for possible interruptions

        self.message_user(request, ngettext(
            '%d task was successfully marked as completed.',
            '%d tasks were successfully marked as completed.',
            updated,
        ) % updated, messages.SUCCESS)

    @admin.action(description='Mark selected tasks as completed force')
    def make_completed_force(self, request, queryset):
        updated = queryset.update(complete=True, force_complete=True) # todo: test on force_complete
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


# class AdminPreferenceForm(forms.ModelForm):
#     def clean(self):
#         if AdminPreference.objects.filter(user=self.request.user):
#             raise forms.ValidationError(
#                 'You have already created Admin Preferences Profile. '
#                 'You cannot create more than one.'
#             )


class AdminPreferenceAdmin(admin.ModelAdmin):
    model = AdminPreference
    # form = AdminPreferenceForm
    list_display = ('user',
                    'campaign')

    exclude = ('user', )

    def has_add_permission(self, request, obj=None):
        return not bool(AdminPreference.objects.filter(user=request.user))

    def has_view_or_change_permission(self, request, obj=None):
        if obj is not None and obj.user != request.user:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.user != request.user:
            return False
        return True

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            # Only set user during the first save.
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def get_form(self, request, *args, **kwargs):
        form = super(AdminPreferenceAdmin, self).get_form(request, *args, **kwargs)
        form.request = request
        return form

    def get_queryset(self, request):
        queryset = super(AdminPreferenceAdmin, self).get_queryset(request)
        return queryset.filter(user=request.user)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "campaign":
            kwargs["queryset"] = db_field.related_model.objects.filter(managers=request.user)
        return super(AdminPreferenceAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


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
admin.site.register(AdminPreference, AdminPreferenceAdmin)
