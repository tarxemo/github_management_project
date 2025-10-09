import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'github_management_project.settings')

app = Celery('github_management_project')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs
app.autodiscover_tasks()

# This will make sure the app is always imported when Django starts
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# Remove the explicit import to avoid circular imports
# Tasks will be discovered by autodiscover_tasks()