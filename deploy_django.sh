#!/bin/bash

# Django EC2 Auto-Deployment Script with Nginx & SSL
# This script automates the complete deployment of a Django application

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_step() {
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}\n"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "Please run this script as root or with sudo"
    exit 1
fi

# Welcome message
clear
echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════════╗
║   Django EC2 Deployment Automation Script         ║
║   Nginx + Gunicorn + SSL + Domain Configuration   ║
╚═══════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Interactive prompts
print_step "STEP 1: Gathering Configuration Information"

read -p "Enter your main domain name (e.g., example.com): " DOMAIN_NAME
read -p "Enter subdomains (space-separated, e.g., api app www): " SUBDOMAINS_INPUT
read -p "Enter your email for SSL certificate (Let's Encrypt): " SSL_EMAIL
read -p "Enter the path to your Django project directory (e.g., /home/ubuntu/myproject): " PROJECT_PATH
read -p "Enter your Django project name (the folder containing settings.py): " PROJECT_NAME
read -p "Enter the system user to run the application (default: ubuntu): " APP_USER
APP_USER=${APP_USER:-ubuntu}
read -p "Do you want to set up HTTPS with Let's Encrypt? (y/n, default: y): " SETUP_SSL
SETUP_SSL=${SETUP_SSL:-y}

# Set default Python version
PYTHON_VERSION=python3

# Process subdomains
SUBDOMAINS=($SUBDOMAINS_INPUT)
DOMAINS="$DOMAIN_NAME"
for sub in "${SUBDOMAINS[@]}"; do
    if [ -n "$sub" ]; then
        DOMAINS+=" $sub.$DOMAIN_NAME"
    fi
done

# Add www if not already included
if [[ ! " ${SUBDOMAINS[@]} " =~ " www " ]]; then
    DOMAINS+=" www.$DOMAIN_NAME"
fi

# Create a comma-separated list for Django ALLOWED_HOSTS
ALLOWED_HOSTS="'$DOMAIN_NAME', 'www.$DOMAIN_NAME'"
for sub in "${SUBDOMAINS[@]}"; do
    if [ -n "$sub" ]; then
        ALLOWED_HOSTS+=", '$sub.$DOMAIN_NAME'"
    fi
done

# Verify project path exists
if [ ! -d "$PROJECT_PATH" ]; then
    print_error "Project directory $PROJECT_PATH does not exist!"
    exit 1
fi

# Verify settings.py exists
if [ ! -f "$PROJECT_PATH/$PROJECT_NAME/settings.py" ]; then
    print_error "Django settings.py not found at $PROJECT_PATH/$PROJECT_NAME/settings.py"
    exit 1
fi

print_message "Configuration collected successfully!"

# Summary
print_step "Configuration Summary"
echo "Domain Name: $DOMAIN_NAME"
echo "SSL Email: $SSL_EMAIL"
echo "Project Path: $PROJECT_PATH"
echo "Project Name: $PROJECT_NAME"
echo "App User: $APP_USER"
echo "Setup SSL: $SETUP_SSL"
echo ""
read -p "Continue with these settings? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    print_error "Deployment cancelled by user"
    exit 1
fi

# Update system
print_step "STEP 2: Updating System Packages"
apt-get update -y
apt-get upgrade -y

# Install required packages
print_step "STEP 3: Installing Required Packages"
apt-get install -y nginx postgresql postgresql-contrib libpq-dev \
    build-essential git curl software-properties-common

# Create virtual environment
print_step "STEP 4: Setting Up Python Virtual Environment"
VENV_PATH="$PROJECT_PATH/venv"
if [ ! -d "$VENV_PATH" ]; then
    print_message "Creating virtual environment..."
    python3 -m venv $VENV_PATH
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
print_message "Installing Python dependencies..."
source $VENV_PATH/bin/activate
pip install --upgrade pip
pip install gunicorn

# Check for requirements.txt
if [ -f "$PROJECT_PATH/requirements.txt" ]; then
    print_message "Installing from requirements.txt..."
    pip install -r $PROJECT_PATH/requirements.txt
else
    print_warning "requirements.txt not found. Installing essential packages..."
    pip install django gunicorn psycopg2-binary python-decouple
fi

