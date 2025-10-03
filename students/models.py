from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from authentication.models import CustomUser
from institutes.models import Institute
from departments.models import Department


class Student(models.Model):
    """Student model with academic information"""
    
    COURSE_LEVELS = (
        ('undergraduate', 'Undergraduate'),
        ('postgraduate', 'Postgraduate'),
        ('phd', 'PhD'),
        ('diploma', 'Diploma'),
    )
    
    ACADEMIC_YEARS = (
        ('1st', '1st Year'),
        ('2nd', '2nd Year'),
        ('3rd', '3rd Year'),
        ('4th', '4th Year'),
        ('5th', '5th Year'),
    )
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(
        max_length=20, 
        unique=True, 
        db_index=True,
        validators=[RegexValidator(
            regex=r'^[A-Z0-9]{8,20}$',
            message='Student ID must be 8-20 characters long and contain only uppercase letters and numbers'
        )]
    )
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='students')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='students')
    course_level = models.CharField(max_length=20, choices=COURSE_LEVELS, db_index=True)
    course_name = models.CharField(max_length=200, db_index=True)
    academic_year = models.CharField(max_length=10, choices=ACADEMIC_YEARS, db_index=True)
    enrollment_date = models.DateField()
    graduation_date = models.DateField(blank=True, null=True)
    cgpa = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    
    # Additional student information
    roll_number = models.CharField(max_length=20, blank=True, null=True)
    admission_type = models.CharField(
        max_length=20,
        choices=[
            ('regular', 'Regular'),
            ('lateral', 'Lateral Entry'),
            ('management', 'Management'),
            ('nri', 'NRI'),
            ('other', 'Other'),
        ],
        default='regular'
    )
    category = models.CharField(
        max_length=20,
        choices=[
            ('general', 'General'),
            ('obc', 'OBC'),
            ('sc', 'SC'),
            ('st', 'ST'),
            ('ews', 'EWS'),
            ('other', 'Other'),
        ],
        blank=True,
        null=True
    )
    
    # Family information
    father_name = models.CharField(max_length=100, blank=True, null=True)
    mother_name = models.CharField(max_length=100, blank=True, null=True)
    guardian_name = models.CharField(max_length=100, blank=True, null=True)
    family_income = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(0)]
    )
    
    # Contact information
    permanent_address = models.TextField(blank=True, null=True)
    current_address = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=15, blank=True, null=True)
    
    # Status tracking
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='verified_students'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student_id} - {self.user.get_full_name()}"
    
    @property
    def current_semester(self):
        """Calculate current semester based on enrollment date and academic year"""
        if self.enrollment_date:
            years_enrolled = (timezone.now().date() - self.enrollment_date).days // 365
            return min(years_enrolled * 2 + 1, 8)  # Assuming max 8 semesters
        return 1
    
    def save(self, *args, **kwargs):
        # Auto-generate student ID if not provided
        if not self.student_id:
            self.student_id = self.generate_student_id()
        super().save(*args, **kwargs)
    
    def generate_student_id(self):
        """Generate unique student ID"""
        import uuid
        prefix = f"{self.institute.code[:3]}{self.department.code[:2]}"
        suffix = str(uuid.uuid4().hex[:6]).upper()
        return f"{prefix}{suffix}"
    
    class Meta:
        db_table = 'students'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['institute', 'department']),
            models.Index(fields=['course_level', 'academic_year']),
            models.Index(fields=['enrollment_date']),
            models.Index(fields=['is_active', 'is_verified']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(graduation_date__gte=models.F('enrollment_date')),
                name='valid_graduation_date'
            ),
            models.CheckConstraint(
                check=models.Q(cgpa__gte=0) & models.Q(cgpa__lte=10),
                name='valid_cgpa_range'
            ),
        ]


class DocumentVerification(models.Model):
    """Model to track document verification process"""
    
    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
        ('resubmission_required', 'Resubmission Required'),
    )
    
    VERIFICATION_LEVEL = (
        ('level_1', 'Level 1 - Basic'),
        ('level_2', 'Level 2 - Detailed'),
        ('level_3', 'Level 3 - Final'),
    )
    
    document = models.OneToOneField('StudentDocument', on_delete=models.CASCADE, related_name='verification')
    status = models.CharField(max_length=30, choices=VERIFICATION_STATUS, default='pending')
    verification_level = models.CharField(max_length=10, choices=VERIFICATION_LEVEL, default='level_1')
    
    # Verification details
    verified_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='document_verifications'
    )
    verification_date = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    verification_notes = models.TextField(blank=True, null=True)
    
    # Verification checklist (JSON field to store verification criteria)
    verification_checklist = models.JSONField(default=dict, blank=True)
    compliance_score = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Auto-verification flags
    auto_verified = models.BooleanField(default=False)
    manual_review_required = models.BooleanField(default=False)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.document.document_name} - {self.status}"
    
    class Meta:
        db_table = 'document_verifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'verification_level']),
            models.Index(fields=['verified_by', 'verification_date']),
        ]


