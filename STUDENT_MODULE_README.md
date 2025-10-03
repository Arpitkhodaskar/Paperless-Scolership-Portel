# Student Module - Django REST Framework API

## Overview

The Student Module provides comprehensive REST API endpoints for student registration, authentication, profile management, document upload with validation, scholarship application submission, and status tracking. It includes MySQL database integration and JWT authentication.

## Features

### 🔐 **Authentication & Registration**
- **Student Registration** with complete profile setup
- **JWT Authentication** with access and refresh tokens
- **Login/Logout** functionality
- **Password Management** with validation
- **Profile Verification** by institute administrators

### 📄 **Document Management**
- **File Upload** with comprehensive validation
- **Multiple File Formats** support (PDF, JPG, PNG, DOC, DOCX)
- **File Size Validation** (max 10MB)
- **Document Verification** workflow
- **Document Status Tracking**

### 🎓 **Scholarship Applications**
- **Application Creation** with detailed validation
- **Multi-stage Workflow** (Draft → Submitted → Review → Approval)
- **Status Tracking** with timeline
- **Application Management** (Create, Update, Submit, Track)

### 👤 **Profile Management**
- **Complete Profile** with academic and personal information
- **Profile Updates** with validation
- **Academic Records** management
- **Family and Income** information

## API Endpoints

### Authentication Endpoints

#### Student Registration
```http
POST /api/students/register/
Content-Type: application/json

{
    "user_data": {
        "username": "john_doe",
        "email": "john@example.com",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": "9876543210"
    },
    "institute": 1,
    "department": 1,
    "course_level": "undergraduate",
    "course_name": "Computer Science",
    "academic_year": "2nd",
    "enrollment_date": "2023-08-15",
    "roll_number": "CS2023001",
    "admission_type": "regular",
    "category": "general",
    "father_name": "Robert Doe",
    "mother_name": "Mary Doe",
    "family_income": 500000,
    "permanent_address": "123 Main St, City, State",
    "current_address": "456 College St, City, State",
    "emergency_contact": "9876543211"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Student registered successfully",
    "data": {
        "student": {
            "student_id": "INST202300001",
            "user_details": {
                "username": "john_doe",
                "email": "john@example.com",
                "full_name": "John Doe"
            }
        },
        "tokens": {
            "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        }
    }
}
```

#### Student Login
```http
POST /api/students/login/
Content-Type: application/json

{
    "username_or_email": "john_doe",
    "password": "SecurePass123!"
}
```

### Profile Management Endpoints

#### Get Student Profile
```http
GET /api/students/profile/
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "success": true,
    "data": {
        "profile": {
            "student_id": "INST202300001",
            "user_details": {
                "username": "john_doe",
                "email": "john@example.com",
                "full_name": "John Doe",
                "phone_number": "9876543210"
            },
            "institute_details": {
                "name": "Example University",
                "code": "INST",
                "city": "Mumbai"
            },
            "verification_status": {
                "is_verified": true,
                "verification_date": "2023-08-20T10:30:00Z"
            }
        },
        "documents": [],
        "applications": [],
        "statistics": {
            "total_documents": 0,
            "verified_documents": 0,
            "total_applications": 0,
            "approved_applications": 0
        }
    }
}
```

#### Update Student Profile
```http
PUT /api/students/profile/update/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "user_data": {
        "first_name": "John",
        "last_name": "Doe Updated",
        "phone_number": "9876543210"
    },
    "family_income": 600000,
    "current_address": "New Address"
}
```

### Document Management Endpoints

#### Upload Document
```http
POST /api/students/documents/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

document_type: identity_proof
document_name: Aadhar Card
document_file: <file>
document_number: 1234-5678-9012
issue_date: 2020-01-15
issuing_authority: Government of India
description: Identity proof document
```

**Response:**
```json
{
    "success": true,
    "message": "Document uploaded successfully",
    "data": {
        "document": {
            "id": 1,
            "document_type": "identity_proof",
            "document_name": "Aadhar Card",
            "file_size_mb": 2.5,
            "is_verified": false,
            "uploaded_at": "2023-08-20T15:30:00Z"
        }
    }
}
```

#### Get All Documents
```http
GET /api/students/documents/
Authorization: Bearer <access_token>

# Optional query parameters:
# ?type=identity_proof
# ?verified=true
```

#### Update Document
```http
PUT /api/students/documents/1/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

document_name: Updated Aadhar Card
description: Updated description
```

#### Delete Document
```http
DELETE /api/students/documents/1/
Authorization: Bearer <access_token>
```

### Scholarship Application Endpoints

