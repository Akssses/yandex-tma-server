from django.urls import path
from django.http import JsonResponse
from . import views
from . import api_views

urlpatterns = [
    path('', lambda request: JsonResponse({
        'ok': True,
        'endpoints': {
            'verify_user': '/api/verify-user/',
            'test_status': '/api/test-status/',
            'save_test_result': '/api/save-test-result/',
            'confirm_gift': '/api/confirm-gift/',
            'quiz_status': '/api/quiz-status/',
            'save_quiz_result': '/api/save-quiz-result/',
            'consultations': {
                'topics': '/api/consultations/topics/',
                'slots': '/api/consultations/slots/',
                'book': '/api/consultations/book/<slot_id>/',
                'cancel': '/api/consultations/cancel/<slot_id>/',
                'my': '/api/consultations/my/',
                'expert_schedule': '/api/consultations/expert/schedule/',
            },
            'drf': {
                'users': '/api/drf/users/',
                'test_status': '/api/drf/test-status/',
                'statistics': '/api/drf/statistics/',
                'export_users_to_sheets': '/api/drf/export/users-to-sheets/',
            },
            'docs': '/swagger/'
        }
    })),
    path('verify-user/', views.verify_user, name='verify_user'),
    path('test-status/', views.get_test_status, name='get_test_status'),
    path('save-test-result/', views.save_test_result, name='save_test_result'),
    path('confirm-gift/', views.confirm_gift, name='confirm_gift'),
    path('quiz-status/', views.get_quiz_status, name='get_quiz_status'),
    path('save-quiz-result/', views.save_quiz_result, name='save_quiz_result'),
    # special
    path('special/workshops/', views.list_workshops, name='list_workshops'),
    path('special/my/', views.my_workshop_status, name='my_workshop_status'),
    path('special/register/<int:workshop_id>/', views.register_workshop, name='register_workshop'),
    path('special/cancel/<int:workshop_id>/', views.cancel_workshop, name='cancel_workshop'),
    # consultations
    path('consultations/topics/', views.consultations_topics, name='consultations_topics'),
    path('consultations/slots/', views.consultations_slots, name='consultations_slots'),
    path('consultations/book/<int:slot_id>/', views.consultations_book, name='consultations_book'),
    path('consultations/cancel/<int:slot_id>/', views.consultations_cancel, name='consultations_cancel'),
    path('consultations/my/', views.consultations_my, name='consultations_my'),
    path('consultations/expert/schedule/', views.expert_schedule, name='expert_schedule'),
    # no expert location editing; fixed location used
    
    # DRF API endpoints для Swagger
    path('drf/users/', api_views.api_users_list, name='api_users_list'),
    path('drf/test-status/', api_views.api_test_status, name='api_test_status'),
    path('drf/statistics/', api_views.api_statistics, name='api_statistics'),
    path('drf/export/users-to-sheets/', api_views.export_users_to_sheets, name='export_users_to_sheets'),
]
