from django.contrib import admin

from okutool.models import (
    Question,
    QuestionAttachment,
    Stage,
    Task,
    Volume,
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


admin.site.register(Volume)
admin.site.register(Stage, StageAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Task)
