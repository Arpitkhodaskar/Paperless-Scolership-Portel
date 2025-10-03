# Student Scholarship Portal

A comprehensive Django-based web application for managing student scholarships, built with Django REST Framework, JWT authentication, and MySQL database.

## 🚀 Features

### Core Features
- **Multi-user Authentication**: JWT-based authentication with role-based access control
- **Student Management**: Complete student profile management with academic records
- **Institute Management**: Comprehensive institute and department administration
- **Scholarship System**: End-to-end scholarship application and disbursement process
- **Finance Management**: Budget tracking, disbursement management, and financial reporting
- **Grievance System**: Complete grievance handling with ticketing system
- **Document Management**: Secure file upload and management system

### User Roles
- **Students**: Apply for scholarships, upload documents, track applications
- **Institute Admins**: Manage institute data, student records, and applications
- **Department Admins**: Handle department-specific operations and student management
- **Finance Admins**: Manage budgets, process disbursements, generate reports
- **Grievance Admins**: Handle student grievances and support tickets
- **Super Admins**: System-wide administration and management

## 🏗️ Project Structure

```
scholarship_portal/
├── manage.py
├── requirements.txt
├── README.md
├── scholarship_portal/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── authentication/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── students/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── institutes/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── departments/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── finance/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── grievances/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── static/
├── media/
├── templates/
└── logs/
```

## 🛠️ Technology Stack

- **Backend**: Django 4.2.7, Django REST Framework 3.14.0
- **Database**: MySQL 8.0+
- **Authentication**: JWT (djangorestframework-simplejwt)
- **File Storage**: Local file system (configurable for cloud storage)
- **API Documentation**: drf-yasg (Swagger/OpenAPI)
- **Image Processing**: Pillow
- **Development**: Django Debug Toolbar, pytest

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.8+
- MySQL 8.0+
- pip (Python package manager)
- Virtual environment (recommended)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd scholarship_portal
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup

#### Create MySQL Database
```sql
CREATE DATABASE scholarship_portal_db;
CREATE USER 'portal_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON scholarship_portal_db.* TO 'portal_user'@'localhost';
FLUSH PRIVILEGES;
```

#### Update Database Configuration
Edit `scholarship_portal/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'scholarship_portal_db',
        'USER': 'portal_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'sql_mode': 'traditional',
        }
    }
}
```

### 5. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser
```bash
python manage.py createsuperuser
```

### 7. Collect Static Files
```bash
python manage.py collectstatic
```

### 8. Run Development Server
```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## 📊 Database Schema

### Key Models

#### Authentication
- **CustomUser**: Extended user model with role-based access
- **UserProfile**: Additional user profile information

#### Students
- **Student**: Student academic information
- **StudentDocument**: Document management
- **AcademicRecord**: Academic performance tracking
- **ScholarshipApplication**: Scholarship applications

#### Institutes & Departments
- **Institute**: Educational institution details
- **Department**: Academic departments
- **Course**: Course information
- **Faculty**: Faculty management

#### Finance
- **ScholarshipScheme**: Available scholarship schemes
- **ScholarshipDisbursement**: Payment processing
- **Budget**: Budget allocation and tracking
- **Transaction**: Financial transaction records

#### Grievances
- **Grievance**: Student complaint system
- **GrievanceCategory**: Categorization system
- **GrievanceComment**: Communication tracking
- **FAQ**: Frequently asked questions

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `GET /api/auth/profile/` - Get user profile
- `PUT /api/auth/profile/update/` - Update profile

### Students
- `GET /api/students/profile/` - Get student profile
- `PUT /api/students/profile/update/` - Update student profile
- `GET /api/students/documents/` - Get documents
- `POST /api/students/documents/` - Upload document
- `GET /api/students/scholarship-applications/` - Get applications
- `POST /api/students/scholarship-applications/` - Create application

### Finance
- `GET /api/finance/schemes/` - Get scholarship schemes
- `GET /api/finance/disbursements/` - Get disbursements
- `GET /api/finance/budgets/` - Get budgets
- `GET /api/finance/transactions/` - Get transactions

### Grievances
- `GET /api/grievances/` - Get grievances
- `POST /api/grievances/create/` - Create grievance
- `GET /api/grievances/{id}/` - Get grievance details
- `GET /api/grievances/categories/` - Get categories

## 🔒 Security Features

- JWT-based authentication
- Role-based access control
- CORS configuration
- File upload validation
- SQL injection protection
- XSS protection
- CSRF protection

## 📁 File Storage

### Local Storage Structure
```
media/
├── profile_pictures/
├── student_documents/
├── institute_documents/
├── grievance_documents/
└── financial_reports/
```

### Storage Configuration
Files are stored locally by default. For production, configure cloud storage:
```python
# AWS S3 Configuration (optional)
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = 'your-access-key'
AWS_SECRET_ACCESS_KEY = 'your-secret-key'
AWS_STORAGE_BUCKET_NAME = 'your-bucket-name'
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test students

# Run with pytest
pytest
```

### Test Coverage
```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

## 🚀 Deployment

### Production Settings
1. Set `DEBUG = False`
2. Configure secure `SECRET_KEY`
3. Set up proper `ALLOWED_HOSTS`
4. Configure production database
5. Set up static file serving
6. Configure email backend
7. Set up logging

### Docker Deployment (Optional)
```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "scholarship_portal.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## 📈 Monitoring & Logging

### Logging Configuration
Logs are stored in `logs/django.log` and include:
- Application errors
- Database queries
- Authentication events
- File upload activities

### Performance Monitoring
- Django Debug Toolbar (development)
- Sentry integration (production)
- Database query optimization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Run quality checks
6. Submit a pull request

### Code Quality
```bash
# Format code
black .
isort .

# Lint code
flake8 .

# Run tests
python manage.py test
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the FAQ section in the grievances module

## 🔄 Version History

- **v1.0.0** - Initial release with core functionality
- **v1.1.0** - Enhanced grievance system
- **v1.2.0** - Advanced financial reporting
- **v2.0.0** - Multi-institute support

## 🎯 Future Enhancements

- Mobile application
- Real-time notifications
- Advanced analytics dashboard
- Integration with payment gateways
- Multi-language support
- AI-powered grievance categorization
- Blockchain-based certificate verification
