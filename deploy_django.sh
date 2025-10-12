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

# Interactive prompts with default values
print_step "STEP 1: Gathering Configuration Information"

# Set default values
DEFAULT_DOMAIN="tarxemo.com"
DEFAULT_SUBDOMAINS="github"
DEFAULT_EMAIL="tarxemo@gmail.com"
DEFAULT_PROJECT_PATH="/home/ubuntu/github_management_project/RB"
DEFAULT_PROJECT_NAME="github_management_project"
DEFAULT_APP_USER="ubuntu"
DEFAULT_APP_PORT="8000"

# Get user input with defaults
read -p "Enter your main domain name (e.g., example.com) [${DEFAULT_DOMAIN}]: " DOMAIN_NAME
DOMAIN_NAME=${DOMAIN_NAME:-$DEFAULT_DOMAIN}

read -p "Enter subdomains (space-separated, e.g., api app www) [${DEFAULT_SUBDOMAINS}]: " SUBDOMAINS_INPUT
SUBDOMAINS_INPUT=${SUBDOMAINS_INPUT:-$DEFAULT_SUBDOMAINS}

read -p "Enter your email for SSL certificate (Let's Encrypt) [${DEFAULT_EMAIL}]: " SSL_EMAIL
SSL_EMAIL=${SSL_EMAIL:-$DEFAULT_EMAIL}

read -p "Enter the path to your Django project directory [${DEFAULT_PROJECT_PATH}]: " PROJECT_PATH
PROJECT_PATH=${PROJECT_PATH:-$DEFAULT_PROJECT_PATH}

read -p "Enter your Django project name [${DEFAULT_PROJECT_NAME}]: " PROJECT_NAME
PROJECT_NAME=${PROJECT_NAME:-$DEFAULT_PROJECT_NAME}

read -p "Enter the system user to run the application [${DEFAULT_APP_USER}]: " APP_USER
APP_USER=${APP_USER:-$DEFAULT_APP_USER}

read -p "Enter the port for the application [${DEFAULT_APP_PORT}]: " APP_PORT
APP_PORT=${APP_PORT:-$DEFAULT_APP_PORT}

# Validate port number
if ! [[ "$APP_PORT" =~ ^[0-9]+$ ]] || [ "$APP_PORT" -lt 1024 ] || [ "$APP_PORT" -gt 65535 ]; then
    print_error "Invalid port number. Please enter a number between 1024 and 65535."
    exit 1
fi

read -p "Do you want to set up HTTPS with Let's Encrypt? (y/n) [y]: " SETUP_SSL
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

# Set primary domain (first subdomain if available, otherwise main domain)
if [ -n "${SUBDOMAINS[0]}" ]; then
    PRIMARY_DOMAIN="${SUBDOMAINS[0]}.$DOMAIN_NAME"
else
    PRIMARY_DOMAIN="$DOMAIN_NAME"
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
echo "All Domains: $DOMAINS"
echo "SSL Email: $SSL_EMAIL"
echo "Project Path: $PROJECT_PATH"
echo "Project Name: $PROJECT_NAME"
echo "App User: $APP_USER"
echo "App Port: $APP_PORT"
echo "Setup SSL: $SETUP_SSL"
echo ""
read -p "Continue with these settings? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    print_error "Deployment cancelled by user"
    exit 1
fi

# Update system
print_step "STEP 2: Updating System Packages"
# apt-get update -y
# apt-get install -y redis-server
# apt-get upgrade -y

print_step "STEP 3: Installing Required Packages"
apt-get install -y nginx postgresql postgresql-contrib libpq-dev \
    build-essential git curl software-properties-common

# Set virtual environment path
VENV_PATH="${PROJECT_PATH}/venv"

