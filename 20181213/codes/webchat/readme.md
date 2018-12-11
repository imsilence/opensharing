部署:
1. python -m venv venv
2. source venv/bin/activate
3. pip install -r requirements.txt
4. python manage.py makemigrations
5. python manage.py migrate
6. python manage.py collectstatic
7. gunicorn -w 5 -k gevent -b 0.0.0.0:9990 webchat.wsgi
6. python manage.py msg

知识点:
1. websocket
2. django
3. dwebsocket
4. send_mail
5. random.sample + string.digits + string.ascii_letters
6. redis 发布订阅
7. 前端安全性xss, HTMLEncode, JSEncode