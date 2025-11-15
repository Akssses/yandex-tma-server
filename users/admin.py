from django.contrib import admin
from .models import (
    TelegramUser,
    TestResult,
    QuizResult,
    Workshop,
    WorkshopRegistration,
    ConsultationTopic,
    ConsultationSlot,
    TopicTimeSlot,
)

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'telegram_id', 'first_name', 'last_name', 'username', 'email', 'workplace', 'position', 'is_expert', 'data_processing_agreement', 'created_at', 'has_completed_test', 'has_completed_quiz')
    list_filter = ('is_expert', 'data_processing_agreement', 'workplace', 'position', 'created_at')
    search_fields = ('first_name', 'last_name', 'username', 'email', 'workplace', 'position', 'telegram_id')
    readonly_fields = ('created_at',)
    fields = ('telegram_id', 'first_name', 'last_name', 'username', 'email', 'workplace', 'position', 'is_expert', 'data_processing_agreement', 'created_at')

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def has_completed_test(self, obj):
        return obj.has_completed_test()
    has_completed_test.boolean = True
    has_completed_test.short_description = 'Прошел тест'

    def has_completed_quiz(self, obj):
        return obj.has_completed_quiz()
    has_completed_quiz.boolean = True
    has_completed_quiz.short_description = 'Прошел квиз'


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


@admin.register(QuizResult)
class QuizResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'quiz_date', 'correct_answers', 'total_questions', 'score_percentage', 'completed_at')
    list_filter = ('quiz_date', 'completed_at', 'correct_answers', 'total_questions')
    search_fields = ('user__first_name', 'user__last_name', 'user__username')
    readonly_fields = ('user', 'quiz_date', 'correct_answers', 'total_questions', 'answers', 'completed_at')
    fields = ('user', 'quiz_date', 'correct_answers', 'total_questions', 'answers', 'completed_at')
    ordering = ('-quiz_date', '-correct_answers', '-completed_at')

    def score_percentage(self, obj):
        if obj.total_questions > 0:
            return f"{(obj.correct_answers / obj.total_questions * 100):.1f}%"
        return "0%"
    score_percentage.short_description = 'Процент правильных'

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


class TopicTimeSlotInline(admin.StackedInline):
    model = TopicTimeSlot
    extra = 1
    filter_horizontal = ('experts',)
    fields = ('start_time', 'end_time', 'experts')


@admin.register(ConsultationTopic)
class ConsultationTopicAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    filter_horizontal = ('experts',)
    inlines = [TopicTimeSlotInline]


@admin.register(ConsultationSlot)
class ConsultationSlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'expert', 'topic', 'start_time', 'end_time', 'is_booked', 'booked_by', 'template')
    list_filter = ('is_booked', 'topic', 'expert', 'start_time')
    search_fields = ('expert__first_name', 'expert__last_name', 'topic__name', 'booked_by__first_name', 'booked_by__last_name')
    readonly_fields = ('expert', 'topic', 'start_time', 'end_time', 'is_booked', 'booked_by', 'created_at', 'template')

    def has_add_permission(self, request):
        # Slots are generated in code and created only upon booking
        return False
