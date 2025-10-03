"""
MySQL Database Configuration and Setup Script for Student Scholarship Portal

This script provides the MySQL database configuration and setup instructions.
Run this script to configure the database for the Django application.
"""

import os
import sys
import django
from django.conf import settings
from django.core.management import execute_from_command_line
from django.db import connection
from django.core.management.base import BaseCommand


# MySQL Database Configuration for settings.py
MYSQL_DATABASE_CONFIG = """
# MySQL Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'scholarship_portal_db'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'your_mysql_password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
            'use_unicode': True,
        },
        'CONN_MAX_AGE': 60,
        'ATOMIC_REQUESTS': True,
    }
}

# Database connection pooling (optional)
# Uncomment if using django-db-pool
# DATABASES['default']['ENGINE'] = 'django_db_pool.backends.mysql'
# DATABASES['default']['POOL_OPTIONS'] = {
#     'POOL_SIZE': 10,
#     'MAX_OVERFLOW': 20,
#     'RECYCLE': 24 * 60 * 60,  # 24 hours
# }
"""

# Environment variables template for .env file
ENV_TEMPLATE = """
# Database Configuration
DB_NAME=scholarship_portal_db
DB_USER=root
DB_PASSWORD=your_mysql_password_here
DB_HOST=localhost
DB_PORT=3306

# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# JWT Configuration
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=10080

# Media and Static Files
MEDIA_ROOT=media/
STATIC_ROOT=staticfiles/
"""

# MySQL database creation script
MYSQL_SETUP_SCRIPT = """
-- MySQL Database Setup Script for Student Scholarship Portal
-- Run this script as MySQL root user

-- Create database
CREATE DATABASE IF NOT EXISTS scholarship_portal_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create application user
CREATE USER IF NOT EXISTS 'scholarship_user'@'localhost' IDENTIFIED BY 'scholarship_password_123';

-- Grant privileges
GRANT ALL PRIVILEGES ON scholarship_portal_db.* TO 'scholarship_user'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER ON scholarship_portal_db.* TO 'scholarship_user'@'localhost';

-- Flush privileges
FLUSH PRIVILEGES;

-- Use the database
USE scholarship_portal_db;

-- Show database info
SELECT 'Database created successfully!' as message;
SHOW DATABASES LIKE 'scholarship_portal_db';
"""

# Django management commands for setup
DJANGO_SETUP_COMMANDS = [
    'makemigrations',
    'makemigrations authentication',
    'makemigrations students',
    'makemigrations institutes',
    'makemigrations departments',
    'makemigrations finance',
    'makemigrations grievances',
    'migrate',
    'collectstatic --noinput',
]

# MySQL indexes for performance optimization
MYSQL_INDEXES_SCRIPT = """
-- Performance optimization indexes for Student Scholarship Portal

USE scholarship_portal_db;

-- Authentication indexes
CREATE INDEX idx_user_email ON authentication_customuser(email);
CREATE INDEX idx_user_type ON authentication_customuser(user_type);
CREATE INDEX idx_user_active ON authentication_customuser(is_active);

-- Student indexes
CREATE INDEX idx_student_id ON students_student(student_id);
CREATE INDEX idx_student_institute ON students_student(institute_id);
CREATE INDEX idx_student_department ON students_student(department_id);
CREATE INDEX idx_student_course_level ON students_student(course_level);
CREATE INDEX idx_student_academic_year ON students_student(academic_year);
CREATE INDEX idx_student_verified ON students_student(is_verified);
CREATE INDEX idx_student_enrollment ON students_student(enrollment_date);

-- Document indexes
CREATE INDEX idx_document_student ON students_studentdocument(student_id);
CREATE INDEX idx_document_type ON students_studentdocument(document_type);
CREATE INDEX idx_document_verified ON students_studentdocument(is_verified);
CREATE INDEX idx_document_uploaded ON students_studentdocument(uploaded_at);

-- Application indexes
CREATE INDEX idx_application_student ON students_scholarshipapplication(student_id);
CREATE INDEX idx_application_status ON students_scholarshipapplication(status);
CREATE INDEX idx_application_type ON students_scholarshipapplication(scholarship_type);
CREATE INDEX idx_application_created ON students_scholarshipapplication(created_at);
CREATE INDEX idx_application_submitted ON students_scholarshipapplication(submitted_at);
CREATE INDEX idx_application_year ON students_scholarshipapplication(academic_year);

-- Institute indexes
CREATE INDEX idx_institute_code ON institutes_institute(code);
CREATE INDEX idx_institute_verified ON institutes_institute(is_verified);
CREATE INDEX idx_institute_type ON institutes_institute(institute_type);
CREATE INDEX idx_institute_state ON institutes_institute(state);

-- Composite indexes for common queries
CREATE INDEX idx_student_institute_year ON students_student(institute_id, academic_year);
CREATE INDEX idx_application_student_status ON students_scholarshipapplication(student_id, status);
CREATE INDEX idx_document_student_type ON students_studentdocument(student_id, document_type);
CREATE INDEX idx_application_status_created ON students_scholarshipapplication(status, created_at);

-- Show created indexes
SELECT 'Indexes created successfully!' as message;
"""