#### Create Application
```http
POST /api/students/applications/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "scholarship_type": "merit",
    "scholarship_name": "Merit Scholarship 2023",
    "amount_requested": 50000,
    "reason": "I am applying for this scholarship because I have maintained excellent academic performance with a CGPA of 9.2. My family's financial situation requires support to continue my education.",
    "additional_information": "Active in college activities and community service",
    "family_details": {
        "father_occupation": "Teacher",
        "mother_occupation": "Homemaker",
        "annual_income": 500000,
        "family_size": 4
    },
    "academic_details": {
        "cgpa": 9.2,
        "percentage": 92,
        "rank": 5
    },
    "academic_year": "2023-24"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Application created successfully",
    "data": {
        "application": {
            "application_id": "APPINST202300001",
            "status": "draft",
            "scholarship_type": "merit",
            "amount_requested": 50000,
            "created_at": "2023-08-20T16:00:00Z"
        }
    }
}
```

#### Get All Applications
```http
GET /api/students/applications/
Authorization: Bearer <access_token>

# Optional query parameters:
# ?status=draft
# ?type=merit
```

#### Submit Application
```http
POST /api/students/applications/APPINST202300001/submit/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "declaration": true
}
```

#### Track Application Status
```http
GET /api/students/applications/APPINST202300001/status/
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "success": true,
    "data": {
        "application_id": "APPINST202300001",
        "current_status": "under_review",
        "status_display": "Under Review",
        "timeline": [
            {
                "status": "draft",
                "description": "Application created",
                "timestamp": "2023-08-20T16:00:00Z",
                "completed": true
            },
            {
                "status": "submitted",
                "description": "Application submitted for review",
                "timestamp": "2023-08-20T18:00:00Z",
                "completed": true
            },
            {
                "status": "under_review",
                "description": "Review started",
                "timestamp": "2023-08-21T10:00:00Z",
                "completed": true,
                "reviewer": "Admin User"
            }
        ],
        "processing_time_days": 1,
        "next_action": "Under review by administrator"
    }
}
```

#### Dashboard Summary
```http
GET /api/students/dashboard/
Authorization: Bearer <access_token>
```

## Database Schema

### MySQL Configuration

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'scholarship_portal_db',
        'USER': 'scholarship_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        }
    }
}
```

### Key Models

#### Student Model
```python
class Student(models.Model):
    user = models.OneToOneField(CustomUser, related_name='student_profile')
    student_id = models.CharField(max_length=20, unique=True)
    institute = models.ForeignKey(Institute)
    department = models.ForeignKey(Department)
    course_level = models.CharField(choices=COURSE_LEVELS)
    course_name = models.CharField(max_length=200)
    academic_year = models.CharField(choices=ACADEMIC_YEARS)
    enrollment_date = models.DateField()
    roll_number = models.CharField(max_length=50)
    family_income = models.DecimalField(max_digits=10, decimal_places=2)
    # ... other fields
```

#### StudentDocument Model
```python
class StudentDocument(models.Model):
    student = models.ForeignKey(Student, related_name='documents')
    document_type = models.CharField(choices=DOCUMENT_TYPES)
    document_file = models.FileField(upload_to='documents/')
    file_size = models.PositiveIntegerField()
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True)
    # ... other fields
```

#### ScholarshipApplication Model
```python
class ScholarshipApplication(models.Model):
    student = models.ForeignKey(Student, related_name='scholarship_applications')
    application_id = models.CharField(max_length=20, unique=True)
    scholarship_type = models.CharField(choices=SCHOLARSHIP_TYPES)
    status = models.CharField(choices=APPLICATION_STATUS, default='draft')
    amount_requested = models.DecimalField(max_digits=10, decimal_places=2)
    submitted_at = models.DateTimeField(null=True)
    # ... other fields
