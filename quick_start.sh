#!/bin/bash

# Django Scholarship Portal - Quick Start Script for Linux/macOS

echo "==============================================="
echo "   Django Scholarship Portal - Quick Start"
echo "==============================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}[$1/8]${NC} $2"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if Python is installed
print_step 1 "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed or not in PATH"
    echo "Please install Python 3.9+ from https://python.org"
    exit 1
fi

python3 --version
print_success "Python is installed"

# Create virtual environment
print_step 2 "Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
print_step 3 "Activating virtual environment..."
source venv/bin/activate
print_success "Virtual environment activated"

# Upgrade pip
print_step 4 "Upgrading pip..."
pip install --upgrade pip
print_success "Pip upgraded"

# Install dependencies
print_step 5 "Installing dependencies..."
pip install -r requirements.txt
print_success "Dependencies installed"

# Setup environment file
print_step 6 "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_success "Environment file created"
    echo
    print_warning "IMPORTANT: Please edit .env file with your database credentials"
    echo "Default database settings:"
    echo "  - Database: scholarship_portal_db"
    echo "  - User: root"
    echo "  - Password: (set your MySQL password)"
    echo
else
    print_warning "Environment file already exists"
fi

# Database migrations
print_step 7 "Running database migrations..."
python manage.py migrate
print_success "Database migrations completed"

# Create superuser
print_step 8 "Creating superuser..."
echo "Please create an admin user:"
python manage.py createsuperuser

echo
echo "==============================================="
echo "           Setup Complete!"
echo "==============================================="
echo
print_success "Your Django Scholarship Portal is ready!"
echo
echo "To start the development server:"
echo "  python manage.py runserver"
echo
echo "Then visit: http://127.0.0.1:8000"
echo "Admin panel: http://127.0.0.1:8000/admin"
echo
echo "For background tasks, run in separate terminals:"
echo "  celery -A scholarship_portal worker -l info"
echo "  celery -A scholarship_portal beat -l info"
echo
echo "==============================================="
