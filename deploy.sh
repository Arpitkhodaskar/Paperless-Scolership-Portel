#!/bin/bash

# Production Deployment Script for Scholarship Portal
# This script automates the deployment process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="scholarship-portal"
PROJECT_DIR="/opt/scholarship_portal"
REPO_URL="https://github.com/yourusername/scholarship-portal.git"
BRANCH="main"
PYTHON_VERSION="3.11"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install system dependencies
install_system_dependencies() {
    print_status "Installing system dependencies..."
    
    # Update package list
    sudo apt update
    
    # Install required packages
    sudo apt install -y \
        python3-pip \
        python3-venv \
        python3-dev \
        nginx \
        supervisor \
        redis-server \
        mysql-client \
        git \
        curl \
        wget \
        certbot \
        python3-certbot-nginx \
        htop \
        vim \
        unzip \
        build-essential \
        libmysqlclient-dev \
        pkg-config \
        libffi-dev \
        libssl-dev
    
    print_success "System dependencies installed"
}

# Function to create application user
create_app_user() {
    print_status "Creating application user..."
    
    if ! id "scholarship" &>/dev/null; then
        sudo adduser --system --group --home $PROJECT_DIR scholarship
        print_success "Application user created"
    else
        print_warning "Application user already exists"
    fi
}

# Function to setup application directory
setup_app_directory() {
    print_status "Setting up application directory..."
    
    # Create directory structure
    sudo mkdir -p $PROJECT_DIR/{app,logs,backups,ssl}
    sudo mkdir -p /var/log/scholarship_portal
    
    # Set permissions
    sudo chown -R scholarship:scholarship $PROJECT_DIR
    sudo chown -R scholarship:scholarship /var/log/scholarship_portal
    
    print_success "Application directory setup complete"
}

# Function to clone or update repository
setup_repository() {
    print_status "Setting up repository..."
    
    if [ -d "$PROJECT_DIR/app/.git" ]; then
        print_status "Updating existing repository..."
        cd $PROJECT_DIR/app
        sudo -u scholarship git fetch origin
        sudo -u scholarship git checkout $BRANCH
        sudo -u scholarship git pull origin $BRANCH
    else
        print_status "Cloning repository..."
        sudo -u scholarship git clone -b $BRANCH $REPO_URL $PROJECT_DIR/app
    fi
    
    print_success "Repository setup complete"
}

# Function to setup Python virtual environment
setup_python_env() {
    print_status "Setting up Python virtual environment..."
    
    cd $PROJECT_DIR/app
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        sudo -u scholarship python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    sudo -u scholarship bash -c "
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install gunicorn psycopg2-binary django-redis boto3 sentry-sdk
    "
    
    print_success "Python environment setup complete"
}

# Function to setup environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f "$PROJECT_DIR/app/.env" ]; then
        print_warning "Creating .env file from template..."
        sudo -u scholarship cp $PROJECT_DIR/app/.env.example $PROJECT_DIR/app/.env
        print_warning "Please edit $PROJECT_DIR/app/.env with your production values"
    else
        print_warning ".env file already exists"
    fi
}

# Function to run Django migrations and setup
setup_django() {
    print_status "Setting up Django application..."
    
    cd $PROJECT_DIR/app
    
    sudo -u scholarship bash -c "
        source venv/bin/activate
        export DJANGO_SETTINGS_MODULE=scholarship_portal.settings.production
        
        # Run migrations
        python manage.py migrate --noinput
        
        # Collect static files
        python manage.py collectstatic --noinput
        
        # Create notification templates
        python manage.py create_notification_templates || true
        
        # Load initial data if exists
        if [ -f 'fixtures/initial_data.json' ]; then
            python manage.py loaddata fixtures/initial_data.json
        fi
    "
    
    print_success "Django application setup complete"
}

# Function to setup Nginx
setup_nginx() {
    print_status "Setting up Nginx..."
    
    # Copy Nginx configuration
    sudo cp $PROJECT_DIR/app/nginx.conf /etc/nginx/sites-available/scholarship_portal
    
    # Enable site
    sudo ln -sf /etc/nginx/sites-available/scholarship_portal /etc/nginx/sites-enabled/
    
    # Remove default site
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test Nginx configuration
    sudo nginx -t
    
    print_success "Nginx setup complete"
}

# Function to setup Supervisor
setup_supervisor() {
    print_status "Setting up Supervisor..."
    
    # Create Supervisor configuration
    sudo tee /etc/supervisor/conf.d/scholarship_portal.conf > /dev/null <<EOF
[program:scholarship_portal]
command=$PROJECT_DIR/app/venv/bin/gunicorn scholarship_portal.wsgi:application -c $PROJECT_DIR/app/gunicorn.conf.py
directory=$PROJECT_DIR/app
user=scholarship
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/scholarship_portal/gunicorn.log
environment=DJANGO_SETTINGS_MODULE="scholarship_portal.settings.production"

[program:scholarship_portal_celery]
command=$PROJECT_DIR/app/venv/bin/celery -A scholarship_portal worker -l info
directory=$PROJECT_DIR/app
user=scholarship
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/scholarship_portal/celery.log
environment=DJANGO_SETTINGS_MODULE="scholarship_portal.settings.production"

[program:scholarship_portal_beat]
command=$PROJECT_DIR/app/venv/bin/celery -A scholarship_portal beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
directory=$PROJECT_DIR/app
user=scholarship
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/scholarship_portal/celery_beat.log
environment=DJANGO_SETTINGS_MODULE="scholarship_portal.settings.production"
EOF
    
    print_success "Supervisor setup complete"
}

