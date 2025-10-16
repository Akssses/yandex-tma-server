from django.urls import path
from . import views

urlpatterns = [
    path('verify-user/', views.verify_user, name='verify_user'),
]
