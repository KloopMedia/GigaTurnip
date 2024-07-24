from django.contrib import admin

from dictionary.models import Category, ProficiencyLevel, Word

admin.site.register(Word)
admin.site.register(ProficiencyLevel)
admin.site.register(Category)
