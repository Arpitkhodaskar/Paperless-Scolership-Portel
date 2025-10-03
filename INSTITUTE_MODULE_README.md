# Institute Module Documentation

## Overview

The Institute Module provides comprehensive REST API endpoints for educational institute administration within the scholarship portal system. This module enables institute administrators to manage student applications, verify documents, track scholarship forms, generate reports, and perform various administrative tasks with role-based permissions.

## Features

### 🏛️ Institute Management
- **Institute Profile Management**: Update institute information, contact details, and settings
- **Admin User Management**: Manage institute administrators with role-based permissions
- **Document Management**: Upload and manage institute verification documents
- **Bank Account Management**: Manage institutional bank accounts for scholarship disbursements

### 📋 Application Management
- **Application Listing**: View all student scholarship applications with advanced filtering
- **Application Processing**: Approve, reject, or request additional documents
- **Bulk Operations**: Perform actions on multiple applications simultaneously
- **Application Tracking**: Detailed timeline and status tracking for each application
- **Comments System**: Add internal and external comments to applications

### 📊 Reporting & Analytics
- **Comprehensive Reports**: Generate various types of reports (summary, detailed, financial, trend analysis)
- **Dashboard Analytics**: Real-time dashboard with key metrics and charts
- **Export Functionality**: Export reports in CSV, PDF, and Excel formats
- **Performance Metrics**: Track processing times, approval rates, and efficiency metrics

### 👥 Student & Document Verification
- **Student Verification**: Verify student profiles and academic records
- **Document Verification**: Review and verify uploaded student documents
- **Bulk Document Processing**: Process multiple documents simultaneously
- **Verification Workflow**: Multi-level verification with compliance scoring

## API Endpoints

### Institute Management

#### List Student Applications
```http
GET /api/institutes/applications/
```

**Query Parameters:**
- `status`: Filter by application status (`pending_verification`, `approved`, `rejected`, `all`)
- `scholarship_type`: Filter by scholarship type
- `priority`: Filter by priority level (`low`, `medium`, `high`, `urgent`)
- `academic_year`: Filter by academic year
- `date_from`: Filter applications from date (YYYY-MM-DD)
- `date_to`: Filter applications to date (YYYY-MM-DD)
- `min_amount`: Minimum requested amount
- `max_amount`: Maximum requested amount
- `department`: Filter by department ID
- `course_level`: Filter by course level
- `show_overdue`: Show only overdue applications (true/false)
- `search`: Search in student ID, name, or application ID
- `ordering`: Order by field (`submitted_at`, `amount_requested`, `priority`, `status`)

**Response:**
```json
{
  "count": 150,
  "next": "http://api/institutes/applications/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "application_id": "APP2025ABC12345",
      "student_details": {
        "id": 101,
        "student_id": "STU2025001",
        "user_name": "John Doe",
        "user_email": "john.doe@email.com",
        "department_name": "Computer Science",
        "course_level": "undergraduate",
        "course_name": "B.Tech Computer Science",
        "academic_year": "3rd",
        "cgpa": 8.5,
        "is_active": true,
        "is_verified": true
      },
      "scholarship_type": "merit",
      "scholarship_name": "Merit-based Scholarship 2025",
      "amount_requested": 50000.00,
      "amount_approved": null,
      "status": "submitted",
      "priority": "medium",
      "reason": "Financial assistance required for continuing education",
      "submitted_at": "2025-01-15T10:30:00Z",
      "review_started_at": null,
      "review_completed_at": null,
      "processing_time_days": 3,
      "is_overdue": false,
      "eligibility_score": 85,
      "document_completeness_score": 90,
      "assigned_to_name": null,
      "reviewed_by_name": null,
      "documents_status": {
        "total_documents": 5,
        "verified_documents": 4,
        "pending_documents": 1,
        "rejected_documents": 0,
        "completeness_percentage": 90
      },
      "academic_year": "2024-25",
      "auto_eligible": false,
      "manual_review_required": true
    }
  ],
  "summary": {
    "total_applications": 150,
    "pending_verification": 25,
    "document_verification": 15,
    "eligibility_check": 10,
    "total_amount_requested": 7500000.00,
    "average_amount": 50000.00
  }
}
```