# Create necessary directories
print_step "STEP 5: Setting Up Directories and Permissions"
mkdir -p $PROJECT_PATH/static
mkdir -p $PROJECT_PATH/media
mkdir -p $PROJECT_PATH/logs

# Collect static files
print_message "Collecting static files..."
cd $PROJECT_PATH
python manage.py collectstatic --noinput || print_warning "Static files collection failed or not configured"

# Set proper permissions
print_message "Setting file permissions..."
chown -R $APP_USER:www-data $PROJECT_PATH
chmod -R 755 $PROJECT_PATH
chmod -R 775 $PROJECT_PATH/static
chmod -R 775 $PROJECT_PATH/media
chmod -R 775 $PROJECT_PATH/logs

# Create Gunicorn systemd service
print_step "STEP 6: Creating Gunicorn Service"
GUNICORN_SERVICE="/etc/systemd/system/gunicorn.service"

cat > $GUNICORN_SERVICE << EOF
[Unit]
Description=Gunicorn daemon for Django project
After=network.target

[Service]
User=$APP_USER
Group=www-data
WorkingDirectory=$PROJECT_PATH
Environment="PATH=$VENV_PATH/bin"
ExecStart=$VENV_PATH/bin/gunicorn \\
    --workers 3 \\
    --bind unix:$PROJECT_PATH/gunicorn.sock \\
    --access-logfile $PROJECT_PATH/logs/gunicorn-access.log \\
    --error-logfile $PROJECT_PATH/logs/gunicorn-error.log \\
    --log-level info \\
    $PROJECT_NAME.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

print_message "Gunicorn service file created"

# Create Gunicorn socket
GUNICORN_SOCKET="/etc/systemd/system/gunicorn.socket"

cat > $GUNICORN_SOCKET << EOF
[Unit]
Description=Gunicorn socket

[Socket]
ListenStream=$PROJECT_PATH/gunicorn.sock

[Install]
WantedBy=sockets.target
EOF

print_message "Gunicorn socket file created"

# Start Gunicorn
print_message "Starting Gunicorn service..."
systemctl daemon-reload
systemctl start gunicorn.socket
systemctl enable gunicorn.socket
systemctl restart gunicorn

# Check Gunicorn status
if systemctl is-active --quiet gunicorn; then
    print_message "Gunicorn is running successfully!"
else
    print_error "Gunicorn failed to start. Check logs with: journalctl -u gunicorn"
fi

# Configure Celery service
print_step "Configuring Celery Service"
CELERY_SERVICE="/etc/systemd/system/celery.service"
CELERY_BEAT_SERVICE="/etc/systemd/system/celery-beat.service"
CELERY_WORKER_SERVICE="/etc/systemd/system/celery-worker.service"

# Create Celery service file
cat > $CELERY_SERVICE << EOF
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=forking
User=$APP_USER
Group=www-data
EnvironmentFile=$PROJECT_PATH/.env
WorkingDirectory=$PROJECT_PATH
ExecStart=$VENV_PATH/bin/celery -A $PROJECT_NAME worker --loglevel=info --logfile=$PROJECT_PATH/logs/celery_worker.log --pidfile=/tmp/celery_worker.pid --detach
ExecStop=/bin/pkill -f "celery worker"
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

# Create Celery Beat service file
cat > $CELERY_BEAT_SERVICE << EOF
[Unit]
Description=Celery Beat Service
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=www-data
EnvironmentFile=$PROJECT_PATH/.env
WorkingDirectory=$PROJECT_PATH
ExecStart=$VENV_PATH/bin/celery -A $PROJECT_NAME beat --loglevel=info --logfile=$PROJECT_PATH/logs/celery_beat.log --pidfile=/tmp/celery_beat.pid --scheduler django_celery_beat.schedulers:DatabaseScheduler
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

# Create Celery Worker service file
cat > $CELERY_WORKER_SERVICE << EOF
[Unit]
Description=Celery Worker Service
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=www-data
EnvironmentFile=$PROJECT_PATH/.env
WorkingDirectory=$PROJECT_PATH
ExecStart=$VENV_PATH/bin/celery -A $PROJECT_NAME worker --loglevel=info --logfile=$PROJECT_PATH/logs/celery_worker.log
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

