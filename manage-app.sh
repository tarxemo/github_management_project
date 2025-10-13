#!/bin/bash

# Management script for Django application
PROJECT_PATH="/home/ubuntu/github_management/RB"

case "$1" in
    start)
        echo "Starting application..."
        sudo systemctl start gunicorn
        sudo systemctl start celery
        sudo systemctl start celery-beat
        sudo systemctl start nginx
        echo "Application started"
        ;;
    stop)
        echo "Stopping application..."
        sudo systemctl stop gunicorn
        sudo systemctl stop celery
        sudo systemctl stop celery-beat
        sudo systemctl stop nginx
        echo "Application stopped"
        ;;
    restart)
        echo "Restarting application..."
        sudo systemctl restart gunicorn
        sudo systemctl restart celery
        sudo systemctl restart celery-beat
        sudo systemctl restart nginx
        echo "Application restarted"
        ;;
    status)
        echo "=== Gunicorn Status ==="
        sudo systemctl status gunicorn --no-pager
        echo ""
        echo "=== Celery Status ==="
        sudo systemctl status celery --no-pager
        echo ""
        echo "=== Celery Beat Status ==="
        sudo systemctl status celery-beat --no-pager
        echo ""
        echo "=== Nginx Status ==="
        sudo systemctl status nginx --no-pager
        ;;
    logs)
        echo "=== Gunicorn Logs ==="
        sudo journalctl -u gunicorn -n 50 --no-pager
        echo ""
        echo "=== Celery Logs ==="
        sudo journalctl -u celery -n 50 --no-pager
        ;;
    update)
        echo "Updating application..."
        cd $PROJECT_PATH
        git pull
        source venv/bin/activate
        pip install -r requirements.txt
        python manage.py migrate
        python manage.py collectstatic --noinput
        deactivate
        sudo systemctl restart gunicorn
        sudo systemctl restart celery
        sudo systemctl restart celery-beat
        echo "Application updated"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|update}"
        exit 1
        ;;
esac
