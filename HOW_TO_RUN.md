# 🚀 How to Run the Django Scholarship Portal

This guide provides step-by-step instructions to set up and run the Scholarship Portal project locally and in production.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Setup (Recommended)](#docker-setup-recommended)
4. [Manual Setup](#manual-setup)
5. [Database Setup](#database-setup)
6. [Running the Application](#running-the-application)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### Required Software:
- **Python 3.9+** (3.11 recommended)
- **MySQL 8.0+** or **PostgreSQL 12+**
- **Redis** (for caching and background tasks)
- **Node.js 16+** (for frontend)
- **Git**

### Optional (for Docker setup):
- **Docker** and **Docker Compose**

## 🐳 Docker Setup (Recommended)

This is the easiest way to run the project with all dependencies.

### 1. Clone the Repository
```bash
git clone https://github.com/Arpitkhodaskar/Paperless-Scolership-Portel.git
cd Paperless-Scolership-Portel
```

### 2. Environment Configuration
```bash
# Copy environment file
cp .env.example .env

# Edit the .env file with your settings
# For local development, you can use the default values
```

### 3. Build and Run with Docker
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 4. Initialize Database
```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Create notification templates
docker-compose exec web python manage.py create_notification_templates
```

### 5. Access the Application
- **Web Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin/
- **API Documentation**: http://localhost:8000/api/docs/
- **Celery Monitoring**: http://localhost:5555

## 🛠️ Manual Setup

If you prefer to set up everything manually without Docker.

### 1. Clone and Setup Repository
```bash
git clone https://github.com/Arpitkhodaskar/Paperless-Scolership-Portel.git
cd Paperless-Scolership-Portel
```

### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Database Setup (MySQL)

#### Install MySQL Server
- **Windows**: Download from MySQL official website
- **macOS**: `brew install mysql`
- **Ubuntu**: `sudo apt install mysql-server`

#### Create Database
```sql
-- Connect to MySQL
mysql -u root -p

-- Create database
CREATE DATABASE scholarship_portal_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user (optional)
CREATE USER 'scholarship_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON scholarship_portal_db.* TO 'scholarship_user'@'localhost';
FLUSH PRIVILEGES;
```

### 5. Redis Setup

#### Install Redis
- **Windows**: Download from Redis website or use WSL
- **macOS**: `brew install redis`
- **Ubuntu**: `sudo apt install redis-server`

#### Start Redis
```bash
# Start Redis server
redis-server

# Or as a service
# macOS: brew services start redis
# Ubuntu: sudo systemctl start redis-server
```

### 6. Environment Configuration
```bash
# Copy environment file
cp .env.example .env
```

Edit the `.env` file:
```bash
# Basic Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
DATABASE_URL=mysql://scholarship_user:your_password@localhost:3306/scholarship_portal_db

# Redis Configuration
REDIS_URL=redis://localhost:6379/1

# Email Configuration (for development)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@localhost
```

### 7. Database Migration
```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Create notification templates
python manage.py create_notification_templates

# Load initial data (if available)
python manage.py loaddata fixtures/initial_data.json
```

## 🚀 Running the Application

### Development Server
```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Start Django development server
python manage.py runserver

# The application will be available at http://127.0.0.1:8000
```

### Background Tasks (Celery)
Open new terminal windows for each:

```bash
# Terminal 1: Celery Worker
celery -A scholarship_portal worker -l info

# Terminal 2: Celery Beat (for scheduled tasks)
celery -A scholarship_portal beat -l info

# Terminal 3: Celery Flower (monitoring) - Optional
celery -A scholarship_portal flower
```

### Frontend Development (if using React)
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Frontend will be available at http://localhost:3000
```

## 🗄️ Database Setup

### MySQL Configuration
```sql
-- Create additional databases for testing
CREATE DATABASE scholarship_portal_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Grant permissions
GRANT ALL PRIVILEGES ON scholarship_portal_test.* TO 'scholarship_user'@'localhost';
```

### Sample Data (Optional)
```bash
# Create sample data
python manage.py shell

# In Django shell:
from django.contrib.auth.models import User
from students.models import Student
from institutes.models import Institute

# Create sample institute
institute = Institute.objects.create(
    name="Sample University",
    code="SU001",
    email="admin@sampleuniversity.edu",
    phone="1234567890"
)

# Create sample user and student
user = User.objects.create_user(
    username="student001",
    email="student@example.com",
    password="password123",
    first_name="John",
    last_name="Doe"
)

student = Student.objects.create(
    user=user,
    student_id="STU001",
    institute=institute,
    phone="9876543210"
)
```

## 🌐 Production Deployment

### Option 1: Automated Deployment Script
```bash
# Make script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh deploy

# Update existing deployment
./deploy.sh update

# Check status
./deploy.sh status
```

### Option 2: Manual Production Setup
```bash
# Set production environment
export DJANGO_SETTINGS_MODULE=scholarship_portal.settings.production

# Install production dependencies
pip install gunicorn psycopg2-binary

# Collect static files
python manage.py collectstatic --noinput

# Run with Gunicorn
gunicorn scholarship_portal.wsgi:application --bind 0.0.0.0:8000
```

## 🔧 Development Commands

### Useful Django Commands
```bash
# Create new Django app
python manage.py startapp app_name

# Make migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Django shell
python manage.py shell

# Run tests
python manage.py test

# Check for issues
python manage.py check
```

### Database Commands
```bash
# Reset database (careful!)
python manage.py flush

# Dump data
python manage.py dumpdata > backup.json

# Load data
python manage.py loaddata backup.json

# Database shell
python manage.py dbshell
```

### Celery Commands
```bash
# Start worker
celery -A scholarship_portal worker -l info

# Start beat scheduler
celery -A scholarship_portal beat -l info

# Purge all tasks
celery -A scholarship_portal purge

# Check active tasks
celery -A scholarship_portal inspect active

# Monitor with Flower
celery -A scholarship_portal flower --port=5555
```

## 🐛 Troubleshooting

### Common Issues and Solutions

#### 1. Database Connection Error
```bash
# Check MySQL is running
sudo systemctl status mysql

# Check credentials in .env file
# Ensure database exists
mysql -u root -p -e "SHOW DATABASES;"
```

#### 2. Redis Connection Error
```bash
# Check Redis is running
redis-cli ping

# Should return "PONG"
# If not, start Redis:
redis-server
```

#### 3. Permission Errors
```bash
# Fix file permissions
chmod +x deploy.sh
chmod +x docker-entrypoint.sh

# Fix directory permissions
sudo chown -R $USER:$USER .
```

#### 4. Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
python manage.py runserver 8001
```

#### 5. Migration Errors
```bash
# Reset migrations (careful!)
python manage.py migrate --fake-initial

# Or reset specific app
python manage.py migrate app_name zero
python manage.py migrate app_name
```

#### 6. Static Files Not Loading
```bash
# Collect static files
python manage.py collectstatic --clear

# Check STATIC_URL in settings
# Ensure web server serves static files
```

### Environment-Specific Issues

#### Development
```bash
# Enable debug mode
DEBUG=True

# Use console email backend
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Use SQLite for quick setup (not recommended for production)
DATABASE_URL=sqlite:///db.sqlite3
```

#### Production
```bash
# Disable debug
DEBUG=False

# Use production database
DATABASE_URL=mysql://user:pass@host:port/db

# Configure email backend
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
```

## 📚 API Usage Examples

### Authentication
```bash
# Register user
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'

# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}'

# Use token in subsequent requests
curl -X GET http://localhost:8000/api/students/profile/ \
  -H "Authorization: Bearer <your-access-token>"
```

### Testing Endpoints
```bash
# Health check
curl http://localhost:8000/health/

# API root
curl http://localhost:8000/api/

# Admin panel
# Visit http://localhost:8000/admin/
```

## 🔒 Security Checklist

### Before Going Live:
- [ ] Change SECRET_KEY and JWT_SIGNING_KEY
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS
- [ ] Setup HTTPS/SSL
- [ ] Configure firewall
- [ ] Setup monitoring
- [ ] Configure backups
- [ ] Review user permissions

## 📞 Support

### Getting Help:
1. Check this README first
2. Review Django documentation
3. Check project issues on GitHub
4. Review deployment logs
5. Test with minimal configuration

### Useful Resources:
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Docker Documentation](https://docs.docker.com/)

---

**Happy Coding! 🚀**

Your Django Scholarship Portal should now be running successfully!