# Create virtual environment
print_step "STEP 4: Creating Python Virtual Environment"
if [ ! -d "$VENV_PATH" ]; then
    print_message "Creating virtual environment at $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
    if [ $? -eq 0 ]; then
        print_message "Virtual environment created successfully at $VENV_PATH"
    else
        print_error "Failed to create virtual environment. Trying with --clear flag..."
        python3 -m venv --clear "$VENV_PATH" || {
            print_error "Failed to create virtual environment. Please check Python installation and permissions."
            exit 1
        }
    fi
else
    print_message "Virtual environment already exists at $VENV_PATH"
fi

# Ensure virtual environment is activated
if [ ! -f "$VENV_PATH/bin/activate" ]; then
    print_error "Virtual environment activation script not found at $VENV_PATH/bin/activate"
    exit 1
fi

# Install Python dependencies
print_step "STEP 5: Installing Python Dependencies"
source $VENV_PATH/bin/activate

# Upgrade pip and install build dependencies
pip install --upgrade pip
pip install --upgrade wheel setuptools

# Install system dependencies required for some Python packages
apt-get install -y python3-dev libffi-dev libssl-dev

# Install requirements if exists, otherwise install essential packages
if [ -f "$PROJECT_PATH/requirements.txt" ]; then
    print_message "Installing from requirements.txt..."
    pip install cryptography
    pip install -r "$PROJECT_PATH/requirements.txt"
else
    print_warning "requirements.txt not found. Installing essential packages..."
    pip install django gunicorn psycopg2-binary python-decouple beautifulsoup4 \
        cryptography django-celery-beat django-celery-results redis python-dotenv
fi

print_message "Python dependencies installed"

# Create necessary directories
print_step "STEP 6: Setting Up Directories and Permissions"
mkdir -p $PROJECT_PATH/static
mkdir -p $PROJECT_PATH/media
mkdir -p $PROJECT_PATH/logs

# Collect static files using virtualenv python
print_message "Collecting static files..."
cd $PROJECT_PATH
$VENV_PATH/bin/python manage.py collectstatic --noinput || print_warning "Static files collection failed or not configured"

# Set proper permissions
print_message "Setting file permissions..."
chown -R $APP_USER:www-data $PROJECT_PATH
chmod -R 755 $PROJECT_PATH
chmod -R 775 $PROJECT_PATH/static
chmod -R 775 $PROJECT_PATH/media
chmod -R 775 $PROJECT_PATH/logs

# Deactivate virtualenv before creating services
deactivate

# Create Gunicorn systemd service
print_step "STEP 7: Creating Gunicorn Service"
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
    --bind 127.0.0.1:$APP_PORT \\
    --access-logfile $PROJECT_PATH/logs/gunicorn-access.log \\
    --error-logfile $PROJECT_PATH/logs/gunicorn-error.log \\
    --log-level info \\
    $PROJECT_NAME.wsgi:application

Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

print_message "Gunicorn service file created"

# We're not using a socket file anymore as it was causing issues
# Gunicorn will be started directly on port 8006
print_message "Using direct port binding for Gunicorn (port $APP_PORT)"

# Start Gunicorn - First disable and remove any existing socket
print_message "Configuring Gunicorn service..."
systemctl disable --now gunicorn.socket 2>/dev/null || true
rm -f /etc/systemd/system/gunicorn.socket 2>/dev/null || true
rm -f /etc/systemd/system/sockets.target.wants/gunicorn.socket 2>/dev/null || true

# Reload systemd and start Gunicorn directly
systemctl daemon-reload
systemctl stop gunicorn 2>/dev/null || true
systemctl start gunicorn
systemctl enable gunicorn

# Wait a moment for Gunicorn to start
sleep 3

# Check Gunicorn status
if systemctl is-active --quiet gunicorn; then
    print_message "Gunicorn is running successfully!"
    print_message "Checking if Gunicorn is listening on port $APP_PORT..."
    if lsof -i :$APP_PORT > /dev/null 2>&1; then
        print_message "Gunicorn is listening on port $APP_PORT"
    else
        print_warning "Gunicorn is active but not listening on port $APP_PORT. Check logs."
    fi
