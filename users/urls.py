from django.urls import path
from . import views

urlpatterns = [
    path('verify-user/', views.verify_user, name='verify_user'),
    path('test-status/', views.get_test_status, name='get_test_status'),
    path('save-test-result/', views.save_test_result, name='save_test_result'),
    path('confirm-gift/', views.confirm_gift, name='confirm_gift'),
]
