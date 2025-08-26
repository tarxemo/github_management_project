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

##########################################
# Generate fake commits (>=10 per day)
##########################################

# Number of fake commits to generate
FAKE_COMMITS=$(( RANDOM % 11 + 10 ))

for i in $(seq 1 $FAKE_COMMITS); do
    FAKE_FILE="$PROJECT_DIR/.fake_commit_$i.txt"

    # Create/update a fake file
    echo "Fake commit $i on $DATE" > "$FAKE_FILE"

    # Add + commit
    /usr/bin/git add "$FAKE_FILE" >> "$LOGFILE" 2>&1
    /usr/bin/git commit -m "added new file $i on $DATE" >> "$LOGFILE" 2>&1

    # Delete the file to avoid clutter
    rm "$FAKE_FILE"
    /usr/bin/git add -u >> "$LOGFILE" 2>&1
    /usr/bin/git commit -m "Cleanup fake commit $i on $DATE" >> "$LOGFILE" 2>&1
done

# Push everything
/usr/bin/git push >> "$LOGFILE" 2>&1