def create_env_file():
    """Create .env file with template values"""
    env_path = os.path.join(os.getcwd(), '.env')
    if not os.path.exists(env_path):
        with open(env_path, 'w') as f:
            f.write(ENV_TEMPLATE)
        print(f"✅ Created .env file at {env_path}")
        print("⚠️  Please update the database credentials in .env file")
    else:
        print("ℹ️  .env file already exists")


def create_mysql_script():
    """Create MySQL setup script file"""
    script_path = os.path.join(os.getcwd(), 'mysql_setup.sql')
    with open(script_path, 'w') as f:
        f.write(MYSQL_SETUP_SCRIPT)
    print(f"✅ Created MySQL setup script at {script_path}")
    
    # Create indexes script
    indexes_path = os.path.join(os.getcwd(), 'mysql_indexes.sql')
    with open(indexes_path, 'w') as f:
        f.write(MYSQL_INDEXES_SCRIPT)
    print(f"✅ Created MySQL indexes script at {indexes_path}")


def run_django_setup():
    """Run Django setup commands"""
    print("🚀 Running Django setup commands...")
    
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scholarship_portal.settings')
    django.setup()
    
    for command in DJANGO_SETUP_COMMANDS:
        try:
            print(f"Running: python manage.py {command}")
            execute_from_command_line(['manage.py'] + command.split())
            print(f"✅ {command} completed successfully")
        except Exception as e:
            print(f"❌ Error running {command}: {str(e)}")
            continue


def check_database_connection():
    """Check if database connection is working"""
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False


def create_superuser():
    """Create Django superuser"""
    print("👤 Creating Django superuser...")
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@scholarship.portal',
                password='admin123',
                first_name='System',
                last_name='Administrator',
                user_type='system_admin'
            )
            print("✅ Superuser 'admin' created with password 'admin123'")
            print("⚠️  Please change the default password after first login")
        else:
            print("ℹ️  Superuser already exists")
    except Exception as e:
        print(f"❌ Error creating superuser: {str(e)}")


def main():
    """Main setup function"""
    print("🏗️  Student Scholarship Portal - Database Setup")
    print("=" * 50)
    
    # Create configuration files
    create_env_file()
    create_mysql_script()
    
    print("\n📋 Setup Instructions:")
    print("1. Install MySQL server if not already installed")
    print("2. Update database credentials in .env file")
    print("3. Run mysql_setup.sql script in MySQL:")
    print("   mysql -u root -p < mysql_setup.sql")
    print("4. Install Python requirements:")
    print("   pip install -r requirements.txt")
    print("5. Run Django migrations:")
    print("   python manage.py migrate")
    print("6. Create superuser:")
    print("   python manage.py createsuperuser")
    print("7. Run development server:")
    print("   python manage.py runserver")
    
    # Ask if user wants to run Django setup
    response = input("\n🤔 Do you want to run Django setup now? (y/n): ")
    if response.lower() == 'y':
        if check_database_connection():
            run_django_setup()
            create_superuser()
            print("\n🎉 Setup completed successfully!")
            print("🌐 You can now start the development server with:")
            print("   python manage.py runserver")
        else:
            print("❌ Please fix database connection issues first")
    
    print("\n📚 API Documentation:")
    print("- Student Registration: POST /api/students/register/")
    print("- Student Login: POST /api/students/login/")
    print("- Profile Management: GET/PUT /api/students/profile/")
    print("- Document Upload: POST /api/students/documents/")
    print("- Application Management: GET/POST /api/students/applications/")
    print("- Status Tracking: GET /api/students/applications/{id}/status/")


if __name__ == "__main__":
    main()
