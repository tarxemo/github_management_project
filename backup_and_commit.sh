#!/bin/bash

# Navigate to project directory
cd /home/ubuntu/RB || exit

# Export database to backup file
pg_dump -h localhost -U tarxemo -F c -f db_backup_$(date +%Y-%m-%d).dump leo

# Run Django management command
source /home/ubuntu/venv/bin/activate
python3 manage.py update_chicken_age

# Git operations
git add .
git commit -m "commit from server commiting database backup"
git pull --no-edit
git add .
git commit -m "commit from server commiting database backup after conflicts"
git push
