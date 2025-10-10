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
apt-get install -y redis-server
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

# Create directories for Celery
CELERY_LOG_DIR="/var/log/celery"
CELERY_RUN_DIR="/var/run/celery"
CELERY_CONF_DIR="/etc/conf.d"
mkdir -p $CELERY_LOG_DIR $CELERY_RUN_DIR $CELERY_CONF_DIR
chown -R $APP_USER:www-data $CELERY_LOG_DIR $CELERY_RUN_DIR
chmod -R 755 $CELERY_LOG_DIR $CELERY_RUN_DIR

# Create Celery configuration
cat > $CELERY_CONF_DIR/celery << EOF
# Name of nodes to start
CELERYD_NODES="worker1"

# Absolute or relative path to the 'celery' command
CELERY_BIN="$VENV_PATH/bin/celery"

# App instance to use
CELERY_APP="$PROJECT_NAME"

# How to call manage.py
CELERYD_MULTI="multi"

# Extra command-line arguments to worker
CELERYD_OPTS="--time-limit=300 --concurrency=8"

# Log and PID files
CELERYD_PID_FILE="$CELERY_RUN_DIR/%n.pid"
CELERYD_LOG_FILE="$CELERY_LOG_DIR/%n%I.log"
CELERYD_LOG_LEVEL="INFO"

# Set the working directory
C_FORCE_ROOT="true"

# Add the virtualenv
ENV_PYTHON="$VENV_PATH/bin/python"
PATH="$VENV_PATH/bin:$PATH"

# Load environment variables from .env file
if [ -f "$PROJECT_PATH/.env" ]; then
    set -o allexport
    source "$PROJECT_PATH/.env"
    set +o allexport
fi
EOF

# Create Celery service file
cat > /etc/systemd/system/celery.service << EOF
[Unit]
Description=Celery Service
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=simple
User=$APP_USER
Group=www-data
EnvironmentFile=$CELERY_CONF_DIR/celery
WorkingDirectory=$PROJECT_PATH
RuntimeDirectory=celery
RuntimeDirectoryMode=0775

# Use full path to celery and specify the worker command directly
ExecStart=$VENV_PATH/bin/celery -A \${CELERY_APP} worker \
    --loglevel=\${CELERYD_LOG_LEVEL} \
    --logfile=\${CELERYD_LOG_FILE} \
    --pidfile=\${CELERYD_PID_FILE} \
    --concurrency=4 \
    --max-tasks-per-child=100 \
    --max-memory-per-child=1200000

# Graceful shutdown
ExecStop=$VENV_PATH/bin/celery control shutdown

# Restart on failure
Restart=always
RestartSec=10s

# Ensure the log directory exists
PermissionsStartOnly=true
ExecStartPre=/bin/mkdir -p /var/log/celery
ExecStartPre=/bin/chown -R $APP_USER:www-data /var/log/celery
ExecStartPre=/bin/chmod -R 755 /var/log/celery

Restart=always
RestartSec=10s
StartLimitInterval=0

[Install]
WantedBy=multi-user.target
EOF

# Create Celery Beat service file
cat > /etc/systemd/system/celery-beat.service << EOF
[Unit]
Description=Celery Beat Service
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=simple
User=$APP_USER
Group=www-data
EnvironmentFile=$CELERY_CONF_DIR/celery
WorkingDirectory=$PROJECT_PATH
RuntimeDirectory=celery
RuntimeDirectoryMode=0775

# Use full path to celery and specify the beat command directly
ExecStart=$VENV_PATH/bin/celery -A \${CELERY_APP} beat \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    --loglevel=\${CELERYD_LOG_LEVEL} \
    --pidfile=$CELERY_RUN_DIR/beat.pid \
    --logfile=$CELERY_LOG_DIR/beat.log

# Restart on failure
Restart=always
RestartSec=10s

Restart=always
RestartSec=10s
StartLimitInterval=0

[Install]
WantedBy=multi-user.target
EOF

# Set permissions and reload systemd
chmod 644 /etc/systemd/system/celery.service /etc/systemd/system/celery-beat.service
systemctl daemon-reload

# Create logrotate configuration for Celery
cat > /etc/logrotate.d/celery << EOF
$CELERY_LOG_DIR/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
    create 640 $APP_USER www-data
    sharedscripts
    postrotate
        systemctl restart celery.service >/dev/null 2>&1 || true
        systemctl restart celery-beat.service >/dev/null 2>&1 || true
    endscript
}
EOF

# Reload systemd to apply changes
systemctl daemon-reload

# Start and enable services
for service in celery celery-beat; do
    # Stop the service if it's running
    systemctl stop $service 2>/dev/null || true
    
    # Enable and start the service
    systemctl enable $service
    if systemctl start $service; then
        sleep 2  # Give it a moment to start
        if systemctl is-active --quiet $service; then
            print_message "$service is running successfully!"
        else
            print_warning "$service started but is not active. Checking logs..."
            journalctl -u $service -n 20 --no-pager
        fi
    else
        print_error "Failed to start $service. Check logs with: journalctl -u $service -n 50"
        journalctl -u $service -n 20 --no-pager
    fi
