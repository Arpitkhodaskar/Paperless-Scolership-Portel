# Django Models Documentation for Student Scholarship Portal

## Overview
This document provides a comprehensive overview of all Django models in the Student Scholarship Portal, including relationships, validations, constraints, and MySQL-specific optimizations.

## Core Models Structure

### 1. Authentication Models (`authentication/models.py`)

#### CustomUser
**Purpose**: Extended Django User model with role-based access control

**Key Features**:
- Role-based user types (student, admin, etc.)
- Profile picture support
- Email verification system
- Phone number validation

**Fields**:
```python
user_type = CharField(choices=USER_TYPES, default='student')
phone_number = CharField(max_length=15, validators=[phone_validator])
profile_picture = ImageField(upload_to='profile_pictures/')
is_verified = BooleanField(default=False)
```

**Relationships**:
- OneToOne with UserProfile
- OneToOne with Student (reverse: student_profile)
- OneToOne with various admin models

**MySQL Optimizations**:
- Index on user_type for fast role-based queries
- Index on email for authentication
- Custom table name: `auth_users`

#### UserProfile
**Purpose**: Extended profile information for users

**Key Features**:
- Demographic information
- Address details
- Emergency contacts

---

### 2. Institute Models (`institutes/models.py`)

#### Institute
**Purpose**: Educational institution management

**Key Features**:
- Multiple institute types (university, college, etc.)
- Accreditation tracking
- Contact information management
- Geographic data

**Fields**:
```python
name = CharField(max_length=200)
code = CharField(max_length=20, unique=True, db_index=True)
institute_type = CharField(choices=INSTITUTE_TYPES, db_index=True)
accreditation = CharField(choices=ACCREDITATION_TYPES)
```

**Relationships**:
- OneToMany with Department
- OneToMany with Student
- OneToMany with InstituteAdmin

**MySQL Optimizations**:
- Unique constraint on code
- Index on institute_type
- Index on city, state for geographic queries

#### InstituteAdmin
**Purpose**: Institute administrator management

#### InstituteBankAccount
**Purpose**: Banking details for institutes

**Key Features**:
- Multiple bank accounts per institute
- Primary account designation
- IFSC validation

#### InstituteDocument
**Purpose**: Institute document management

---

### 3. Department Models (`departments/models.py`)

#### Department
**Purpose**: Academic department management

**Fields**:
```python
name = CharField(max_length=200)
code = CharField(max_length=20)
institute = ForeignKey(Institute, on_delete=CASCADE)
```

**Relationships**:
- ManyToOne with Institute
- OneToMany with Course
- OneToMany with Student

**Constraints**:
- Unique together: ['institute', 'code']

#### Course
**Purpose**: Academic course management

**Key Features**:
- Course level tracking (undergraduate, postgraduate, etc.)
- Duration and fee management
- Seat capacity

#### Subject
**Purpose**: Individual subject management

#### Faculty
**Purpose**: Faculty member profiles

---

### 4. Student Models (`students/models.py`)

#### Student
**Purpose**: Core student profile with academic information

**Enhanced Features**:
- Auto-generated student ID with validation
- CGPA validation (0-10 range)
- Family information tracking
- Category-based classification
- Verification workflow

**Fields**:
```python
student_id = CharField(
    max_length=20, 
    unique=True, 
    validators=[RegexValidator(r'^[A-Z0-9]{8,20}$')]
)
cgpa = DecimalField(
    max_digits=4, 
    decimal_places=2,
    validators=[MinValueValidator(0), MaxValueValidator(10)]
)
family_income = DecimalField(
    max_digits=10, 
    decimal_places=2,
    validators=[MinValueValidator(0)]
)
```

**Relationships**:
- OneToOne with CustomUser
- ManyToOne with Institute
- ManyToOne with Department
- OneToMany with StudentDocument
- OneToMany with ScholarshipApplication

**MySQL Optimizations**:
```python
class Meta:
    indexes = [
        Index(fields=['institute', 'department']),
        Index(fields=['course_level', 'academic_year']),
        Index(fields=['is_active', 'is_verified']),
    ]
    constraints = [
        CheckConstraint(
            check=Q(graduation_date__gte=F('enrollment_date')),
            name='valid_graduation_date'
        ),
        CheckConstraint(
            check=Q(cgpa__gte=0) & Q(cgpa__lte=10),
            name='valid_cgpa_range'
        ),
    ]
```

#### DocumentVerification
**Purpose**: Document verification workflow management

**Key Features**:
- Multi-level verification process
- Compliance scoring (0-100)
- Auto-verification capabilities
- Verification checklist (JSON field)

**Fields**:
```python
status = CharField(choices=VERIFICATION_STATUS, default='pending')
verification_level = CharField(choices=VERIFICATION_LEVEL)
compliance_score = PositiveIntegerField(
    validators=[MinValueValidator(0), MaxValueValidator(100)]
)
verification_checklist = JSONField(default=dict)
```

#### StudentDocument
**Purpose**: Enhanced document management with metadata

**Enhanced Features**:
- File size and format tracking
- Document expiry management
- Version control system
- Advanced validation

**Fields**:
```python
document_type = CharField(choices=DOCUMENT_TYPES, db_index=True)
file_size = PositiveIntegerField()  # bytes
file_format = CharField(max_length=10)
document_number = CharField(max_length=50)  # Official document number
issue_date = DateField()
expiry_date = DateField()
version = PositiveIntegerField(default=1)
```

**Relationships**:
- ManyToOne with Student
- OneToOne with DocumentVerification
- Self-referencing for document versions

#### ScholarshipApplication
**Purpose**: Comprehensive scholarship application management

**Enhanced Features**:
- Multi-stage workflow (12 status types)
- Auto-ID generation with validation
- Eligibility scoring system
- Processing time tracking
- SLA monitoring

