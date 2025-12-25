from django.urls import path
from . import views

urlpatterns = [
    path('transfer', views.transfer, name='transfer'),
]

