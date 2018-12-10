#encoding: utf-8

from django.urls import path

from . import views

app_name = 'host'

urlpatterns = [
    path('', views.index, name='index'),
    path('delete/', views.delete, name='delete'),
]