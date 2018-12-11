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

    user = request.session.get('user')

    #获取websocket连接对象
    websocket = request.websocket

    key_subscribe = 'webchat:all'
    key_user = 'webchat:users'

    #验证用户是否登陆
    if user is None:
        websocket.send(json.dumps({'code' : 400}))
    else:
        redis_cli = None
        redis_pubsub = None
        try:
            #使用redis发布订阅功能广播消息
            #获取连接
            redis_cli = get_redis_connection()

            redis_cli.publish(key_subscribe, json.dumps({'type' : 'online', 'user' : user, 'date' : timezone.now().strftime('%Y-%m-%d %H:%M:%S')}))

            #订阅消息
            redis_pubsub = redis_cli.pubsub()
            redis_pubsub.subscribe(key_subscribe)

            # 用户上线,更新redis用户信息(在线状态, 上线时间), 广播给所有用户当前上线
            redis_info = redis_cli.hget(key_user, user['pk'])
            redis_info = json.loads(redis_info) if redis_info else {}
            redis_info.update({'pk' : user['pk'], 'email' : user['email'], 'online' : True, 'online_time' : time.time()})
            # 使用map结构存储用户信息, pk : user
            redis_cli.hset(key_user, user['pk'], json.dumps(redis_info))

            # 广播所有用户信息, 更新web页面状态
            users = redis_cli.hgetall(key_user)
            users = [json.loads(user) for user in users.values()]
            users.sort(key=lambda x: (not x['online'], x['pk']))
            redis_cli.publish(key_subscribe, json.dumps({'type' : 'user', 'msg' : users}))

            while True:
                # 获取websocket消息
                ws_message = websocket.read()

                # 获取redis广播消息
                sub_message = redis_pubsub.get_message()

                if ws_message:
                    message = json.loads(ws_message)
                    message['user'] = user
                    message['date'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')

                    # 广播消息
                    redis_cli.publish(key_subscribe, json.dumps(message))

                if sub_message and sub_message['type'] == 'message':
                    # 将redis广播消息发送给浏览器
                    messsage = json.loads(sub_message['data'])
                    messsage['code'] = 200
                    websocket.send(json.dumps(messsage))
        except BaseException as e:
            print(e)
        finally:
            print("close")

            redis_info.update({'pk' : user['pk'], 'email' : user['email'], 'online' : False, 'offline_time' : time.time()})
            # 取消订阅
            if redis_pubsub:
                redis_pubsub.unsubscribe(key_subscribe)

            if redis_cli:
                # 用户下线,更新redis用户信息(在线状态, 离线时间), 广播给所有用户当前下线
                redis_cli.hset(key_user, user['pk'], json.dumps(redis_info))
                redis_cli.publish(key_subscribe, json.dumps({'type' : 'offline', 'user' : user, 'date' : timezone.now().strftime('%Y-%m-%d %H:%M:%S')}))

                # 广播所有用户信息, 更新web页面状态
                users = redis_cli.hgetall(key_user)
                users = [json.loads(user) for user in users.values()]
                users.sort(key=lambda x: (not x['online'], x['pk']))
                redis_cli.publish(key_subscribe, json.dumps({'type' : 'user', 'msg' : users}))