# Set permissions and enable services
chmod 644 $CELERY_SERVICE $CELERY_BEAT_SERVICE $CELERY_WORKER_SERVICE
systemctl daemon-reload

# Start and enable Celery services
for service in celery celery-beat celery-worker; do
    if systemctl is-enabled $service >/dev/null 2>&1; then
        systemctl restart $service
    else
        systemctl enable --now $service
    fi
    
    if systemctl is-active --quiet $service; then
        print_message "$service is running successfully!"
    else
        print_error "Failed to start $service. Check logs with: journalctl -u $service"
    fi
done

# Configure Nginx
print_step "STEP 7: Configuring Nginx"
NGINX_CONF="/etc/nginx/sites-available/$DOMAIN_NAME"

# Create Nginx configuration with all domains
cat > $NGINX_CONF << EOF
# Main server block that redirects HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAINS;
    return 301 https://\$host\$request_uri;
}

# Main HTTPS server block
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAINS;
    
    # SSL configuration will be managed by certbot
    ssl_certificate /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    
    client_max_body_size 100M;
    
    access_log $PROJECT_PATH/logs/nginx-access.log;
    error_log $PROJECT_PATH/logs/nginx-error.log;

    location = /favicon.ico { 
        access_log off; 
        log_not_found off; 
    }
    
    location /static/ {
        alias $PROJECT_PATH/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias $PROJECT_PATH/media/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$PROJECT_PATH/gunicorn.sock;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Host \$host;
        proxy_redirect off;
    }
}
EOF

# Enable Nginx site
ln -sf $NGINX_CONF /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
print_message "Testing Nginx configuration..."
if nginx -t; then
    print_message "Nginx configuration is valid"
    systemctl restart nginx
    systemctl enable nginx
else
    print_error "Nginx configuration test failed!"
    exit 1
fi

# Setup SSL with Let's Encrypt
if [ "$SETUP_SSL" = "y" ] || [ "$SETUP_SSL" = "Y" ]; then
    print_step "STEP 8: Setting Up SSL Certificate (Let's Encrypt)"
    
    # Install Certbot
    apt-get install -y certbot python3-certbot-nginx
    
    # Prepare the certbot command with all domains
    CERTBOT_CMD="certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME"
    for sub in "${SUBDOMAINS[@]}"; do
        if [ -n "$sub" ]; then
            CERTBOT_CMD+=" -d $sub.$DOMAIN_NAME"
        fi
    done
    
    print_message "Obtaining SSL certificate for: $DOMAINS"
    $CERTBOT_CMD --non-interactive --agree-tos --email $SSL_EMAIL --redirect
    
    if [ $? -eq 0 ]; then
        print_message "SSL certificate installed successfully!"
        
        # Setup auto-renewal
        systemctl enable certbot.timer
        systemctl start certbot.timer
        print_message "SSL auto-renewal configured"
        
        # Update Django's ALLOWED_HOSTS
        print_message "Updating Django ALLOWED_HOSTS..."
        SETTINGS_FILE="$PROJECT_PATH/$PROJECT_NAME/settings.py"
        if [ -f "$SETTINGS_FILE" ]; then
            # Remove any existing ALLOWED_HOSTS line
            sed -i '/^ALLOWED_HOSTS/d' "$SETTINGS_FILE"
            # Add the new ALLOWED_HOSTS
            echo "ALLOWED_HOSTS = [$ALLOWED_HOSTS]" >> "$SETTINGS_FILE"
            print_message "Updated ALLOWED_HOSTS in Django settings"
        fi
    else
        print_warning "SSL certificate installation failed. You can run it manually later with:"
        echo "$CERTBOT_CMD"
    fi
else
    print_warning "Skipping SSL setup. Your site will use HTTP only."
fi

# Configure firewall
print_step "STEP 9: Configuring Firewall"
if command -v ufw &> /dev/null; then
    print_message "Configuring UFW firewall..."
    ufw allow 'Nginx Full'
    ufw allow OpenSSH
    ufw --force enable
    print_message "Firewall configured"
else
    print_warning "UFW not found. Please configure your firewall manually to allow ports 80 and 443"
fi

