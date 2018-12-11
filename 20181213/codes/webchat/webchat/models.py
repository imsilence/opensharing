#encoding: utf-8

from datetime import timedelta
import random
import string
import smtplib

from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist


class User(models.Model):
    email = models.EmailField(max_length=32, null=False, default="", unique=True)
    login_code = models.CharField(max_length=8, null=False, default="")
    login_code_created_time = models.DateTimeField(null=True)
    last_login_time = models.DateTimeField(null=True)

    @classmethod
    def create_login_code(cls, email):
        '''用户信息记录，验证码生成，发送邮件'''
        if email != "":
            user = None

            # 获取用户信息，若以前注册过则获取，否则创建用户信息
            try:
                user = User.objects.get(email=email)
            except ObjectDoesNotExist as e:
                user = User()
                user.email = email
                user.login_code = ""

            # 生成验证码并发送邮件
            if user.login_code == "" or user.login_code_created_time is None \
                or timezone.now() - user.login_code_created_time > timedelta(minutes=5):

                #生成验证码
                user.login_code = ''.join(random.sample(string.digits + string.ascii_letters, 6))
                user.login_code_created_time = timezone.now()

                try:
                    #发送验证码给用户
                    send_mail(
                        '[webchat]登陆验证码',
                        '请使用验证码 {0} 进行登陆，有效时间5分钟'.format(user.login_code),
                        settings.EMAIL_FROM,
                        [email],
                        fail_silently=False,
                    )
                except smtplib.SMTPException as e:
                    return False
                else:
                    # 记录验证码到数据库
                    user.save()
                    return True
            return True
        return False


    @classmethod
    def login(cls, email, login_code):
        '''登陆验证'''
        try:
            #获取用户
            user = User.objects.get(email=email)

            # 验证邮箱，验证码是否正确，同时验证验证码有效时间
            if email != "" and login_code != "" \
                and user.login_code_created_time \
                and login_code.lower() == user.login_code.lower() \
                and timezone.now() - user.login_code_created_time < timedelta(minutes=5):

                # 更新数据库记录
                user.login_code = ""
                user.last_login_time = timezone.now()
                user.save()
                return user
            return None
        except ObjectDoesNotExist as e:
            return None

    def __str__(self):
        return '{0}'.format(self.email)

class Message(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE)
    msg = models.TextField(null=False, default='')
    create_time = models.DateTimeField(null=False)

    def __str__(self):
        return '{0} {1} {2}'.format(self.from_user, self.msg, self.create_time.strftime('%Y-%m-%d %H:%M:%S'))
