from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Campaign, Chain, \
    TaskStage, ConditionalStage, Case, Task, CustomUser, Rank, RankLimit, RankRecord, CampaignManagement, Track


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
                    'assignee', )
    list_filter = ('stage__chain__campaign',
                   'stage__chain',
                   'stage', )
    search_fields = ('id',
                     'case__id',
                     'stage__name',
                     'assignee__email',
                     'stage__chain__name',
                     'stage__chain__campaign__name')
    autocomplete_fields = ('in_tasks', )
    raw_id_fields = ('stage', 'assignee', 'case', )


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
