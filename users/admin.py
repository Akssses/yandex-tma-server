from django.contrib import admin
from .models import TelegramUser

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'username', 'email', 'workplace', 'position', 'data_processing_agreement', 'created_at')
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
