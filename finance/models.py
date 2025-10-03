from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from authentication.models import CustomUser
from students.models import Student, ScholarshipApplication
from institutes.models import Institute
from departments.models import Department


class ScholarshipScheme(models.Model):
    """Model for different scholarship schemes available"""
    
    SCHEME_TYPES = (
        ('government', 'Government'),
        ('institutional', 'Institutional'),
        ('private', 'Private'),
        ('international', 'International'),
    )
    
    ELIGIBILITY_TYPES = (
        ('merit', 'Merit-based'),
        ('need', 'Need-based'),
        ('minority', 'Minority'),
        ('sports', 'Sports'),
        ('arts', 'Arts & Culture'),
        ('research', 'Research'),
        ('disability', 'Disability'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    )
    
    name = models.CharField(max_length=200, db_index=True)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    description = models.TextField()
    scheme_type = models.CharField(max_length=20, choices=SCHEME_TYPES, db_index=True)
    eligibility_type = models.CharField(max_length=20, choices=ELIGIBILITY_TYPES, db_index=True)
    
    # Financial details
    min_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    max_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    total_budget = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    utilized_budget = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Eligibility criteria
    min_cgpa = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    min_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    max_family_income = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(0)]
    )
    
    # Date fields
    application_start_date = models.DateField()
    application_end_date = models.DateField()
    academic_year = models.CharField(max_length=10)  # e.g., "2024-25"
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    renewable = models.BooleanField(default=False)
    max_duration_years = models.PositiveIntegerField(default=1)
    
    # Tracking
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_schemes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def remaining_budget(self):
        return self.total_budget - self.utilized_budget
    
    @property
    def is_active(self):
        return (
            self.status == 'active' and 
            self.application_start_date <= timezone.now().date() <= self.application_end_date
        )
    
    class Meta:
        db_table = 'scholarship_schemes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['scheme_type', 'eligibility_type']),
            models.Index(fields=['academic_year', 'status']),
            models.Index(fields=['application_start_date', 'application_end_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(application_end_date__gte=models.F('application_start_date')),
                name='valid_application_dates'
            ),
            models.CheckConstraint(
                check=models.Q(max_amount__gte=models.F('min_amount')),
                name='valid_amount_range'
            ),
            models.CheckConstraint(
                check=models.Q(utilized_budget__lte=models.F('total_budget')),
                name='valid_budget_utilization'
            ),
        ]


class ScholarshipDisbursement(models.Model):
    """Model for tracking scholarship disbursements"""
    
    DISBURSEMENT_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('disbursed', 'Disbursed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    DISBURSEMENT_METHOD = (
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('cash', 'Cash'),
        ('fee_adjustment', 'Fee Adjustment'),
    )
    
    application = models.OneToOneField(ScholarshipApplication, on_delete=models.CASCADE, related_name='disbursement')
    scheme = models.ForeignKey(ScholarshipScheme, on_delete=models.CASCADE, related_name='disbursements')
    disbursement_id = models.CharField(max_length=30, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    disbursement_method = models.CharField(max_length=20, choices=DISBURSEMENT_METHOD)
    status = models.CharField(max_length=20, choices=DISBURSEMENT_STATUS, default='pending')
    bank_account_number = models.CharField(max_length=20, blank=True, null=True)
    bank_ifsc = models.CharField(max_length=11, blank=True, null=True)
    cheque_number = models.CharField(max_length=20, blank=True, null=True)
    transaction_reference = models.CharField(max_length=50, blank=True, null=True)
    disbursed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='disbursed_scholarships')
    disbursement_date = models.DateTimeField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.disbursement_id} - {self.application.student.student_id}"
    
    class Meta:
        db_table = 'scholarship_disbursements'
        ordering = ['-created_at']


class FinanceAdmin(models.Model):
    """Model for finance administrators"""
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='finance_admin_profile')
    employee_id = models.CharField(max_length=20, unique=True)
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='finance_admins', blank=True, null=True)
    designation = models.CharField(max_length=100)
    permissions = models.JSONField(default=dict, blank=True)  # Store specific permissions
    is_primary_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Finance Admin"
    
    class Meta:
        db_table = 'finance_admins'


class Budget(models.Model):
    """Model for budget allocation and tracking"""
    
    BUDGET_TYPES = (
        ('scholarship', 'Scholarship'),
        ('infrastructure', 'Infrastructure'),
        ('operational', 'Operational'),
        ('research', 'Research'),
        ('other', 'Other'),
    )
    
    name = models.CharField(max_length=200)
    budget_type = models.CharField(max_length=20, choices=BUDGET_TYPES)
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='budgets')
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    allocated_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    utilized_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    financial_year = models.CharField(max_length=20)  # e.g., "2023-24"
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_budgets')
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_budgets')
    approval_date = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def remaining_amount(self):
        return self.total_amount - self.utilized_amount
    
    def __str__(self):
        return f"{self.institute.name} - {self.name} - {self.financial_year}"
    
    class Meta:
        db_table = 'budgets'
        unique_together = ['institute', 'name', 'financial_year']
        ordering = ['-created_at']


class Transaction(models.Model):
    """Model for recording financial transactions"""
    
    TRANSACTION_TYPES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )
    
    TRANSACTION_CATEGORIES = (
        ('scholarship_disbursement', 'Scholarship Disbursement'),
        ('fee_collection', 'Fee Collection'),
        ('infrastructure', 'Infrastructure'),
        ('salary', 'Salary'),
        ('utilities', 'Utilities'),
        ('maintenance', 'Maintenance'),
        ('other', 'Other'),
    )
    
    transaction_id = models.CharField(max_length=30, unique=True)
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='transactions')
    budget = models.ForeignKey(Budget, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    category = models.CharField(max_length=30, choices=TRANSACTION_CATEGORIES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    reference_number = models.CharField(max_length=50, blank=True, null=True)
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    disbursement = models.ForeignKey(ScholarshipDisbursement, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    processed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='processed_transactions')
    transaction_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.transaction_id} - {self.transaction_type} - {self.amount}"
    
    class Meta:
        db_table = 'transactions'
        ordering = ['-transaction_date']


class FinancialReport(models.Model):
    """Model for generated financial reports"""
    
    REPORT_TYPES = (
        ('scholarship_summary', 'Scholarship Summary'),
        ('budget_utilization', 'Budget Utilization'),
        ('disbursement_report', 'Disbursement Report'),
        ('institute_financial', 'Institute Financial'),
        ('audit_report', 'Audit Report'),
    )
    
    REPORT_PERIODS = (
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half Yearly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom'),
    )
    
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='financial_reports', blank=True, null=True)
    report_period = models.CharField(max_length=20, choices=REPORT_PERIODS)
    start_date = models.DateField()
    end_date = models.DateField()
    generated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='generated_reports')
    report_file = models.FileField(upload_to='financial_reports/', blank=True, null=True)
    summary_data = models.JSONField(default=dict, blank=True)  # Store report summary
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.start_date} to {self.end_date}"
    
    class Meta:
        db_table = 'financial_reports'
        ordering = ['-created_at']
