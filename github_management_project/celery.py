# github_management_project/celery.py
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'github_management_project.settings')

app = Celery('github_management_project')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs
app.autodiscover_tasks()

# Configure beat schedule
app.conf.beat_schedule = {
    'update-github-stats': {
        'task': 'github_management.tasks.update_github_stats',
        'schedule': crontab(hour=0, minute=0),
    },
}
app.conf.timezone = 'UTC'

# This will make sure the app is always imported when Django starts
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')