# Function to setup SSL certificate
setup_ssl() {
    read -p "Enter your domain name: " DOMAIN_NAME
    
    if [ -n "$DOMAIN_NAME" ]; then
        print_status "Setting up SSL certificate for $DOMAIN_NAME..."
        
        # Obtain SSL certificate
        sudo certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME
        
        # Setup auto-renewal
        sudo crontab -l 2>/dev/null | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet"; } | sudo crontab -
        
        print_success "SSL certificate setup complete"
    else
        print_warning "Skipping SSL setup - no domain provided"
    fi
}

# Function to setup firewall
setup_firewall() {
    print_status "Setting up firewall..."
    
    # Enable UFW
    sudo ufw --force enable
    
    # Allow SSH
    sudo ufw allow ssh
    
    # Allow HTTP and HTTPS
    sudo ufw allow 'Nginx Full'
    
    # Allow Redis (only from localhost)
    sudo ufw allow from 127.0.0.1 to any port 6379
    
    # Allow MySQL (only from localhost)
    sudo ufw allow from 127.0.0.1 to any port 3306
    
    print_success "Firewall setup complete"
}

# Function to start services
start_services() {
    print_status "Starting services..."
    
    # Reload Supervisor
    sudo supervisorctl reread
    sudo supervisorctl update
    
    # Start application
    sudo supervisorctl start scholarship_portal
    sudo supervisorctl start scholarship_portal_celery
    sudo supervisorctl start scholarship_portal_beat
    
    # Start Nginx
    sudo systemctl enable nginx
    sudo systemctl restart nginx
    
    # Start Redis
    sudo systemctl enable redis-server
    sudo systemctl restart redis-server
    
    print_success "Services started"
}

# Function to create backup script
setup_backup_script() {
    print_status "Setting up backup script..."
    
    sudo tee $PROJECT_DIR/backup.sh > /dev/null <<'EOF'
#!/bin/bash

# Backup script for Scholarship Portal

BACKUP_DIR="/opt/scholarship_portal/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup application files
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz -C /opt/scholarship_portal app

# Backup logs
tar -czf $BACKUP_DIR/logs_backup_$DATE.tar.gz -C /var/log scholarship_portal

# Clean old backups (keep last 7 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF
    
    sudo chmod +x $PROJECT_DIR/backup.sh
    sudo chown scholarship:scholarship $PROJECT_DIR/backup.sh
    
    # Add to crontab
    (sudo crontab -u scholarship -l 2>/dev/null; echo "0 2 * * * $PROJECT_DIR/backup.sh") | sudo crontab -u scholarship -
    
    print_success "Backup script setup complete"
}

# Function to display service status
show_status() {
    print_status "Service Status:"
    echo
    
    echo "Supervisor processes:"
    sudo supervisorctl status
    echo
    
    echo "Nginx status:"
    sudo systemctl status nginx --no-pager -l
    echo
    
    echo "Redis status:"
    sudo systemctl status redis-server --no-pager -l
    echo
    
    echo "Application logs (last 10 lines):"
    sudo tail -n 10 /var/log/scholarship_portal/gunicorn.log
    echo
}

# Main deployment function
deploy() {
    print_status "Starting deployment of Scholarship Portal..."
    
    # Check if running as root or with sudo
    if [ "$EUID" -eq 0 ]; then
        print_error "This script should not be run as root. Please run with sudo when needed."
        exit 1
    fi
    
    # Install system dependencies
    install_system_dependencies
    
    # Create application user
    create_app_user
    
    # Setup application directory
    setup_app_directory
    
    # Setup repository
    setup_repository
    
    # Setup Python environment
    setup_python_env
    
    # Setup environment configuration
    setup_environment
    
    # Setup Django
    setup_django
    
    # Setup Nginx
    setup_nginx
    
    # Setup Supervisor
    setup_supervisor
    
    # Setup SSL (optional)
    read -p "Do you want to setup SSL certificate? (y/n): " setup_ssl_choice
    if [ "$setup_ssl_choice" = "y" ]; then
        setup_ssl
    fi
    
    # Setup firewall
    setup_firewall
    
    # Setup backup script
    setup_backup_script
    
    # Start services
    start_services
    
    # Show status
    show_status
    
    print_success "Deployment completed successfully!"
    print_status "Your application should be available at: http://your-domain.com"
    print_warning "Don't forget to:"
    echo "  1. Edit $PROJECT_DIR/app/.env with your production values"
    echo "  2. Create a superuser: cd $PROJECT_DIR/app && sudo -u scholarship venv/bin/python manage.py createsuperuser"
    echo "  3. Configure your domain DNS to point to this server"
    echo "  4. Test all functionality thoroughly"
}

# Script options
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "update")
        print_status "Updating application..."
        setup_repository
        setup_python_env
        setup_django
        sudo supervisorctl restart scholarship_portal
        sudo supervisorctl restart scholarship_portal_celery
        sudo systemctl reload nginx
        print_success "Update completed"
        ;;
    "status")
        show_status
        ;;
    "backup")
        $PROJECT_DIR/backup.sh
        ;;
    "logs")
        print_status "Recent application logs:"
        sudo tail -f /var/log/scholarship_portal/gunicorn.log
        ;;
    *)
        echo "Usage: $0 {deploy|update|status|backup|logs}"
        echo "  deploy  - Full deployment"
        echo "  update  - Update application code"
        echo "  status  - Show service status"
        echo "  backup  - Run backup"
        echo "  logs    - Show application logs"
        exit 1
        ;;
esac