#### Approve/Reject Application
```http
POST /api/institutes/applications/{application_id}/approve/
```

**Request Body:**
```json
{
  "action": "approve",
  "remarks": "Application approved based on merit and financial need assessment",
  "internal_notes": "Student has excellent academic record and family income meets criteria",
  "approved_amount": 50000.00
}
```

**Response:**
```json
{
  "id": 1,
  "application_id": "APP2025ABC12345",
  "student_name": "John Doe",
  "scholarship_type": "merit",
  "amount_requested": 50000.00,
  "amount_approved": 50000.00,
  "status": "approved",
  "priority": "medium",
  "review_comments": "Application approved based on merit and financial need assessment",
  "rejection_reason": null,
  "approved_at": "2025-01-18T14:30:00Z",
  "rejected_at": null,
  "updated_at": "2025-01-18T14:30:00Z"
}
```

#### Bulk Application Actions
```http
PATCH /api/institutes/applications/bulk-action/
```

**Request Body:**
```json
{
  "application_ids": ["APP2025ABC12345", "APP2025DEF67890", "APP2025GHI11111"],
  "action": "approve",
  "remarks": "Bulk approval based on eligibility criteria review"
}
```

**Response:**
```json
{
  "message": "Bulk action completed. 3 applications processed.",
  "processed_count": 3,
  "failed_applications": []
}
```

#### Track Application Progress
```http
GET /api/institutes/applications/{application_id}/track/
```

**Response:**
```json
{
  "application": {
    "id": 1,
    "application_id": "APP2025ABC12345",
    "student_details": {...},
    "scholarship_type": "merit",
    "status": "approved",
    "submitted_at": "2025-01-15T10:30:00Z"
  },
  "timeline": [
    {
      "status": "draft",
      "timestamp": "2025-01-15T09:00:00Z",
      "description": "Application created",
      "user": "John Doe",
      "details": "Initial application for Merit-based Scholarship 2025"
    },
    {
      "status": "submitted",
      "timestamp": "2025-01-15T10:30:00Z",
      "description": "Application submitted",
      "user": "John Doe",
      "details": "Amount requested: ₹50,000"
    },
    {
      "status": "approved",
      "timestamp": "2025-01-18T14:30:00Z",
      "description": "Application approved",
      "user": "Institute Admin",
      "details": "Application approved based on merit and financial need assessment"
    }
  ],
  "document_status": {
    "total_documents": 5,
    "verified_documents": 5,
    "pending_documents": 0,
    "rejected_documents": 0,
    "documents": [
      {
        "document_type": "id_proof",
        "document_name": "Aadhar Card",
        "status": "verified",
        "is_verified": true,
        "uploaded_at": "2025-01-15T09:15:00Z",
        "verification_date": "2025-01-16T11:00:00Z",
        "rejection_reason": null
      }
    ]
  },
  "processing_stats": {
    "days_since_submission": 3,
    "processing_time": null,
    "is_overdue": false,
    "priority": "medium",
    "eligibility_score": 85,
    "document_completeness_score": 100
  },
  "next_steps": [
    "Process disbursement",
    "Send approval notification"
  ],
  "workflow_history": [
    {
      "application_id": "APP2025ABC12345",
      "action": "approve",
      "remarks": "Application approved based on merit and financial need assessment",
      "user": "admin@institute.edu",
      "timestamp": "2025-01-18T14:30:00Z"
    }
  ]
}
```

### Reports & Analytics

#### Generate Institute Reports
```http
GET /api/institutes/reports/
```

**Query Parameters:**
- `report_type`: Type of report (`summary`, `detailed`, `financial`, `monthly`, `department_wise`, `trend_analysis`)
- `date_from`: Start date for report (YYYY-MM-DD)
- `date_to`: End date for report (YYYY-MM-DD)
- `format`: Report format (`json`, `csv`, `pdf`)
- `department`: Filter by department ID
- `scholarship_type`: Filter by scholarship type