class StudentDocument(models.Model):
    """Documents uploaded by students with enhanced validation"""
    
    DOCUMENT_TYPES = (
        ('id_proof', 'ID Proof'),
        ('address_proof', 'Address Proof'),
        ('academic_transcript', 'Academic Transcript'),
        ('income_certificate', 'Income Certificate'),
        ('caste_certificate', 'Caste Certificate'),
        ('bank_statement', 'Bank Statement'),
        ('passport_photo', 'Passport Photo'),
        ('birth_certificate', 'Birth Certificate'),
        ('migration_certificate', 'Migration Certificate'),
        ('transfer_certificate', 'Transfer Certificate'),
        ('character_certificate', 'Character Certificate'),
        ('medical_certificate', 'Medical Certificate'),
        ('scholarship_certificate', 'Previous Scholarship Certificate'),
        ('other', 'Other'),
    )
    
    DOCUMENT_STATUS = (
        ('uploaded', 'Uploaded'),
        ('pending_verification', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES, db_index=True)
    document_name = models.CharField(max_length=200)
    document_file = models.FileField(
        upload_to='student_documents/',
        validators=[
            # Add file size validator (max 10MB)
            # FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])
        ]
    )
    
    # Document metadata
    file_size = models.PositiveIntegerField(blank=True, null=True)  # in bytes
    file_format = models.CharField(max_length=10, blank=True, null=True)
    document_number = models.CharField(max_length=50, blank=True, null=True)  # Document ID/Number
    issue_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    issuing_authority = models.CharField(max_length=200, blank=True, null=True)
    
    # Verification and status
    status = models.CharField(max_length=30, choices=DOCUMENT_STATUS, default='uploaded')
    description = models.TextField(blank=True, null=True)
    is_mandatory = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='verified_documents'
    )
    verification_date = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Version control
    version = models.PositiveIntegerField(default=1)
    replaced_document = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='replacement_documents'
    )
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.student_id} - {self.document_name}"
    
    @property
    def is_expired(self):
        """Check if document has expired"""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0
    
    def save(self, *args, **kwargs):
        # Auto-detect file format and size
        if self.document_file:
            self.file_format = self.document_file.name.split('.')[-1].lower()
            if hasattr(self.document_file.file, 'size'):
                self.file_size = self.document_file.file.size
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'student_documents'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['student', 'document_type']),
            models.Index(fields=['status', 'is_verified']),
            models.Index(fields=['uploaded_at']),
            models.Index(fields=['expiry_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(expiry_date__gte=models.F('issue_date')),
                name='valid_document_dates'
            ),
            models.CheckConstraint(
                check=models.Q(version__gte=1),
                name='valid_version_number'
            ),
        ]


class AcademicRecord(models.Model):
    """Academic records of students"""
    
    SEMESTER_CHOICES = (
        ('1st', '1st Semester'),
        ('2nd', '2nd Semester'),
        ('3rd', '3rd Semester'),
        ('4th', '4th Semester'),
        ('5th', '5th Semester'),
        ('6th', '6th Semester'),
        ('7th', '7th Semester'),
        ('8th', '8th Semester'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='academic_records')
    academic_year = models.CharField(max_length=20)  # e.g., "2023-24"
    semester = models.CharField(max_length=15, choices=SEMESTER_CHOICES)
    gpa = models.DecimalField(max_digits=4, decimal_places=2)
    total_credits = models.IntegerField()
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.student_id} - {self.academic_year} - {self.semester}"
    
    class Meta:
        db_table = 'academic_records'
        unique_together = ['student', 'academic_year', 'semester']
        ordering = ['-academic_year', '-semester']