else
    print_error "Gunicorn failed to start. Check logs with: journalctl -u gunicorn -n 50"
    journalctl -u gunicorn -n 20 --no-pager
fi

# Configure Celery service
print_step "STEP 8: Configuring Celery Service"

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

ExecStart=$VENV_PATH/bin/celery -A \${CELERY_APP} worker \
    --loglevel=\${CELERYD_LOG_LEVEL} \
    --logfile=\${CELERYD_LOG_FILE} \
    --pidfile=\${CELERYD_PID_FILE} \
    --concurrency=4 \
    --max-tasks-per-child=100 \
    --max-memory-per-child=1200000

ExecStop=$VENV_PATH/bin/celery control shutdown

Restart=always
RestartSec=10s
StartLimitInterval=0

PermissionsStartOnly=true
ExecStartPre=/bin/mkdir -p /var/log/celery
ExecStartPre=/bin/chown -R $APP_USER:www-data /var/log/celery
ExecStartPre=/bin/chmod -R 755 /var/log/celery

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

ExecStart=$VENV_PATH/bin/celery -A \${CELERY_APP} beat \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    --loglevel=\${CELERYD_LOG_LEVEL} \
    --pidfile=$CELERY_RUN_DIR/beat.pid \
    --logfile=$CELERY_LOG_DIR/beat.log

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

# Start and enable Celery services
for service in celery celery-beat; do
    systemctl stop $service 2>/dev/null || true
    systemctl enable $service
    if systemctl start $service; then
        sleep 2
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
print_step "STEP 9: Configuring Nginx"
# Determine primary domain (use first subdomain if available, otherwise use main domain)
if [ -n "${SUBDOMAINS[0]}" ]; then
    PRIMARY_DOMAIN="${SUBDOMAINS[0]}.$DOMAIN_NAME"
else
    PRIMARY_DOMAIN="$DOMAIN_NAME"
fi

NGINX_CONF="/etc/nginx/sites-available/${PRIMARY_DOMAIN}"

