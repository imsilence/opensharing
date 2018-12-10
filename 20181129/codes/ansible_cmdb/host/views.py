#encoding: utf-8

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required

from .models import Host

@login_required
def index(request):
    return render(request, 'host/index.html', {'objects' : Host.objects.all()})


@login_required
def delete(request):
    pk = request.GET.get("pk", 0)
    Host.objects.filter(pk=pk).delete()
    return redirect(reverse('host:index'))