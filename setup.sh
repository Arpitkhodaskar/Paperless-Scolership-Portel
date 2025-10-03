#!/bin/bash

# Student Scholarship Portal Setup Script
# This script sets up the Django project with all necessary configurations

echo "🚀 Setting up Student Scholarship Portal..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Database setup
echo "🗄️ Setting up database..."
echo "Please ensure MySQL is running and create the database:"
echo "CREATE DATABASE scholarship_portal_db;"
echo "CREATE USER 'portal_user'@'localhost' IDENTIFIED BY 'your_password';"
echo "GRANT ALL PRIVILEGES ON scholarship_portal_db.* TO 'portal_user'@'localhost';"
echo "FLUSH PRIVILEGES;"
echo ""
read -p "Press Enter after creating the database..."

# Run migrations
echo "🔄 Running migrations..."
python manage.py makemigrations
python manage.py migrate

# Create superuser
echo "👤 Creating superuser..."
python manage.py createsuperuser

# Collect static files
echo "📂 Collecting static files..."
python manage.py collectstatic --noinput

# Create media directories
echo "📁 Creating media directories..."
mkdir -p media/profile_pictures
mkdir -p media/student_documents
mkdir -p media/institute_documents
mkdir -p media/grievance_documents
mkdir -p media/financial_reports

# Create logs directory
mkdir -p logs

echo "✅ Setup complete!"
echo "🌐 Run 'python manage.py runserver' to start the development server"
echo "📊 Access admin panel at: http://localhost:8000/admin/"
echo "📖 API documentation will be available at: http://localhost:8000/api/docs/"