# Create Nginx configuration with all domains
cat > $NGINX_CONF << 'NGINX_EOF'
# HTTP server - redirect to HTTPS (will be updated after SSL setup)
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAINS;
    
    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /var/log/nginx/PRIMARY_DOMAIN_PLACEHOLDER-access.log;
    error_log /var/log/nginx/PRIMARY_DOMAIN_PLACEHOLDER-error.log warn;
    
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
        alias PROJECT_PATH_PLACEHOLDER/static/;
        expires 30d;
        access_log off;
        add_header Cache-Control "public, max-age=2592000";
    }
    
    # Media files
    location /media/ {
        alias PROJECT_PATH_PLACEHOLDER/media/;
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
        proxy_pass http://127.0.0.1:8006;
        proxy_http_version 1.1;
        
        # Standard headers
        proxy_set_header Host               $host;
        proxy_set_header X-Real-IP          $remote_addr;
        proxy_set_header X-Forwarded-For    $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto  $scheme;
        
        # WebSocket support
        proxy_set_header Upgrade            $http_upgrade;
        proxy_set_header Connection         "upgrade";
        
        # Timeouts
        proxy_read_timeout                  300s;
        proxy_connect_timeout               300s;
        
        # Other settings
        proxy_redirect                      off;
        proxy_buffering                     off;
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
NGINX_EOF

# Replace placeholders in Nginx config
sed -i "s|PROJECT_PATH_PLACEHOLDER|$PROJECT_PATH|g" $NGINX_CONF
sed -i "s|DOMAINS_PLACEHOLDER|$DOMAINS|g" $NGINX_CONF
sed -i "s|PRIMARY_DOMAIN_PLACEHOLDER|$PRIMARY_DOMAIN|g" $NGINX_CONF

print_message "Nginx configuration created"

# Enable Nginx site
ln -sf $NGINX_CONF /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
print_message "Testing Nginx configuration..."
if nginx -t; then
    print_message "Nginx configuration is valid"
    systemctl restart nginx
    systemctl enable nginx
    print_message "Nginx restarted successfully"
else
    print_error "Nginx configuration test failed!"
    nginx -t
    exit 1
fi

# Configure firewall
print_step "STEP 10: Configuring Firewall"
if command -v ufw &> /dev/null; then
    print_message "Configuring UFW firewall..."
    ufw allow 'Nginx Full'
    ufw allow OpenSSH
    ufw --force enable
    print_message "Firewall configured"
else
    print_warning "UFW not found. Please configure your firewall manually to allow ports 80 and 443"
fi

# SSL Setup Instructions
print_step "STEP 11: SSL Certificate Setup"

# Install Certbot
if ! command -v certbot &> /dev/null; then
    print_message "Installing certbot..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

# Create a script for easy SSL setup
SSL_SETUP_SCRIPT="/usr/local/bin/setup_ssl_${DOMAIN_NAME//./_}.sh"

# Create the SSL setup script
cat > $SSL_SETUP_SCRIPT << 'SSL_SCRIPT_EOF'
#!/bin/bash

# Set variables from command line arguments
DOMAIN="$1"
EMAIL="$2"
shift 2
SUBDOMAINS=("$@")

echo "Setting up SSL for domain: $DOMAIN"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Ensure Nginx is running
if ! systemctl is-active --quiet nginx; then
    systemctl start nginx
fi

# Build the certbot command with the main domain
CERTBOT_CMD="certbot --nginx --non-interactive --agree-tos"
CERTBOT_CMD+=" --email $EMAIL"
CERTBOT_CMD+=" --redirect"
CERTBOT_CMD+=" --hsts"
CERTBOT_CMD+=" --staple-ocsp"
CERTBOT_CMD+=" --keep-until-expiring"
CERTBOT_CMD+=" --rsa-key-size 2048"
CERTBOT_CMD+=" --preferred-challenges http"

# Add main domain
CERTBOT_CMD+=" -d $DOMAIN"

# Add subdomains if any
for sub in "${SUBDOMAINS[@]}"; do
    if [ -n "$sub" ] && [ "$sub" != "www" ]; then
        CERTBOT_CMD+=" -d $sub.$DOMAIN"
    fi
done

# Add www subdomain if not already included
if [[ ! " ${SUBDOMAINS[@]} " =~ " www " ]]; then
    CERTBOT_CMD+=" -d www.$DOMAIN"
fi

# Execute the certbot command
echo "Running: $CERTBOT_CMD"

# Create a temporary Nginx config for HTTP challenge
TEMP_NGINX_CONF="/etc/nginx/conf.d/letsencrypt.conf"
cat > $TEMP_NGINX_CONF << NGINX_EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    location / {
        return 301 https://\$host\$request_uri;
    }
}
NGINX_EOF

# Test and reload Nginx
nginx -t && systemctl reload nginx

# Run certbot
eval $CERTBOT_CMD
CERTBOT_EXIT_CODE=$?

# Clean up temporary Nginx config
rm -f $TEMP_NGINX_CONF
nginx -t && systemctl reload nginx

if [ $CERTBOT_EXIT_CODE -eq 0 ]; then
    echo -e "\n✅ SSL certificate installed successfully!"
    echo "Testing Nginx configuration..."
    nginx -t && systemctl restart nginx
    echo -e "\n🔒 SSL setup complete! Your site is now secured with HTTPS."
    echo -e "\nYou can test automatic renewal with: certbot renew --dry-run"
else
    echo -e "\n❌ Failed to install SSL certificate."
    echo "Common issues:"
    echo "1. DNS not properly configured (check with: dig +short $DOMAIN)"
    echo "2. Port 80/443 is blocked (check with: sudo ufw status)"
    echo "3. Nginx is not running (check with: systemctl status nginx)"
    echo -e "\nCheck the full error logs with: journalctl -u nginx -n 50"
    exit 1