**Summary Report Response:**
```json
{
  "report_type": "summary",
  "institute": "Tech University",
  "generated_at": "2025-01-18T15:00:00Z",
  "total_applications": 150,
  "total_requested_amount": 7500000.00,
  "total_approved_amount": 5250000.00,
  "approval_rate": 65.33,
  "average_processing_time": 12.5,
  "status_breakdown": [
    {
      "status": "approved",
      "count": 98,
      "total_amount": 4900000.00,
      "avg_amount": 50000.00
    },
    {
      "status": "rejected",
      "count": 32,
      "total_amount": 1600000.00,
      "avg_amount": 50000.00
    },
    {
      "status": "pending",
      "count": 20,
      "total_amount": 1000000.00,
      "avg_amount": 50000.00
    }
  ],
  "type_breakdown": [
    {
      "scholarship_type": "merit",
      "count": 80,
      "total_amount": 4000000.00
    },
    {
      "scholarship_type": "need",
      "count": 50,
      "total_amount": 2500000.00
    },
    {
      "scholarship_type": "minority",
      "count": 20,
      "total_amount": 1000000.00
    }
  ],
  "monthly_trends": [
    {
      "month": "2024-12",
      "count": 25,
      "total_amount": 1250000.00
    },
    {
      "month": "2025-01",
      "count": 35,
      "total_amount": 1750000.00
    }
  ]
}
```

#### Institute Dashboard
```http
GET /api/institutes/dashboard/
```

**Response:**
```json
{
  "institute_name": "Tech University",
  "generated_at": "2025-01-18T15:00:00Z",
  "key_metrics": {
    "total_applications": 150,
    "pending_applications": 25,
    "approved_applications": 98,
    "rejected_applications": 32,
    "approval_rate": 65.33,
    "total_amount_requested": 7500000.00,
    "total_amount_approved": 4900000.00,
    "recent_applications": 15,
    "overdue_applications": 5
  },
  "charts": {
    "status_distribution": [
      {"status": "approved", "count": 98},
      {"status": "pending", "count": 25},
      {"status": "rejected", "count": 32}
    ],
    "monthly_trends": [
      {"month": "2024-08", "count": 20},
      {"month": "2024-09", "count": 25},
      {"month": "2024-10", "count": 30},
      {"month": "2024-11", "count": 28},
      {"month": "2024-12", "count": 25},
      {"month": "2025-01", "count": 35}
    ],
    "scholarship_types": [
      {"scholarship_type": "merit", "count": 80, "total_amount": 4000000.00},
      {"scholarship_type": "need", "count": 50, "total_amount": 2500000.00},
      {"scholarship_type": "minority", "count": 20, "total_amount": 1000000.00}
    ]
  },
  "alerts": {
    "overdue_count": 5,
    "pending_documents": 12,
    "high_priority_pending": 3
  }
}
```

### Document Verification

#### Verify Document
```http
POST /api/institutes/documents/verify/{document_id}/
```

**Request Body:**
```json
{
  "status": "verified",
  "verification_notes": "Document verified successfully. All details match records.",
  "compliance_score": 95
}
```

**Response:**
```json
{
  "message": "Document verified successfully",
  "verification_id": 123
}
```

#### Bulk Verify Documents
```http
POST /api/institutes/documents/bulk-verify/
```

**Request Body:**
```json
{
  "document_ids": [101, 102, 103, 104],
  "status": "verified",
  "verification_notes": "Bulk verification completed after review"
}
```

**Response:**
```json
{
  "message": "Bulk verification completed for 4 documents",
  "updated_count": 4
}
```

### Student Verification

#### Verify Student
```http
POST /api/institutes/students/{student_id}/verify/
```

**Request Body:**
```json
{
  "is_verified": true,
  "verification_notes": "Student profile verified. All academic records and documents are authentic."
}
```

**Response:**
```json
{
  "message": "Student verified successfully",
  "verification_notes": "Student profile verified. All academic records and documents are authentic."
}
```

#### Get Pending Students
```http
GET /api/institutes/students/pending-verification/
```

## Role-Based Permissions

### Permission Classes