class ScholarshipApplication(models.Model):
    """Enhanced scholarship applications with workflow management"""
    
    APPLICATION_STATUS = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('document_verification', 'Document Verification'),
        ('eligibility_check', 'Eligibility Check'),
        ('approved', 'Approved'),
        ('partially_approved', 'Partially Approved'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
        ('disbursed', 'Disbursed'),
        ('completed', 'Completed'),
    )
    
    SCHOLARSHIP_TYPES = (
        ('merit', 'Merit-based'),
        ('need', 'Need-based'),
        ('minority', 'Minority'),
        ('sports', 'Sports'),
        ('arts', 'Arts'),
        ('research', 'Research'),
        ('disability', 'Disability'),
        ('first_generation', 'First Generation'),
        ('girl_child', 'Girl Child'),
        ('rural', 'Rural Area'),
        ('other', 'Other'),
    )
    
    PRIORITY_LEVELS = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='scholarship_applications')
    application_id = models.CharField(
        max_length=30, 
        unique=True, 
        db_index=True,
        validators=[RegexValidator(
            regex=r'^APP[A-Z0-9]{8,25}$',
            message='Application ID must start with APP followed by alphanumeric characters'
        )]
    )
    
    # Scholarship details
    scholarship_type = models.CharField(max_length=20, choices=SCHOLARSHIP_TYPES, db_index=True)
    scholarship_name = models.CharField(max_length=200)
    scheme_reference = models.CharField(max_length=50, blank=True, null=True)  # Reference to external scheme
    
    # Financial details
    amount_requested = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(1)]
    )
    amount_approved = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(0)]
    )
    academic_year = models.CharField(max_length=10, blank=True, null=True)
    
    # Application content
    reason = models.TextField()
    additional_information = models.TextField(blank=True, null=True)
    family_details = models.JSONField(default=dict, blank=True)  # Store family information
    academic_details = models.JSONField(default=dict, blank=True)  # Store academic information
    
    # Status and workflow
    status = models.CharField(max_length=30, choices=APPLICATION_STATUS, default='draft', db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    # Workflow tracking
    submitted_at = models.DateTimeField(blank=True, null=True)
    review_started_at = models.DateTimeField(blank=True, null=True)
    review_completed_at = models.DateTimeField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    rejected_at = models.DateTimeField(blank=True, null=True)
    
    # Assignment and review
    assigned_to = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_applications'
    )
    reviewed_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_applications'
    )
    approved_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_applications'
    )
    
    # Review details
    review_comments = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Compliance and eligibility
    eligibility_score = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    document_completeness_score = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    auto_eligible = models.BooleanField(default=False)
    manual_review_required = models.BooleanField(default=True)
    
    # Additional metadata
    application_source = models.CharField(
        max_length=20,
        choices=[
            ('web', 'Web Portal'),
            ('mobile', 'Mobile App'),
            ('offline', 'Offline'),
            ('bulk_upload', 'Bulk Upload'),
        ],
        default='web'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.application_id} - {self.student.student_id}"
    
    @property
    def processing_time(self):
        """Calculate processing time from submission to completion"""
        if self.submitted_at and self.review_completed_at:
            return (self.review_completed_at - self.submitted_at).days
        return None
    
    @property
    def is_overdue(self):
        """Check if application is overdue for review"""
        if self.submitted_at and self.status in ['submitted', 'under_review']:
            days_pending = (timezone.now() - self.submitted_at).days
            return days_pending > 30  # 30 days SLA
        return False
    
    def save(self, *args, **kwargs):
        # Auto-generate application ID if not provided
        if not self.application_id:
            self.application_id = self.generate_application_id()
        
        # Update status timestamps
        if self.status == 'submitted' and not self.submitted_at:
            self.submitted_at = timezone.now()
        elif self.status == 'under_review' and not self.review_started_at:
            self.review_started_at = timezone.now()
        elif self.status in ['approved', 'rejected'] and not self.review_completed_at:
            self.review_completed_at = timezone.now()
            if self.status == 'approved':
                self.approved_at = timezone.now()
            elif self.status == 'rejected':
                self.rejected_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def generate_application_id(self):
        """Generate unique application ID"""
        import uuid
        current_year = timezone.now().year
        random_part = str(uuid.uuid4().hex[:8]).upper()
        return f"APP{current_year}{random_part}"
    
    class Meta:
        db_table = 'scholarship_applications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['scholarship_type', 'academic_year']),
            models.Index(fields=['submitted_at', 'status']),
            models.Index(fields=['student', 'status']),
            models.Index(fields=['assigned_to', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount_requested__gt=0),
                name='positive_requested_amount'
            ),
            models.CheckConstraint(
                check=models.Q(amount_approved__gte=0),
                name='non_negative_approved_amount'
            ),
            models.CheckConstraint(
                check=models.Q(eligibility_score__gte=0) & models.Q(eligibility_score__lte=100),
                name='valid_eligibility_score'
            ),
        ]
