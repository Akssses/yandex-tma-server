from django.contrib import admin
from .models import TelegramUser, TestResult, Workshop, WorkshopRegistration

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'username', 'email', 'workplace', 'position', 'data_processing_agreement', 'created_at', 'has_completed_test')
    list_filter = ('data_processing_agreement', 'workplace', 'position', 'created_at')
    search_fields = ('first_name', 'last_name', 'username', 'email', 'workplace', 'position')
    readonly_fields = ('first_name', 'last_name', 'username', 'email', 'workplace', 'position', 'data_processing_agreement', 'created_at')
    fields = ('first_name', 'last_name', 'username', 'email', 'workplace', 'position', 'data_processing_agreement', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def has_completed_test(self, obj):
        return obj.has_completed_test()
    has_completed_test.boolean = True
    has_completed_test.short_description = 'Прошел тест'


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'analyst_type', 'analyst_name', 'animal', 'ei_score', 'pj_score', 'gift_received', 'completed_at')
    list_filter = ('analyst_type', 'gift_received', 'completed_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__username', 'analyst_name', 'animal')
    readonly_fields = ('user', 'analyst_type', 'analyst_name', 'animal', 'description', 'tags', 'ei_score', 'pj_score', 'completed_at')
    fields = ('user', 'analyst_type', 'analyst_name', 'animal', 'description', 'tags', 'ei_score', 'pj_score', 'gift_received', 'completed_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True


@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'tag', 'start_time', 'end_time', 'created_at')
    search_fields = ('title', 'tag')
    list_filter = ('start_time', 'end_time', 'created_at')


@admin.register(WorkshopRegistration)
class WorkshopRegistrationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'workshop', 'registered_at')
    list_filter = ('registered_at', 'workshop')
    search_fields = ('user__first_name', 'user__last_name', 'user__username', 'workshop__title')
