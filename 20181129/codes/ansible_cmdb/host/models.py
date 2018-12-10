#encoding: utf-8

from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from datetime import timedelta

class Host(models.Model):
    name = models.CharField(verbose_name='主机名', max_length=256, default='', null=False)
    os = models.CharField(verbose_name='操作系统', max_length=256, default='', null=False)
    ip = models.GenericIPAddressField(verbose_name='IP地址')
    arch = models.CharField(verbose_name='架构', max_length=32, default='', null=False)
    mem = models.BigIntegerField(verbose_name='内存', default=0, null=False)
    cpu = models.IntegerField(verbose_name='CPU', default=0, null=False)
    remark = models.TextField(verbose_name='备注', default='', blank=True)
    created_time = models.DateTimeField(verbose_name='发现时间', auto_now_add=True, null=False)
    last_time = models.DateTimeField(verbose_name='最后发现时间', auto_now=True, null=False)

    def is_online(self):
        return timezone.now() - self.last_time < timedelta(hours=6)

    @classmethod
    def create_or_replace(cls, name, ip, arch, os, mem, cpu):
        obj = None
        try:
            obj = Host.objects.get(ip=ip)
        except ObjectDoesNotExist as e:
            obj = Host()
            obj.ip = ip
        obj.name = name
        obj.arch = arch
        obj.os = os
        obj.mem = mem
        obj.cpu = cpu

        obj.save()
        return obj

    def __str__(self):
        return '{0}({1})'.format(self.name, self.ip)