1. **InstituteAdminPermission**: Basic institute admin access
2. **InstitutePrimaryAdminPermission**: Primary admin access for sensitive operations
3. **InstituteReportsPermission**: Reports and analytics access
4. **StudentVerificationPermission**: Student and document verification access
5. **ApplicationProcessingPermission**: Scholarship application processing access

### Permission Matrix

| Role | Applications | Reports | Student Verification | Document Management | Bulk Operations |
|------|--------------|---------|---------------------|---------------------|-----------------|
| Primary Admin | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| Admin Officer | ✅ Full | ✅ View | ✅ Full | ✅ Full | ✅ Limited |
| Scholarship Officer | ✅ Process | ✅ View | ❌ | ❌ | ❌ |
| Academic Officer | ✅ View | ✅ View | ✅ Full | ✅ Limited | ❌ |
| Registrar | ✅ Full | ✅ Full | ✅ Full | ✅ View | ✅ Full |

## Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
  "error": "Invalid data provided",
  "detail": "Application cannot be processed. Current status: completed",
  "validation_errors": {
    "approved_amount": ["This field is required for approve action"]
  }
}
```

#### 403 Forbidden
```json
{
  "error": "Permission denied",
  "detail": "Institute admin permission required"
}
```

#### 404 Not Found
```json
{
  "error": "Application not found",
  "detail": "No application found with ID: APP2025XYZ99999"
}
```

#### 500 Internal Server Error
```json
{
  "error": "Failed to process application",
  "detail": "Database connection error"
}
```

## Usage Examples

### Python/Django Client Example

```python
import requests
from rest_framework.authtoken.models import Token

# Get authentication token
token = Token.objects.get(user__email='admin@institute.edu')
headers = {'Authorization': f'Token {token.key}'}

# List pending applications
response = requests.get(
    'http://api/institutes/applications/',
    params={'status': 'pending_verification', 'priority': 'high'},
    headers=headers
)
applications = response.json()['results']

# Approve an application
for app in applications:
    if app['eligibility_score'] >= 80:
        approval_data = {
            'action': 'approve',
            'remarks': 'Auto-approved based on high eligibility score',
            'approved_amount': app['amount_requested']
        }
        
        response = requests.post(
            f"http://api/institutes/applications/{app['application_id']}/approve/",
            json=approval_data,
            headers=headers
        )
        
        if response.status_code == 200:
            print(f"Approved application {app['application_id']}")
```

### JavaScript/React Example

```javascript
// Service for API calls
class InstituteAPI {
  constructor(token) {
    this.token = token;
    this.baseURL = 'http://api/institutes';
  }

