#encoding: utf-8

import time
import json
import uuid

from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone

from django_redis import get_redis_connection

from dwebsocket import require_websocket
from .models import User, Message


def login(request):
    '''用户登录'''
    # 检查用户是否已经登陆，如果已经登陆则跳转到首页
    if request.session.get("user"):
        return redirect(reverse("index"))

    if request.method == 'GET':
        # 若为GET请求则为打开登陆页面
        return render(request, 'login.html')

    elif request.method == 'POST':
        # 若为POST请求则为用户登陆
        # 获取邮箱和登陆验证码
        email = request.POST.get("email", "").strip()
        login_code = request.POST.get("login_code", "").strip()
        errors = []

        # 比较用户邮箱和登陆验证码
        user = User.login(email, login_code)
        if user:
            # 用户登录成功，记录session信息
            request.session['user'] = {'email' : user.email, 'pk' : user.id}
            return JsonResponse({"code" : 200})
        else:
            return JsonResponse({"code" : 400})


def login_code(request):
    '''登陆验证码获取'''
    email = request.POST.get("email", "").strip()
    code = 200 if User.create_login_code(email) else 400
    return JsonResponse({"code" : code})


def logout(request):
    '''退出登录'''
    request.session.flush()
    return redirect(reverse('index'))


def index(request):
    '''聊天页面'''
    if request.session.get('user') is None:
        return redirect(reverse('login'))

    return render(request, 'index.html')


#使用dwebsocket提供的装饰器修饰函数，只接收websocket请求
@require_websocket
def msg(request):
    '''websocket消息处理'''
    key_subscribe = 'webchat:all'

    websocket = request.websocket #获取websocket连接对象
    user = request.session.get('user')

    #验证用户是否登陆
    if user is None:
        websocket.send(json.dumps({'code' : 400}))
    else:
        redis_cli = None
        redis_pubsub = None
        try:
            #使用redis发布订阅功能广播消息
            redis_cli = get_redis_connection() #获取redis连接
            redis_pubsub = redis_cli.pubsub()
            redis_pubsub.subscribe(key_subscribe)  #订阅消息

            _online_offline(redis_cli, user, 'online') #在线
            msgs = list(Message.objects.order_by('-create_time')[:10])
            msgs.reverse()
            for msg in msgs:
                message = {}
                message['user'] = {'pk' : msg.from_user.pk, 'email' : msg.from_user.email}
                message['date'] = msg.create_time.strftime('%Y-%m-%d %H:%M:%S')
                message['msg'] = msg.msg
                message['type'] = 'msg'
                message['code'] = 200
                websocket.send(json.dumps(message))

            while True:
                ws_message = websocket.read() # 获取websocket消息
                sub_message = redis_pubsub.get_message() # 获取redis广播消息

                if ws_message:
                    message = json.loads(ws_message)
                    message['user'] = user
                    message['date'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                    redis_cli.publish(key_subscribe, json.dumps(message)) # 广播消息

                if sub_message and sub_message['type'] == 'message':
                    messsage = json.loads(sub_message['data'])
                    messsage['code'] = 200
                    websocket.send(json.dumps(messsage)) # 将redis广播消息发送给浏览器
        finally:
            if redis_pubsub:
                redis_pubsub.unsubscribe(key_subscribe) # 取消订阅

            if redis_cli:
                _online_offline(redis_cli, user, 'offline') #离线



def _online_offline(redis_cli, user, stype='online'):
    '''用户/离线数据更新&消息广播'''
    key_user = 'webchat:users'
    key_subscribe = 'webchat:all'

    # 用户上线/下线更新redis用户信息(在线状态, 上线和离线时间)
    redis_cli.publish(key_subscribe, json.dumps({'type' : stype, 'user' : user}))

    # 使用map结构存储用户信息, pk : user
    redis_info = redis_cli.hget(key_user, user['pk'])
    redis_info = json.loads(redis_info) if redis_info else {}
    redis_info.update({'pk' : user['pk'], 'email' : user['email']})

    if stype == 'online':
        redis_info.update({'online' : True, 'online_time' : time.time()})
    else:
        redis_info.update({'online' : False, 'offline_time' : time.time()})

    # 更新redis数据
    redis_cli.hset(key_user, user['pk'], json.dumps(redis_info))

    # 广播所有用户信息, 更新web页面状态
    users = redis_cli.hgetall(key_user)
    users = [json.loads(user) for user in users.values()]
    users.sort(key=lambda x: (not x['online'], x['pk']))
    redis_cli.publish(key_subscribe, json.dumps({'type' : 'user', 'msg' : users}))
