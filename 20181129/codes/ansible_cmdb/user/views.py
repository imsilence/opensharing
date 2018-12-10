#encoding: utf-8

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout


def login_view(request):
    username = ''
    errors = None
    if 'POST' == request.method:
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(reverse('host:index'))

        else:
            errors = ['用户名或密码错误']

    return render(request, 'user/login.html', {'username' : username, 'errors' : errors})


def logout_view(request):
    logout(request)
    return redirect(reverse('user:login'))