  async getApplications(filters = {}) {
    const params = new URLSearchParams(filters);
    const response = await fetch(`${this.baseURL}/applications/?${params}`, {
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      }
    });
    return response.json();
  }

  async approveApplication(applicationId, data) {
    const response = await fetch(`${this.baseURL}/applications/${applicationId}/approve/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });
    return response.json();
  }

  async generateReport(reportType, filters = {}) {
    const params = new URLSearchParams({report_type: reportType, ...filters});
    const response = await fetch(`${this.baseURL}/reports/?${params}`, {
      headers: {
        'Authorization': `Bearer ${this.token}`
      }
    });
    return response.json();
  }
}

// React component example
function ApplicationsList() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const api = new InstituteAPI(localStorage.getItem('token'));

  useEffect(() => {
    loadApplications();
  }, []);

  const loadApplications = async () => {
    try {
      const data = await api.getApplications({status: 'pending_verification'});
      setApplications(data.results);
    } catch (error) {
      console.error('Failed to load applications:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (applicationId) => {
    try {
      await api.approveApplication(applicationId, {
        action: 'approve',
        remarks: 'Approved by admin review'
      });
      loadApplications(); // Refresh list
    } catch (error) {
      console.error('Failed to approve application:', error);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h2>Pending Applications</h2>
      {applications.map(app => (
        <div key={app.id} className="application-card">
          <h3>{app.student_details.user_name}</h3>
          <p>Amount: ₹{app.amount_requested}</p>
          <p>Status: {app.status}</p>
          <button onClick={() => handleApprove(app.application_id)}>
            Approve
          </button>
        </div>
      ))}
    </div>
  );
}
```

### cURL Examples

```bash
# List applications with filtering
curl -X GET \
  "http://api/institutes/applications/?status=pending_verification&priority=high" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Approve application
curl -X POST \
  "http://api/institutes/applications/APP2025ABC12345/approve/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "remarks": "Application meets all criteria",
    "approved_amount": 50000.00
  }'

# Generate summary report
curl -X GET \
  "http://api/institutes/reports/?report_type=summary&date_from=2025-01-01" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Bulk approve applications
curl -X PATCH \
  "http://api/institutes/applications/bulk-action/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "application_ids": ["APP2025ABC12345", "APP2025DEF67890"],
    "action": "approve",
    "remarks": "Bulk approval after review"
  }'
```

## Performance Considerations

### Database Optimization
- **Indexes**: All frequently queried fields have database indexes
- **Query Optimization**: Uses `select_related` and `prefetch_related` for efficient queries
- **Pagination**: All list endpoints support pagination to handle large datasets
- **Caching**: Dashboard data is cached for 30 minutes to improve performance

### API Rate Limiting
- Institute APIs are rate-limited to prevent abuse
- Bulk operations have additional validation to prevent system overload
- Report generation is throttled for resource-intensive operations

### File Handling
- Document uploads are validated for size (max 10MB) and format
- Files are stored securely with proper access controls
- Large files use streaming for efficient memory usage

## Security Features

### Authentication & Authorization
- JWT token-based authentication
- Role-based access control with granular permissions
- Session management with token expiration

### Data Protection
- Sensitive data masking (bank account numbers)
- Audit logging for all administrative actions
- Input validation and sanitization
- SQL injection prevention

### File Security
- File type validation and virus scanning
- Secure file storage with access controls
- Document watermarking for verification

## Testing

### Unit Tests
```python
# Example test case
class InstituteApplicationsViewTestCase(TestCase):
    def setUp(self):
        self.institute = Institute.objects.create(name="Test Institute")
        self.admin_user = User.objects.create_user(
            email="admin@test.edu",
            password="testpass123"
        )
        self.institute_admin = InstituteAdmin.objects.create(
            user=self.admin_user,
            institute=self.institute,
            designation="Admin Officer"
        )
        self.client.force_authenticate(user=self.admin_user)

    def test_list_applications(self):
        response = self.client.get('/api/institutes/applications/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)

    def test_approve_application(self):
        application = ScholarshipApplication.objects.create(
            student=self.student,
            scholarship_type='merit',
            amount_requested=50000
        )
        
        data = {
            'action': 'approve',
            'remarks': 'Test approval',
            'approved_amount': 50000
        }
        
        response = self.client.post(
            f'/api/institutes/applications/{application.application_id}/approve/',
            data=data
        )
        
        self.assertEqual(response.status_code, 200)
        application.refresh_from_db()
        self.assertEqual(application.status, 'approved')
```

## Deployment

### Environment Variables
```bash
# Required environment variables
DATABASE_URL=postgresql://user:pass@localhost:5432/scholarship_db
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=api.scholarshipportal.edu,localhost

# Email settings for notifications
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@scholarshipportal.edu
EMAIL_HOST_PASSWORD=your-email-password

# File storage settings
MEDIA_ROOT=/var/www/media
STATIC_ROOT=/var/www/static

# Cache settings
REDIS_URL=redis://localhost:6379/0
```

### Docker Configuration
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "scholarship_portal.wsgi:application"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/scholarship_db
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=scholarship_db
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    
volumes:
  postgres_data:
```

## Monitoring & Logging

### Application Logging
```python
# logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/scholarship_portal/institute.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'institutes': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### Metrics Collection
- Application performance metrics
- API response times and error rates  
- User activity tracking
- Resource utilization monitoring

This comprehensive Institute Module provides a complete solution for educational institutions to manage scholarship applications, verify students and documents, generate reports, and perform administrative tasks through a secure and efficient REST API interface.
