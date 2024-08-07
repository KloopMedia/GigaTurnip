from django.contrib import admin

from okutool.models import Question, QuestionAttachment, Stage, Volume


class QuestionAttachmentInline(admin.TabularInline):
    model = QuestionAttachment


class QuestionInline(admin.StackedInline):
    model = Question


class QuestionAdmin(admin.ModelAdmin):
    inlines = [QuestionAttachmentInline]


class StageAdmin(admin.ModelAdmin):
    inlines = [QuestionInline]


admin.site.register(Volume)
admin.site.register(Stage, StageAdmin)
admin.site.register(Question, QuestionAdmin)
