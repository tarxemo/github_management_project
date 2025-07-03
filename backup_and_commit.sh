#!/bin/bash

# Navigate to project directory
cd /home/ubuntu/RB || exit

# Export database to backup file
PGPASSWORD='@SuperCoder' pg_dump -U postgres leo > db_backup_$(date +%Y-%m-%d).sql

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
