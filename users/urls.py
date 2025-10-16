from django.urls import path
from . import views

urlpatterns = [
    path('verify-user/', views.verify_user, name='verify_user'),
    path('test-status/', views.get_test_status, name='get_test_status'),
    path('save-test-result/', views.save_test_result, name='save_test_result'),
    path('confirm-gift/', views.confirm_gift, name='confirm_gift'),
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
]