done

# Configure Nginx
print_step "STEP 7: Configuring Nginx"
NGINX_CONF="/etc/nginx/sites-available/$DOMAIN_NAME"

# Create Nginx configuration with all domains
cat > $NGINX_CONF << EOF
# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAINS;
    
    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Redirect all HTTP requests to HTTPS
    return 301 https://\$host\$request_uri;
}

# HTTPS server configuration will be added by Certbot
# This is a template that will be updated by Certbot
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAINS;
    
    # SSL configuration will be managed by Certbot
    # ssl_certificate /etc/letsencrypt/live/\$host/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/\$host/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /var/log/nginx/\$host-access.log;
    error_log /var/log/nginx/\$host-error.log warn;
    
    # Max upload size
    client_max_body_size 100M;
    
    # Gzip settings
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/xml application/xml+rss text/javascript;
    
    # Static files
    location /static/ {
        alias $PROJECT_PATH/static/;
        expires 30d;
        access_log off;
        add_header Cache-Control "public, max-age=2592000";
    }
    
    # Media files
    location /media/ {
        alias $PROJECT_PATH/media/;
        expires 30d;
        access_log off;
        add_header Cache-Control "public, max-age=2592000";
    }
    
    # Security headers for static files
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
        access_log off;
    }
    
    # Proxy configuration for Django
    location / {
        proxy_pass http://unix:$PROJECT_PATH/gunicorn.sock;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        
        # WebSocket support
        proxy_redirect off;
        proxy_buffering off;
    }
    
    # Deny access to hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    # Deny access to sensitive files
    location ~* \.(py|pyc|sh|sql|env|git|gitignore|gitattributes|htaccess|htpasswd|ini|conf|cfg|inc)$ {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    # Error pages
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
    }
}

# Include Let's Encrypt challenge directory for certificate renewal
include /etc/letsencrypt/options-ssl-nginx.conf;
include /etc/letsencrypt/options-ssl-nginx-*.conf;


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

# SSL Setup Instructions
print_step "STEP 8: SSL Certificate Setup (Manual Step Required)"

# Create a script for easy SSL setup later
SSL_SETUP_SCRIPT="/usr/local/bin/setup_ssl_${DOMAIN_NAME//./_}.sh"
cat > $SSL_SETUP_SCRIPT << EOF
#!/bin/bash
echo "Setting up SSL for $DOMAIN_NAME..."
if [ "\$EUID" -ne 0 ]
  then echo "Please run as root (use sudo)"
  exit 1
fi

# Install certbot if not installed
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

# Build the certbot command
CERTBOT_CMD="certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME"
for sub in "${SUBDOMAINS[@]}"; do
    if [ -n "\$sub" ]; then
        CERTBOT_CMD+=" -d \$sub.$DOMAIN_NAME"
    fi
done

# Add email if provided
if [ -n "$SSL_EMAIL" ]; then
    CERTBOT_CMD+=" --email $SSL_EMAIL --agree-tos"
else
    CERTBOT_CMD+=" --register-unsafely-without-email"
fi

# Add non-interactive and redirect options
CERTBOT_CMD+=" --non-interactive --redirect"

echo "Running: \$ $CERTBOT_CMD"
eval "\$CERTBOT_CMD"

if [ \$? -eq 0 ]; then
    echo -e "\n${GREEN}SSL certificate installed successfully!${NC}"
    echo "Testing Nginx configuration..."
    nginx -t && systemctl restart nginx
    echo -e "\n${GREEN}SSL setup complete! Your site is now secured with HTTPS.${NC}"
else
    echo -e "\n${RED}Failed to install SSL certificate.${NC}"
    echo "Common issues:"
    echo "1. DNS not properly configured (check with: dig +short $DOMAIN_NAME)"
    echo "2. Port 80 is blocked (check with: sudo ufw status)"
    echo "3. Nginx is not running (check with: systemctl status nginx)"
    exit 1
fi
EOF

chmod +x $SSL_SETUP_SCRIPT

echo -e "\n${YELLOW}IMPORTANT: Your site is now running on HTTP. To set up SSL:${NC}"
echo "1. Make sure your domain ($DOMAIN_NAME) points to this server's IP"
echo "2. Wait for DNS propagation (use: dig +short $DOMAIN_NAME to verify)"
echo -e "3. Run: ${GREEN}sudo $SSL_SETUP_SCRIPT${NC}"
echo -e "\nOr run the certbot command manually:"
echo -e "${GREEN}sudo certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME \\
    --non-interactive \\
    --agree-tos \\
    --email $SSL_EMAIL \\
    --redirect${NC}"

# Install Certbot but don't run it yet
if ! command -v certbot &> /dev/null; then
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