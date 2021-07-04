from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Campaign, Chain, \
    TaskStage, WebHookStage, ConditionalStage, Case, Task, CustomUser


class CustomUserAdmin(UserAdmin):
    model = CustomUser


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Campaign)
admin.site.register(Chain)
admin.site.register(TaskStage)
admin.site.register(WebHookStage)
admin.site.register(ConditionalStage)
admin.site.register(Case)
admin.site.register(Task)
