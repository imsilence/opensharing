#encoding: utf-8

from django.urls import path

from . import views

app_name = 'user'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login2'),
    path('logout/', views.logout_view, name='logout'),
]