fi
SSL_SCRIPT_EOF

# Make the script executable
chmod +x $SSL_SETUP_SCRIPT
print_message "SSL setup script created at $SSL_SETUP_SCRIPT"

# Run the SSL setup script
print_message "Setting up SSL certificates..."
$SSL_SETUP_SCRIPT "$DOMAIN_NAME" "$SSL_EMAIL" "${SUBDOMAINS[@]}"

if [ $? -ne 0 ]; then
    print_warning "SSL setup encountered an error. Please check the output above for details."
    print_warning "You can try running the setup manually with: sudo $SSL_SETUP_SCRIPT $DOMAIN_NAME $SSL_EMAIL ${SUBDOMAINS[@]}"
fi

chmod +x "$SSL_SETUP_SCRIPT"

echo -e "\n${YELLOW}═══════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}       SSL SETUP INSTRUCTIONS${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
echo -e "\n${YELLOW}IMPORTANT: Your site is now running on HTTP.${NC}"
echo -e "\nTo set up SSL/HTTPS:"
echo -e "1. Make sure your domain points to this server's IP"
echo -e "   Current domains: ${GREEN}$DOMAINS${NC}"
echo -e "2. Verify DNS propagation:"
echo -e "   ${GREEN}dig +short $DOMAIN_NAME${NC}"
for sub in "${SUBDOMAINS[@]}"; do
    if [ -n "$sub" ]; then
        echo -e "   ${GREEN}dig +short $sub.$DOMAIN_NAME${NC}"
    fi
done
echo -e "3. Run the SSL setup script:"
echo -e "   ${GREEN}sudo $SSL_SETUP_SCRIPT${NC}"
echo -e "\n${YELLOW}═══════════════════════════════════════════════════${NC}\n"

# Create management script
print_step "STEP 12: Creating Management Scripts"
MANAGE_SCRIPT="$PROJECT_PATH/manage-app.sh"

cat > $MANAGE_SCRIPT << 'MANAGE_EOF'
#!/bin/bash

# Management script for Django application
PROJECT_PATH="MANAGE_PROJECT_PATH_PLACEHOLDER"

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
MANAGE_EOF

sed -i "s|MANAGE_PROJECT_PATH_PLACEHOLDER|$PROJECT_PATH|g" $MANAGE_SCRIPT
chmod +x $MANAGE_SCRIPT
chown $APP_USER:$APP_USER $MANAGE_SCRIPT

print_message "Management script created at $MANAGE_SCRIPT"

# Final verification
print_step "STEP 13: Final Verification"

echo "Checking services..."
SERVICES_OK=true

# Check if Gunicorn is running and listening on the port
if systemctl is-active --quiet gunicorn; then
    if lsof -i :$APP_PORT > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Gunicorn is running and listening on port $APP_PORT"
    else
        echo -e "${YELLOW}⚠${NC} Gunicorn is running but not listening on port $APP_PORT"
        SERVICES_OK=false
    fi
else
    echo -e "${RED}✗${NC} Gunicorn is not running"
    SERVICES_OK=false
fi

if systemctl is-active --quiet celery; then
    echo -e "${GREEN}✓${NC} Celery is running"
else
    echo -e "${RED}✗${NC} Celery is not running"
fi

if systemctl is-active --quiet celery-beat; then
    echo -e "${GREEN}✓${NC} Celery Beat is running"
else
    echo -e "${RED}✗${NC} Celery Beat is not running"
    SERVICES_OK=false
fi

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓${NC} Nginx is running"
else
    echo -e "${RED}✗${NC} Nginx is not running"
    SERVICES_OK=false
fi

# Check if port is listening
echo ""
echo "Checking port $APP_PORT..."
if lsof -i :$APP_PORT > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Application is listening on port $APP_PORT"
else
    echo -e "${RED}✗${NC} Nothing is listening on port $APP_PORT"
    SERVICES_OK=false
