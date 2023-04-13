from abc import ABC

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count

from .asyncstuff import process_completed_task
from .models import (
    Campaign, Chain, TaskStage, ConditionalStage, Case, Task,  CustomUser,
    Rank, RankLimit, RankRecord, CampaignManagement, Track, Log,
    Notification, NotificationStatus, AdminPreference, Stage, Integration,
    Webhook, CopyField, StagePublisher, Quiz, ResponseFlattener, TaskAward,
    DynamicJson, PreviousManual, AutoNotification, ConditionalLimit,
    DatetimeSort, ErrorItem, TestWebhook, CampaignLinker, ApproveLink,
    Language, Category
)
from django.contrib import messages
from django.utils.translation import ngettext
from api.utils.utils import set_rank_to_user_action, filter_by_admin_preference


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
            return queryset.distinct() \
                .exclude(responses__iexact="") \
                .exclude(responses__iexact="{}") \
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
            return queryset.distinct() \
                .exclude(task__responses__iexact="") \
                .exclude(task__responses__iexact="{}") \
                .exclude(task__responses__isnull=True)


class DuplicateTasksCaseFilter(SimpleListFilter):
    title = "Duplicate Tasks Filter"
    parameter_name = "Tasks"

    def lookups(self, request, model_admin):
        return [
            ("duplicate", "Duplicate"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "duplicate":
            qs = Task.objects.values('stage__id', 'case__id') \
                .annotate(Count('pk')).filter(pk__count__gte=2).values_list('case_id', flat=True)
            return queryset.filter(id__in=qs)


class DuplicateTasksFilter(SimpleListFilter):
    title = "Duplicate Tasks Filter"
    parameter_name = "Tasks"

    def lookups(self, request, model_admin):
        return [
            ("duplicate", "Duplicate"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "duplicate":
            qs = Task.objects.values('stage__id', 'case__id') \
                .annotate(Count('pk')).filter(pk__count__gte=2)
            cases = qs.values_list('case_id', flat=True)
            stages = qs.values_list('stage_id', flat=True)
            return queryset.filter(case_id__in=cases).filter(stage_id__in=stages)


class UserNoRankFilter(SimpleListFilter):
    title = "not existing Ranks"
    parameter_name = "rank_exclude"

    def lookups(self, request, model_admin):
        rank_lookups = []
        ranks = Rank.objects.filter(track__campaign__campaign_managements__user=request.user)
        for rank in ranks:
            rank_lookups.append((rank.id, rank.name))
        return rank_lookups

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
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
    list_filter = (
        UserTaskCompleteFilter,
        UserNoRankFilter,
        "ranks",
        "is_active",
        "is_staff",
        "is_superuser",
        "groups",
    )
    search_fields = ("id", "email", "first_name", "last_name", "username")

    def get_actions(self, request):
        actions = super(CustomUserAdmin, self).get_actions(request)
        preference = AdminPreference.objects.filter(campaign__in=request.user.managed_campaigns.all(), user=request.user)
        if preference:
            queryset = Rank.objects.filter(track__in=preference[0].campaign.tracks.all())
            for rank in queryset:
                action = set_rank_to_user_action(rank)
                actions[action.__name__] = (action,
                                            action.__name__,
                                            action.short_description)
        return actions

    def get_queryset(self, request):
        queryset = super(CustomUserAdmin, self).get_queryset(request)
        if not request.user.is_superuser:
            managed_campaigns = request.user.managed_campaigns.all()
            campaigns_ranks = Rank.objects.filter(track__in=managed_campaigns.values_list('tracks', flat=True))
            return queryset.filter(ranks__in=campaigns_ranks).distinct()
        return queryset.all()


class CampaignAdmin(admin.ModelAdmin):
    search_fields = ("id", "name", )
    autocomplete_fields = ("default_track", "category", "language", )


class ChainAdmin(admin.ModelAdmin):
    list_display = ("name", "campaign",)
    list_filter = ("campaign",)
    autocomplete_fields = ("campaign",)
    search_fields = ("name", "description",)

    def get_form(self, request, *args, **kwargs):
        form = super(ChainAdmin, self).get_form(request, *args, **kwargs)
        form.request = request
        return form

    def get_queryset(self, request):
        queryset = super(ChainAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, "")


class GeneralStageAdmin(admin.ModelAdmin):
    search_fields = ('name',
                     'chain__name',
                     'chain__campaign__name',)

    def has_add_permission(self, request, obj=None):
        return False

    def has_view_or_change_permission(self, request, obj=None):
        return False

    # def has_delete_permission(self, request, obj=None):
    #     return False

    def has_module_permission(self, request):
        return False

    def get_form(self, request, *args, **kwargs):
        form = super(GeneralStageAdmin, self).get_form(request, *args, **kwargs)
        form.request = request
        return form

    def get_queryset(self, request):
        queryset = super(GeneralStageAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, "chain__")


class StageAdmin(admin.ModelAdmin):
    list_display = ('name', 'id', 'chain',)
    list_filter = ('chain__campaign', 'chain')
    search_fields = ('name',
                     'chain__name',
                     'chain__campaign__name',)
    autocomplete_fields = ('chain', 'in_stages')

    def get_form(self, request, *args, **kwargs):
        form = super(StageAdmin, self).get_form(request, *args, **kwargs)
        form.request = request
        return form

    def get_queryset(self, request):
        queryset = super(StageAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, "chain__")


class ConditionalLimitAdmin(admin.ModelAdmin):
    model = ConditionalLimit
    list_display = ('conditional_stage', )
    autocomplete_fields = ('conditional_stage', )
    list_filter = (
        'conditional_stage__chain',
    )

    def get_queryset(self, request):
        queryset = super(ConditionalLimitAdmin, self).get_queryset(request)
        return queryset \
            .filter(
            conditional_stage__chain__campaign__campaign_managements__user=request.user
        )


class TaskStageAdmin(StageAdmin):
    autocomplete_fields = StageAdmin.autocomplete_fields + \
                          ("displayed_prev_stages", "assign_user_from_stage")


class IntegrationAdmin(admin.ModelAdmin):
    search_fields = ('task_stage__name',)
    autocomplete_fields = ('task_stage',)

    def get_form(self, request, *args, **kwargs):
        form = super(IntegrationAdmin, self).get_form(request, *args, **kwargs)
        form.request = request
        return form

    def get_queryset(self, request):
        queryset = super(IntegrationAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, "task_stage__chain__")


class WebhookAdmin(admin.ModelAdmin):
    search_fields = ('task_stage', 'url', )
    autocomplete_fields = ('task_stage', )

    def get_queryset(self, request):
        queryset = super(WebhookAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, 'task_stage__chain__')


class CaseAdmin(admin.ModelAdmin):
    list_filter = (DuplicateTasksCaseFilter,)
    search_fields = ('pk',)


class RankLimitAdmin(admin.ModelAdmin):
    list_display = ('id',
                    'rank',
                    'stage',
                    'created_at',
                    'updated_at')
    search_fields = ('pk', 'rank__name', 'stage__name', )
    autocomplete_fields = ('stage', 'rank')
    list_filter = (
        "rank",
        "stage",
        "stage__chain__campaign",
        "rank",
        'is_listing_allowed',
        'is_submission_open',
        'is_selection_open',
        'is_creation_open'
    )

    def get_queryset(self, request):
        queryset = super(RankLimitAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, "stage__chain__")


class RankRecordAdmin(admin.ModelAdmin):
    list_display = ('id',
                    'user',
                    'rank',
                    'created_at',
                    'updated_at')
    raw_id_fields = ('user', )
    autocomplete_fields = ('rank', )
    search_fields = ('user__email', 'user__username', 'user__last_name', 'user__first_name')

    def get_queryset(self, request):
        queryset = super(RankRecordAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, "rank__track__")


class TrackAdmin(admin.ModelAdmin):
    list_display = ('id',
                    'name',
                    'campaign',
                    'created_at',
                    'updated_at')
    #autocomplete_fields = ('campaign', )
    search_fields = ('campaign__name', 'name')

    def get_queryset(self, request):
        queryset = super(TrackAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, "")


class RankAdmin(admin.ModelAdmin):
    list_display = ("id",
                    "name",
                    "track",
                    "created_at",
                    "updated_at")
    autocomplete_fields = ("track", )
    search_fields = ("name", )
    list_select_related = (
        "track",
    )

    def get_queryset(self, request):
        queryset = super(RankAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, "track__")


class TaskAwardAdmin(admin.ModelAdmin):
    list_display = (
        "task_stage_completion",
        "task_stage_verified",
        "rank",
        "count"
    )
    list_filter = (
        "task_stage_completion__chain__campaign",
        "task_stage_completion",
        "task_stage_verified",
        "rank",
        "count"
    )
    autocomplete_fields = ('task_stage_completion', 'task_stage_verified', 'rank', 'notification')
    list_select_related = (
        "task_stage_completion",
        "task_stage_completion__chain__campaign",
        "task_stage_verified",
        "rank",
    )

    def get_queryset(self, request):
        queryset = super(TaskAwardAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, 'task_stage_completion__chain__')


class CopyFieldAdmin(admin.ModelAdmin):
    list_display = ("id",
                    "task_stage",
                    "copy_from_stage",
                    "fields_to_copy",
                    "created_at",
                    "updated_at")
    autocomplete_fields = ("task_stage", "copy_from_stage")
    search_fields = ("task_stage__name", "copy_from_stage__name")

    def get_queryset(self, request):
        queryset = super(CopyFieldAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, "task_stage__chain__")


class QuizAdmin(admin.ModelAdmin):
    list_display = ("pk",
                    "task_stage",
                    "correct_responses_task")
    autocomplete_fields = ("task_stage", )
    raw_id_fields = ("correct_responses_task",)
    search_fields = ("task_stage", )
    list_select_related = (
        "task_stage",
        "correct_responses_task",
        "correct_responses_task__case"
    )

    def get_queryset(self, request):
        queryset = super(QuizAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, "task_stage__chain__")


class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "case",
        "stage",
        "assignee",
        "created_at",
        "updated_at"
    )
    list_filter = (
        StageFilter,
        "stage__chain__campaign",
        "stage__chain",
        "stage",
        "stage__is_public",
        "complete",
        "force_complete",
        TaskResponsesStatusFilter,
        "created_at",
        "updated_at",
        DuplicateTasksFilter
    )
    search_fields = (
        "id",
        "case__id",
        "stage__name",
        "assignee__email",
        "stage__chain__name",
        "stage__chain__campaign__name"
    )
    autocomplete_fields = ("in_tasks",)
    raw_id_fields = ("stage", "assignee", "case",)
    readonly_fields = ("created_at", "updated_at")
    list_select_related = (
        "stage",
        "stage__chain",
        "case",
        "assignee"
    )

    actions = ["make_completed", "make_completed_force"]

    def get_form(self, request, *args, **kwargs):
        form = super(TaskAdmin, self).get_form(request, *args, **kwargs)
        form.request = request
        return form

    def get_queryset(self, request):
        queryset = super(TaskAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, "stage__chain__")

    @admin.action(description='Mark selected tasks as completed')
    def make_completed(self, request, queryset):
        updated = queryset.update(complete=True)
        for task in queryset:
            process_completed_task(task)  # ToDo: put complete=True inside cycle, account for possible interruptions

        self.message_user(request, ngettext(
            '%d task was successfully marked as completed.',
            '%d tasks were successfully marked as completed.',
            updated,
        ) % updated, messages.SUCCESS)

    @admin.action(description='Mark selected tasks as completed force')
    def make_completed_force(self, request, queryset):
        updated = queryset.update(complete=True, force_complete=True)
        self.message_user(request, ngettext(
            '%d task was successfully marked as force completed.',
            '%d tasks were successfully marked as force completed.',
            updated,
        ) % updated, messages.SUCCESS)


class LanguageAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "id")
    search_fields = ("name", "code")


class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", )
    list_filter = ("parents__name", )
    search_fields = ("name", )
    autocomplete_fields = ("parents", )

    class Meta:
        verbose_name = "Categories"


class LogAdmin(admin.ModelAdmin):
    list_display = ("id",
                    "name",
                    "campaign",
                    "stage",
                    "task",
                    "user",
                    "created_at",
                    "updated_at")
    list_filter = ("campaign",
                   "stage",
                   "created_at",
                   "task__complete",
                   LogsTaskResponsesStatusFilter)
    search_fields = ("id",
                     "name",
                     "stage__name",
                     "task__id"
                     )
    autocomplete_fields = (
        "campaign",
        "chain",
        "stage",
        "user",
        "case",
        "task",
        "track",
        "rank",
        "rank_limit",
        "rank_record"
    )
    raw_id_fields = ("stage", "user", "case", "task")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = (
        "campaign",
        "chain",
        "stage",
        "user",
        "case",
        "task",
        "track",
        "rank",
        "rank_limit",
        "rank_record"
    )


class ResponseFlattenerAdmin(admin.ModelAdmin):
    model = ResponseFlattener
    list_display = ("task_stage", "id", "copy_first_level", "copy_system_fields")
    list_filter = ("task_stage", "id", "copy_first_level", "copy_system_fields")
    search_fields = ("task_stage__name",)
    autocomplete_fields = ("task_stage",)
    list_select_related = (
        "task_stage",
    )

    def get_queryset(self, request):
        queryset = super(ResponseFlattenerAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, 'task_stage__chain__')

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
    autocomplete_fields = ('campaign', )
    exclude = ('user',)

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


class CampaignManagementAdmin(admin.ModelAdmin):
    list_display = ("campaign", "user",)
    search_fields = (
        "user__email",
        "user__phone_number",
        "campaign__name",
        "campaign__description",
    )
    autocomplete_fields = ("user", 'campaign')


class CampaignLinkerAdmin(admin.ModelAdmin):
    list_display = ("name", "out_stage", "target", "created_at", "updated_at",)
    search_fields = ("name", "description", "out_stage",)
    autocomplete_fields = ("out_stage", "stage_with_user", "target",)
    list_filter = (
        "target",
        "out_stage",
        "out_stage__chain",
        "out_stage__chain__campaign",
    )

    def get_queryset(self, request):
        qs = super(CampaignLinkerAdmin, self).get_queryset(request)
        user_admin_pref = request.user.get_admin_preference()
        # filter for autocomplete calls by select2 widget
        if request.path == '/admin/autocomplete/':
            return qs.filter(
                target=user_admin_pref.campaign
            )

        # qs for default changelist calls
        if not user_admin_pref:
            return CampaignLinker.objects.none()
        return qs.filter(
            out_stage__chain__campaign=user_admin_pref.campaign
        )

    def save_model(self, request, obj, form, change):
        is_old = bool(obj.id)
        super().save_model(request, obj, form, change)

        if is_old:
            return

        ApproveLink.objects.create(
            campaign=obj.target,
            linker=obj,
            rank=None,
        )


class ApproveLinkAdmin(admin.ModelAdmin):
    list_display = (
        "linker",
        "rank",
        "approved",
        "notification",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "linker__name",
        "rank__name",
        "task_stage__name",
    )
    autocomplete_fields = (
        "linker",
        "rank",
        "task_stage",
        "notification",
    )
    exclude = ("campaign",)

    def get_queryset(self, request):
        qs = super(ApproveLinkAdmin, self).get_queryset(request)
        return qs.filter(
            campaign=request.user.get_admin_preference().campaign
        )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            # Only set active campaign in admin preference.
            obj.campaign = request.user.get_admin_preference().campaign
        super().save_model(request, obj, form, change)


class DynamicJsonAdmin(admin.ModelAdmin):
    model = DynamicJson
    list_display = ("target", "webhook", "id", "created_at", "updated_at", )
    search_fields = ("target__name", "webhook__url", )
    autocomplete_fields = ("target", "webhook", )
    list_filter = (
        "target",
        "target__chain",
        "target__chain__campaign",
        "webhook",
    )

    def get_queryset(self, request):
        queryset = super(DynamicJsonAdmin, self).get_queryset(request)
        return queryset \
            .filter(
            target__chain__campaign__campaign_managements__user=request.user
        )


class PreviousManualAdmin(admin.ModelAdmin):
    model = PreviousManual
    list_display = ('__str__', 'task_stage_to_assign', 'task_stage_email', 'is_id', 'created_at', 'updated_at', )
    autocomplete_fields = ('task_stage_to_assign', 'task_stage_email',)
    search_fields = ('task_stage_to_assign__name', 'task_stage_email__name', 'field', )
    list_filter = (
        "task_stage_to_assign",
        "task_stage_email",
        "task_stage_email__chain",
        "task_stage_email__chain__campaign",
        "task_stage_to_assign__chain",
        "task_stage_to_assign__chain__campaign",
        "is_id",
    )

    def get_queryset(self, request):
        queryset = super(PreviousManualAdmin, self).get_queryset(request)
        return queryset \
            .filter(
            task_stage_email__chain__campaign__campaign_managements__user=request.user
        )


class NotificationAdmin(admin.ModelAdmin):
    model = Notification
    search_fields = ("title", )
    list_display = ("title", "campaign", "rank", "target_user", "importance", )
    autocomplete_fields = ("campaign", "rank", "target_user")
    readonly_fields = ("sender_task", "receiver_task", "trigger_go",)
    list_filter = (
        "campaign", "rank", "importance"
    )
    list_select_related = (
        "campaign",
        "rank",
        "target_user",
        "sender_task",
        "receiver_task",
    )

    def get_queryset(self, request):
        queryset = super(NotificationAdmin, self).get_queryset(request)
        q = queryset \
            .filter(
            campaign__campaign_managements__user=request.user
        )
        return q

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super(NotificationAdmin, self).get_form(request, obj, **kwargs)

        form.base_fields['campaign'].queryset = Campaign.objects.filter(
            campaign_managements__user=request.user
        )
        form.base_fields['rank'].queryset = Rank.objects.filter(
            track__campaign__campaign_managements__user=request.user
        )

        user_s = obj.target_user if obj else None
        if user_s:
            user_s = CustomUser.objects.filter(id=user_s.id)
        else:
            all_ranks = []
            [all_ranks.extend(track.ranks.values_list('id', flat=True))
             for track in AdminPreference.objects.get(user=request.user).campaign.tracks.all()]
            user_s = CustomUser.objects.filter(
                id__in=RankRecord.objects.filter(
                    rank_id__in=all_ranks
                ).values_list('user_id', flat=True)
            )

        form.base_fields['target_user'].queryset = user_s

        ### Do it because sql query asks all tasks
        # form.base_fields['sender_task'].queryset = Task.objects.filter(
        #     id=obj.sender_task_id) if obj.sender_task else Task.objects.none()
        # form.base_fields['receiver_task'].queryset = Task.objects.filter(
        #     id=obj.receiver_task_id) if obj.receiver_task else Task.objects.none()
        return form


class AutoNotificationAdmin(admin.ModelAdmin):
    model = AutoNotification
    list_display = (
        "trigger_stage",
        "recipient_stage",
        "notification"
    )
    autocomplete_fields = (
        "trigger_stage",
        "recipient_stage",
        "notification",
    )
    search_fields = (
        "notification__title",
        "trigger_stage__name",
        "recipient_stage__name",
    )
    list_filter = (
        "trigger_stage",
        "recipient_stage",
        "trigger_stage__chain",
        "trigger_stage__chain__campaign",
        "recipient_stage__chain",
        "recipient_stage__chain__campaign",
        "go",
        "notification__title",
    )
    list_select_related = (
        "trigger_stage",
        "recipient_stage",
        "trigger_stage__chain",
        "trigger_stage__chain__campaign",
        "recipient_stage__chain",
        "recipient_stage__chain__campaign",
        'notification',
    )

    def get_queryset(self, request):
        queryset = super(AutoNotificationAdmin, self).get_queryset(request)
        return queryset \
            .filter(
            trigger_stage__chain__campaign__campaign_managements__user=request.user
        )


class DatetimeSortAdmin(admin.ModelAdmin):
    model = DatetimeSort
    list_display = ('id',
                    'stage',
                    'start_time',
                    'end_time',
                    'created_at',
                    'updated_at'
                    )
    autocomplete_fields = ('stage', )

    def get_queryset(self, request):
        queryset = super(DatetimeSortAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, 'stage__chain__')


class ErrorItemAdmin(admin.ModelAdmin):
    model = ErrorItem
    list_display = (
        'campaign',
        'group',
        'traceback_info',
        'filename',
        'line',
        'details',
        'data',
        'created_at', )
    list_filter = ('campaign', 'group', )

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        queryset = super(ErrorItemAdmin, self).get_queryset(request).select_related('campaign')
        if request.user.is_superuser:
            return queryset
        return queryset.filter(campaign__in=request.user.managed_campaigns.all())


class TestWebhookAdmin(admin.ModelAdmin):
    model = TestWebhook
    list_display = (
        'id',
        'expected_task',
        'sent_task',
    )
    autocomplete_fields = ('expected_task', 'sent_task')


admin.site.register(Language, LanguageAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Campaign, CampaignAdmin)
admin.site.register(CampaignLinker, CampaignLinkerAdmin)
admin.site.register(ApproveLink, ApproveLinkAdmin)
admin.site.register(Chain, ChainAdmin)
admin.site.register(TaskStage, TaskStageAdmin)
admin.site.register(ConditionalStage, StageAdmin)
admin.site.register(ConditionalLimit, ConditionalLimitAdmin)
admin.site.register(Stage, GeneralStageAdmin)
admin.site.register(Integration, IntegrationAdmin)
admin.site.register(Webhook, WebhookAdmin)
admin.site.register(DynamicJson, DynamicJsonAdmin)
admin.site.register(StagePublisher, IntegrationAdmin)
admin.site.register(CopyField, CopyFieldAdmin)
admin.site.register(Quiz, QuizAdmin)
admin.site.register(Case, CaseAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(Rank, RankAdmin)
admin.site.register(RankLimit, RankLimitAdmin)
admin.site.register(RankRecord, RankRecordAdmin)
admin.site.register(ResponseFlattener, ResponseFlattenerAdmin)
admin.site.register(CampaignManagement, CampaignManagementAdmin)
admin.site.register(TaskAward, TaskAwardAdmin)
admin.site.register(PreviousManual, PreviousManualAdmin)
admin.site.register(Track, TrackAdmin)
admin.site.register(Log, LogAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(AutoNotification, AutoNotificationAdmin)
admin.site.register(NotificationStatus)
admin.site.register(AdminPreference, AdminPreferenceAdmin)
admin.site.register(DatetimeSort, DatetimeSortAdmin)
admin.site.register(ErrorItem, ErrorItemAdmin)
admin.site.register(TestWebhook, TestWebhookAdmin)
