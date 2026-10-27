from django.contrib import admin
from .models import Subject, Assignment


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'course_code', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('name', 'course_code', 'user__username')
    ordering = ('name',)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'user', 'due_date', 'priority', 'status', 'is_overdue')
    list_filter = ('status', 'priority', 'due_date', 'subject', 'user')
    search_fields = ('title', 'description', 'subject__name', 'user__username')
    ordering = ('due_date',)
    date_hierarchy = 'due_date'