fi

# Display summary
print_step "Deployment Complete!"

cat << SUMMARY_EOF

${GREEN}╔═══════════════════════════════════════════════════╗
║           Deployment Summary                       ║
╚═══════════════════════════════════════════════════╝${NC}

${GREEN}✓${NC} Your Django application has been deployed!

Domain Configuration:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Main Domain: http://$DOMAIN_NAME
  • All Configured Domains: $DOMAINS
  • Port: $APP_PORT

Important Files and Locations:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Project Path: $PROJECT_PATH
  • Virtual Environment: $VENV_PATH
  • Nginx Config: $NGINX_CONF
  • Logs Directory: $PROJECT_PATH/logs
  • Static Files: $PROJECT_PATH/static
  • Media Files: $PROJECT_PATH/media
  • Management Script: $MANAGE_SCRIPT
  • SSL Setup Script: $SSL_SETUP_SCRIPT

Service Management:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Restart all: $MANAGE_SCRIPT restart
  • Check status: $MANAGE_SCRIPT status
  • View logs: $MANAGE_SCRIPT logs
  • Update app: $MANAGE_SCRIPT update

Individual Services:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Restart Gunicorn: sudo systemctl restart gunicorn
  • Restart Celery: sudo systemctl restart celery
  • Restart Celery Beat: sudo systemctl restart celery-beat
  • Restart Nginx: sudo systemctl restart nginx
  • View Gunicorn logs: sudo journalctl -u gunicorn -f
  • View Celery logs: sudo journalctl -u celery -f
  • View Nginx logs: sudo tail -f /var/log/nginx/$DOMAIN_NAME-error.log

Testing Your Deployment:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Test locally: curl http://localhost:$APP_PORT
  2. Test via Nginx: curl http://localhost
  3. Check from external: curl http://$DOMAIN_NAME

Next Steps (IMPORTANT):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Update Django settings.py:
     ${YELLOW}ALLOWED_HOSTS = [$ALLOWED_HOSTS]
     DEBUG = False${NC}

  2. Configure your database in settings.py or .env

  3. Run database migrations:
     ${GREEN}cd $PROJECT_PATH
     source venv/bin/activate
     python manage.py migrate
     python manage.py createsuperuser  # Optional
     deactivate${NC}

  4. Update DNS records to point to this server's IP:
     ${GREEN}$(curl -s ifconfig.me 2>/dev/null || echo "Run: curl ifconfig.me")${NC}

  5. After DNS propagates, set up SSL:
     ${GREEN}sudo $SSL_SETUP_SCRIPT${NC}

Troubleshooting:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • If site not reachable:
    - Check Gunicorn: sudo systemctl status gunicorn
    - Check Nginx: sudo systemctl status nginx
    - Check port: sudo lsof -i :$APP_PORT
    - Check logs: sudo journalctl -u gunicorn -n 100

  • If 502 Bad Gateway:
    - Gunicorn may not be running or crashed
    - Check: sudo journalctl -u gunicorn -n 50
    - Restart: sudo systemctl restart gunicorn

  • If static files not loading:
    - Run: cd $PROJECT_PATH && source venv/bin/activate
    - Then: python manage.py collectstatic --noinput
    - Check permissions: ls -la $PROJECT_PATH/static

$(if [ "$SERVICES_OK" = false ]; then
    echo -e "${YELLOW}⚠ WARNING: Some services are not running properly!"
    echo -e "   Please check the logs:"
    echo -e "   - Gunicorn: sudo journalctl -u gunicorn -n 50"
    echo -e "   - Celery: sudo journalctl -u celery -n 50"
    echo -e "   - Nginx: sudo journalctl -u nginx -n 50${NC}"
fi)

${GREEN}Happy deploying! 🚀${NC}

For support and documentation, visit: https://docs.djangoproject.com/

SUMMARY_EOF

exit 0