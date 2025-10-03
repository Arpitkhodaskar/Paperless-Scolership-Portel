from django.db import models
from authentication.models import CustomUser


class Institute(models.Model):
    """Model representing educational institutes"""
    
    INSTITUTE_TYPES = (
        ('university', 'University'),
        ('college', 'College'),
        ('school', 'School'),
        ('technical', 'Technical Institute'),
        ('medical', 'Medical College'),
        ('engineering', 'Engineering College'),
        ('arts', 'Arts College'),
        ('commerce', 'Commerce College'),
        ('other', 'Other'),
    )
    
    ACCREDITATION_TYPES = (
        ('ugc', 'UGC'),
        ('aicte', 'AICTE'),
        ('mci', 'MCI'),
        ('bar_council', 'Bar Council'),
        ('naac', 'NAAC'),
        ('nba', 'NBA'),
        ('other', 'Other'),
    )
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    institute_type = models.CharField(max_length=20, choices=INSTITUTE_TYPES)
    established_year = models.PositiveIntegerField()
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    postal_code = models.CharField(max_length=10)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField()
    website = models.URLField(blank=True, null=True)
    accreditation = models.CharField(max_length=20, choices=ACCREDITATION_TYPES, blank=True, null=True)
    accreditation_grade = models.CharField(max_length=10, blank=True, null=True)
    principal_name = models.CharField(max_length=100, blank=True, null=True)
    principal_email = models.EmailField(blank=True, null=True)
    principal_phone = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        db_table = 'institutes'
        ordering = ['name']


class InstituteAdmin(models.Model):
    """Model for institute administrators"""
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='institute_admin_profile')
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='admins')
    designation = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=20, unique=True)
    is_primary_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.institute.name}"
    
    class Meta:
        db_table = 'institute_admins'
        unique_together = ['institute', 'user']


class InstituteBankAccount(models.Model):
    """Bank account details for institutes"""
    
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='bank_accounts')
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=100)
    branch_name = models.CharField(max_length=100)
    ifsc_code = models.CharField(max_length=11)
    account_type = models.CharField(max_length=20, choices=[
        ('savings', 'Savings'),
        ('current', 'Current'),
        ('institutional', 'Institutional'),
    ])
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.institute.name} - {self.account_number}"
    
    class Meta:
        db_table = 'institute_bank_accounts'


class InstituteDocument(models.Model):
    """Documents related to institutes"""
    
    DOCUMENT_TYPES = (
        ('affiliation_certificate', 'Affiliation Certificate'),
        ('registration_certificate', 'Registration Certificate'),
        ('accreditation_certificate', 'Accreditation Certificate'),
        ('pan_card', 'PAN Card'),
        ('tax_exemption', 'Tax Exemption Certificate'),
        ('bank_statement', 'Bank Statement'),
        ('other', 'Other'),
    )
    
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    document_name = models.CharField(max_length=200)
    document_file = models.FileField(upload_to='institute_documents/')
    description = models.TextField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_institute_documents')
    verification_date = models.DateTimeField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.institute.name} - {self.document_name}"
    
    class Meta:
        db_table = 'institute_documents'
        ordering = ['-uploaded_at']
