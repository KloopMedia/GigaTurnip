from django.contrib import admin

from api.admin import TaskAdmin
from api.utils.utils import filter_by_admin_preference
from okutool.models import (
    Question,
    QuestionAttachment,
    Test,
)


class QuestionAttachmentInline(admin.TabularInline):
    model = QuestionAttachment
    extra = 0


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0


class QuestionAdmin(admin.ModelAdmin):
    inlines = [QuestionAttachmentInline]

    def get_queryset(self, request):
        queryset = super(QuestionAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, "test__stage__chain__")


class TestAdmin(admin.ModelAdmin):
    inlines = [QuestionInline]

    def get_queryset(self, request):
        queryset = super(TestAdmin, self).get_queryset(request)
        return filter_by_admin_preference(queryset, request, "stage__chain__")


admin.site.register(Test, TestAdmin)
admin.site.register(Question, QuestionAdmin)
