import os

from celery import Celery
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sciarticle.settings')

app = Celery('sciarticle')

app.config_from_object('django.conf:settings', namespace='CELERY')


app.autodiscover_tasks()


app.conf.beat_schedule = {
    'run_every_hour': {  # название задачи
        'task': "bot.tasks.run_check",  # путь к задаче
        'schedule': timedelta(minutes=1),  # каждый час
    },
    'delete_pdf': {
        'task': 'bot.tasks.run_check_and_delete_pdf',
        'schedule': timedelta(minutes=1),  # каждый час
    },
    'delete_thank_message': {
        'task': 'bot.tasks.run_check_and_delete_thank_message',
        'schedule': timedelta(minutes=1),  # каждые 20 минут
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