# Create management script
print_step "STEP 10: Creating Management Scripts"
MANAGE_SCRIPT="$PROJECT_PATH/manage-app.sh"

cat > $MANAGE_SCRIPT << 'EOFSCRIPT'
#!/bin/bash

# Management script for Django application

case "$1" in
    start)
        echo "Starting application..."
        sudo systemctl start gunicorn
        sudo systemctl start nginx
        echo "Application started"
        ;;
    stop)
        echo "Stopping application..."
        sudo systemctl stop gunicorn
        sudo systemctl stop nginx
        echo "Application stopped"
        ;;
    restart)
        echo "Restarting application..."
        sudo systemctl restart gunicorn
        sudo systemctl restart nginx
        echo "Application restarted"
        ;;
    status)
        echo "=== Gunicorn Status ==="
        sudo systemctl status gunicorn --no-pager
        echo ""
        echo "=== Nginx Status ==="
        sudo systemctl status nginx --no-pager
        ;;
    logs)
        echo "=== Gunicorn Logs ==="
        sudo journalctl -u gunicorn -n 50 --no-pager
        ;;
    update)
        echo "Updating application..."
        cd PROJECT_PATH_PLACEHOLDER
        git pull
        source venv/bin/activate
        pip install -r requirements.txt
        python manage.py migrate
        python manage.py collectstatic --noinput
        sudo systemctl restart gunicorn
        echo "Application updated"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|update}"
        exit 1
        ;;
esac
EOFSCRIPT

sed -i "s|PROJECT_PATH_PLACEHOLDER|$PROJECT_PATH|g" $MANAGE_SCRIPT
chmod +x $MANAGE_SCRIPT
chown $APP_USER:$APP_USER $MANAGE_SCRIPT

print_message "Management script created at $MANAGE_SCRIPT"

# Final verification
print_step "STEP 11: Final Verification"

echo "Checking services..."
SERVICES_OK=true

if systemctl is-active --quiet gunicorn; then
    echo -e "${GREEN}✓${NC} Gunicorn is running"
else
    echo -e "${RED}✗${NC} Gunicorn is not running"
    SERVICES_OK=false
fi

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓${NC} Nginx is running"
else
    echo -e "${RED}✗${NC} Nginx is not running"
    SERVICES_OK=false
fi

# Display summary
print_step "Deployment Complete!"

cat << EOF

${GREEN}╔═══════════════════════════════════════════════════╗
║           Deployment Summary                       ║
╚═══════════════════════════════════════════════════╝${NC}

${GREEN}✓${NC} Your Django application is now deployed!

Domain: http://$DOMAIN_NAME
$([ "$SETUP_SSL" = "y" ] && echo "HTTPS: https://$DOMAIN_NAME")

Important Files and Locations:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Project Path: $PROJECT_PATH
  • Virtual Environment: $VENV_PATH
  • Gunicorn Socket: $PROJECT_PATH/gunicorn.sock
  • Nginx Config: $NGINX_CONF
  • Logs Directory: $PROJECT_PATH/logs
  • Static Files: $PROJECT_PATH/static
  • Media Files: $PROJECT_PATH/media
  • Management Script: $MANAGE_SCRIPT

Useful Commands:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Restart app: sudo systemctl restart gunicorn
  • Restart nginx: sudo systemctl restart nginx
  • View logs: sudo journalctl -u gunicorn -f
  • Check status: sudo systemctl status gunicorn
  • Manage app: $MANAGE_SCRIPT {start|stop|restart|status|logs|update}

Next Steps:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Update your DNS settings to point to this server's IP
  2. Configure your Django ALLOWED_HOSTS in settings.py:
     ALLOWED_HOSTS = ['$DOMAIN_NAME', 'www.$DOMAIN_NAME']
  3. Set DEBUG = False in production
  4. Configure your database settings
  5. Run migrations: cd $PROJECT_PATH && source venv/bin/activate && python manage.py migrate

$(if [ "$SERVICES_OK" = false ]; then
    echo -e "${YELLOW}⚠ Warning: Some services are not running properly."
    echo -e "   Check the logs with: sudo journalctl -u gunicorn -n 50${NC}"
fi)

${GREEN}Happy deploying! 🚀${NC}

EOF

deactivate 2>/dev/null || true

exit 0