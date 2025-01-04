from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shop_vivu.settings')
app = Celery('shop_vivu')
app.conf.update(
    worker_pool='solo',
)
# Khởi tạo Django trước khi sử dụng mô hình
import django
django.setup()
# Sử dụng redis làm message broker
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
app.conf.broker_connection_retry_on_startup = True
from recommendation import tasks
app.autodiscover_tasks(lambda: ['recommendation'])