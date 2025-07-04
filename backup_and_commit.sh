#!/bin/bash

# Set to fail on errors
set -e

# Variables
DATE=$(date +%Y-%m-%d)
PROJECT_DIR="/home/ubuntu/RB"
VENV_PYTHON="/home/ubuntu/venv/bin/python3"
DB_BACKUP_PATH="$PROJECT_DIR/db_backup_${DATE}.dump"
LOGFILE="$PROJECT_DIR/cron.log"

# Change to project directory
cd "$PROJECT_DIR" || exit 1

# Backup database
/usr/bin/pg_dump -h localhost -U tarxemo -F c -f "$DB_BACKUP_PATH" leo >> "$LOGFILE" 2>&1

# Run Django management command using venv Python
"$VENV_PYTHON" manage.py update_chicken_age >> "$LOGFILE" 2>&1

# Git operations
/usr/bin/git add . >> "$LOGFILE" 2>&1
/usr/bin/git commit -m "Automated backup and update at $DATE" >> "$LOGFILE" 2>&1 || echo "No changes to commit" >> "$LOGFILE"
/usr/bin/git pull --no-edit >> "$LOGFILE" 2>&1
/usr/bin/git add . >> "$LOGFILE" 2>&1
/usr/bin/git commit -m "Post-pull commit at $DATE" >> "$LOGFILE" 2>&1 || echo "No post-pull changes to commit" >> "$LOGFILE"
/usr/bin/git push >> "$LOGFILE" 2>&1
