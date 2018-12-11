#encoding: utf-8

import json
from datetime import datetime

from django.core.management.base import BaseCommand
from django_redis import get_redis_connection

from webchat.models import Message, User

class Command(BaseCommand):

    def handle(self, *args, **options):
        key_subscribe = 'webchat:all'
        redis_cli = get_redis_connection()
        redis_pubsub = redis_cli.pubsub()
        redis_pubsub.subscribe(key_subscribe)

        for item in redis_pubsub.listen():
            if item['type'] == 'message':
                msg = json.loads(item['data'])
                if msg['type'] != 'msg':
                    continue
                message = Message.objects.create(from_user=User.objects.get(pk=msg['user']['pk']),
                    msg=msg['msg'],
                    create_time=datetime.strptime(msg['date'], '%Y-%m-%d %H:%M:%S')
                )
                print(message)