**Fields**:
```python
application_id = CharField(
    validators=[RegexValidator(r'^APP[A-Z0-9]{8,25}$')]
)
amount_requested = DecimalField(
    validators=[MinValueValidator(1)]
)
eligibility_score = PositiveIntegerField(
    validators=[MinValueValidator(0), MaxValueValidator(100)]
)
family_details = JSONField(default=dict)
academic_details = JSONField(default=dict)
```

**Workflow Tracking**:
```python
submitted_at = DateTimeField()
review_started_at = DateTimeField()
review_completed_at = DateTimeField()
approved_at = DateTimeField()
```

---

### 5. Finance Models (`finance/models.py`)

#### ScholarshipScheme
**Purpose**: Scholarship scheme management with budget tracking

**Enhanced Features**:
- Multi-criteria eligibility checking
- Budget utilization tracking
- Date-based activation
- CGPA and income limits

**Fields**:
```python
min_amount = DecimalField(validators=[MinValueValidator(0)])
max_amount = DecimalField(validators=[MinValueValidator(0)])
total_budget = DecimalField(validators=[MinValueValidator(0)])
min_cgpa = DecimalField(
    validators=[MinValueValidator(0), MaxValueValidator(10)]
)
max_family_income = DecimalField(validators=[MinValueValidator(0)])
```

**Constraints**:
```python
constraints = [
    CheckConstraint(
        check=Q(application_end_date__gte=F('application_start_date')),
        name='valid_application_dates'
    ),
    CheckConstraint(
        check=Q(max_amount__gte=F('min_amount')),
        name='valid_amount_range'
    ),
]
```

#### ScholarshipDisbursement
**Purpose**: Payment processing and tracking

**Enhanced Features**:
- Multiple disbursement methods
- Bank detail validation
- Transaction reference tracking
- Approval workflow

**Fields**:
```python
disbursement_id = CharField(unique=True, db_index=True)
sanctioned_amount = DecimalField(validators=[MinValueValidator(0)])
disbursed_amount = DecimalField(validators=[MinValueValidator(0)])
deduction_amount = DecimalField(default=0, validators=[MinValueValidator(0)])
```

#### Budget
**Purpose**: Financial budget allocation and tracking

**Features**:
- Multi-type budget categories
- Utilization percentage calculation
- Approval workflow
- Financial year tracking

#### Transaction
**Purpose**: Complete financial transaction recording

**Features**:
- Auto-generated transaction IDs
- Multi-category classification
- Audit trail maintenance
- Reference number tracking

#### FinancialReport
**Purpose**: Financial reporting and analytics

---

### 6. Grievance Models (`grievances/models.py`)

#### Grievance
**Purpose**: Student complaint management system

**Enhanced Features**:
- Priority-based categorization
- SLA tracking with expected resolution dates
- Escalation management
- Satisfaction rating system

**Fields**:
```python
grievance_id = CharField(unique=True, db_index=True)
priority = CharField(choices=PRIORITY_CHOICES, default='medium')
satisfaction_rating = IntegerField(choices=[(1, '1 - Very Dissatisfied'), ...])
expected_resolution_date = DateTimeField()
```

**Workflow Management**:
- Assignment to specific users
- Status change logging
- Escalation tracking
- Resolution summary

#### GrievanceCategory
**Purpose**: Categorization and SLA management

#### GrievanceComment
**Purpose**: Communication tracking

#### FAQ
**Purpose**: Frequently asked questions management

---

## Key Design Patterns

### 1. Validation Strategy
- **Field-level validation**: Using Django validators for data integrity
- **Model-level validation**: Custom clean methods for complex business rules
- **Database constraints**: CheckConstraints for data consistency

### 2. Relationship Design
- **Soft deletes**: Using SET_NULL for important references
- **Cascade deletes**: Only for true parent-child relationships
- **Related names**: Consistent naming convention for reverse relationships

### 3. MySQL Optimizations

#### Indexing Strategy
```python
# Composite indexes for common query patterns
Index(fields=['institute', 'department'])
Index(fields=['status', 'priority'])
Index(fields=['created_at', 'status'])

# Single field indexes for filtering
db_index=True on frequently queried fields
```

#### Constraints
```python
# Data integrity constraints
CheckConstraint(check=Q(end_date__gte=F('start_date')))
CheckConstraint(check=Q(amount__gt=0))

# Unique constraints
unique_together = ['institute', 'code']
```

#### Table Names
- Custom table names for better database organization
- Consistent naming convention across all models

### 4. JSON Field Usage
- **Flexible data storage**: For varying data structures
- **Configuration storage**: Permissions, preferences, checklists
- **Audit information**: Change logs and metadata

### 5. Audit Trail Implementation
- **Creation timestamps**: auto_now_add=True
- **Modification timestamps**: auto_now=True
- **User tracking**: created_by, updated_by fields
- **Status change logs**: Separate models for tracking changes

## Performance Considerations

### 1. Query Optimization
- Proper use of select_related and prefetch_related
- Database indexes on frequently queried fields
- Composite indexes for multi-field queries

### 2. File Storage
- Organized upload paths
- File size validation
- Format validation
- Metadata tracking

### 3. Caching Strategy
- Model-level caching for lookup data
- Query result caching for expensive operations
- File metadata caching

## Security Features

### 1. Data Validation
- Input sanitization through validators
- File upload restrictions
- SQL injection prevention through ORM

### 2. Access Control
- Role-based permissions
- Field-level access control
- Object-level permissions

### 3. Audit Logging
- User action tracking
- Data change history
- Access attempt logging

This model design provides a robust foundation for the Student Scholarship Portal with proper relationships, validations, and MySQL optimizations for performance and data integrity.