```

## Validation Features

### File Upload Validation
- **File Size**: Maximum 10MB
- **File Types**: PDF, JPG, JPEG, PNG, DOC, DOCX
- **Security**: Checks for malicious files
- **Name Validation**: Validates file names for security

### Data Validation
- **Email**: Unique and format validation
- **Phone**: 10+ digit validation
- **Amount**: Range validation (0 to 10,00,000)
- **Dates**: Logical date validation
- **Required Fields**: Comprehensive field validation

### Business Logic Validation
- **Duplicate Applications**: Prevents multiple applications for same scholarship type
- **Document Requirements**: Ensures required documents before submission
- **Status Transitions**: Validates application status changes
- **Profile Completeness**: Checks profile completion percentage

## Security Features

### Authentication
- **JWT Tokens**: Secure token-based authentication
- **Token Refresh**: Automatic token refresh mechanism
- **Password Hashing**: Django's built-in password hashing
- **Session Management**: Secure session handling

### Authorization
- **Role-based Access**: Different permissions for different user types
- **Data Isolation**: Students can only access their own data
- **API Security**: Comprehensive permission checks

### File Security
- **Upload Validation**: Comprehensive file validation
- **Storage Security**: Secure file storage with proper permissions
- **Content Validation**: Basic content validation for uploaded files

## Performance Optimizations

### Database Optimizations
- **Indexes**: Optimized database indexes for common queries
- **Query Optimization**: Use of select_related and prefetch_related
- **Connection Pooling**: Database connection pooling support
- **Atomic Transactions**: Ensures data consistency

### API Optimizations
- **Pagination**: Built-in pagination for list endpoints
- **Filtering**: Django-filter integration for efficient filtering
- **Caching**: Ready for caching implementation
- **Serializer Optimization**: Efficient serialization with minimal queries

## Error Handling

### Comprehensive Error Responses
```json
{
    "success": false,
    "message": "Registration failed",
    "errors": {
        "user_data": {
            "email": ["A user with this email already exists."]
        },
        "family_income": ["Family income cannot be negative"]
    }
}
```

### Status Codes
- **200**: Success
- **201**: Created
- **400**: Bad Request (Validation errors)
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **500**: Internal Server Error

## Setup Instructions

### 1. Database Setup
```bash
# Create MySQL database
mysql -u root -p < mysql_setup.sql

# Run migrations
python manage.py makemigrations
python manage.py migrate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configuration
```bash
# Create .env file
cp .env.example .env

# Update database credentials in .env
DB_NAME=scholarship_portal_db
DB_USER=scholarship_user
DB_PASSWORD=your_password
```

### 4. Run Server
```bash
python manage.py runserver
```

## Testing

### API Testing with curl

#### Registration Test
```bash
curl -X POST http://localhost:8000/api/students/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "username": "testuser",
      "email": "test@example.com",
      "password": "TestPass123!",
      "confirm_password": "TestPass123!",
      "first_name": "Test",
      "last_name": "User",
      "phone_number": "9876543210"
    },
    "institute": 1,
    "department": 1,
    "course_level": "undergraduate",
    "course_name": "Computer Science",
    "academic_year": "2nd",
    "enrollment_date": "2023-08-15",
    "roll_number": "CS2023001",
    "admission_type": "regular",
    "category": "general",
    "father_name": "Test Father",
    "mother_name": "Test Mother",
    "family_income": 500000,
    "permanent_address": "Test Address",
    "current_address": "Test Current Address",
    "emergency_contact": "9876543211"
  }'
```

#### Login Test
```bash
curl -X POST http://localhost:8000/api/students/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "testuser",
    "password": "TestPass123!"
  }'
```

### Integration with Frontend

The API is designed to work seamlessly with modern frontend frameworks:

#### React/Vue.js Example
```javascript
// Login function
async function loginStudent(credentials) {
  const response = await fetch('/api/students/login/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials)
  });
  
  const data = await response.json();
  if (data.success) {
    localStorage.setItem('access_token', data.data.tokens.access);
    localStorage.setItem('refresh_token', data.data.tokens.refresh);
  }
  return data;
}

// API call with authentication
async function getProfile() {
  const token = localStorage.getItem('access_token');
  const response = await fetch('/api/students/profile/', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
}
```

## Monitoring and Logging

### Application Monitoring
- **Database Query Monitoring**: Track slow queries
- **API Response Times**: Monitor endpoint performance
- **Error Tracking**: Comprehensive error logging
- **User Activity**: Track user actions and patterns

### Log Files
- **Django Logs**: Application logs in logs/django.log
- **Database Logs**: MySQL query logs
- **Security Logs**: Authentication and authorization logs
- **File Upload Logs**: Document upload activity logs

## Future Enhancements

### Planned Features
- **Email Notifications**: Automated email notifications for status updates
- **SMS Alerts**: SMS notifications for important updates
- **Document OCR**: Automatic text extraction from uploaded documents
- **Advanced Analytics**: Detailed analytics and reporting
- **Mobile App API**: Enhanced API for mobile applications
- **Real-time Updates**: WebSocket support for real-time notifications

### Scalability Considerations
- **Microservices**: Ready for microservices architecture
- **Horizontal Scaling**: Database and application scaling support
- **CDN Integration**: File storage with CDN support
- **Cache Strategy**: Redis/Memcached integration ready

## Support and Documentation

For additional support and detailed API documentation, refer to:
- **Postman Collection**: Available in `docs/postman_collection.json`
- **OpenAPI Spec**: Available at `/api/docs/`
- **Database ER Diagram**: Available in `docs/database_schema.pdf`
- **Technical Documentation**: Available in `docs/technical_documentation.md`
