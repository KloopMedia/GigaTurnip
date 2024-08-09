from django.contrib import admin

from okutool.models import (
    Question,
    QuestionAttachment,
    Stage,
    StageRelationship,
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


class InStagesInline(admin.TabularInline):
    model = StageRelationship
    extra = 1
    fk_name = "to_stage"


class StageAdmin(admin.ModelAdmin):
    inlines = [InStagesInline, QuestionInline]


admin.site.register(Volume)
admin.site.register(Stage, StageAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Task)
