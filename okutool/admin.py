from django.contrib import admin

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


class StageAdmin(admin.ModelAdmin):
    inlines = [QuestionInline]


admin.site.register(Test)
admin.site.register(Question, QuestionAdmin)
