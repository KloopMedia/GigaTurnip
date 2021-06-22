from django.contrib import admin
from .models import Campaign, Chain, \
    TaskStage, WebHookStage, ConditionalStage, Case, Task

admin.site.register(Campaign)
admin.site.register(Chain)
admin.site.register(TaskStage)
admin.site.register(WebHookStage)
admin.site.register(ConditionalStage)
admin.site.register(Case)
admin.site.register(Task)