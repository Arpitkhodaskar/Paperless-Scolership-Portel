from django.db import models
from authentication.models import CustomUser
from institutes.models import Institute


class Department(models.Model):
    """Model representing academic departments"""
    
    DEPARTMENT_TYPES = (
        ('academic', 'Academic'),
        ('administrative', 'Administrative'),
        ('support', 'Support'),
        ('research', 'Research'),
    )
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    institute = models.ForeignKey(Institute, on_delete=models.CASCADE, related_name='departments')
    department_type = models.CharField(max_length=20, choices=DEPARTMENT_TYPES, default='academic')
    description = models.TextField(blank=True, null=True)
    head_of_department = models.CharField(max_length=100, blank=True, null=True)
    hod_email = models.EmailField(blank=True, null=True)
    hod_phone = models.CharField(max_length=15, blank=True, null=True)
    office_location = models.CharField(max_length=200, blank=True, null=True)
    office_phone = models.CharField(max_length=15, blank=True, null=True)
    office_email = models.EmailField(blank=True, null=True)
    established_year = models.PositiveIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.institute.code} - {self.code} - {self.name}"
    
    class Meta:
        db_table = 'departments'
        unique_together = ['institute', 'code']
        ordering = ['name']


class Course(models.Model):
    """Model representing courses offered by departments"""
    
    COURSE_TYPES = (
        ('undergraduate', 'Undergraduate'),
        ('postgraduate', 'Postgraduate'),
        ('phd', 'PhD'),
        ('diploma', 'Diploma'),
        ('certificate', 'Certificate'),
    )
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')
    course_type = models.CharField(max_length=20, choices=COURSE_TYPES)
    duration_years = models.PositiveIntegerField()
    duration_semesters = models.PositiveIntegerField()
    total_seats = models.PositiveIntegerField()
    fee_per_semester = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    eligibility_criteria = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.department.code} - {self.code} - {self.name}"
    
    class Meta:
        db_table = 'courses'
        unique_together = ['department', 'code']
        ordering = ['name']


class DepartmentAdmin(models.Model):
    """Model for department administrators"""
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='department_admin_profile')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='admins')
    designation = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=20, unique=True)
    is_primary_admin = models.BooleanField(default=False)
    permissions = models.JSONField(default=dict, blank=True)  # Store specific permissions
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.department.name}"
    
    class Meta:
        db_table = 'department_admins'
        unique_together = ['department', 'user']


class Subject(models.Model):
    """Model representing subjects taught in courses"""
    
    SUBJECT_TYPES = (
        ('core', 'Core'),
        ('elective', 'Elective'),
        ('project', 'Project'),
        ('internship', 'Internship'),
        ('laboratory', 'Laboratory'),
    )
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='subjects')
    subject_type = models.CharField(max_length=20, choices=SUBJECT_TYPES)
    credits = models.PositiveIntegerField()
    semester = models.PositiveIntegerField()
    description = models.TextField(blank=True, null=True)
    syllabus = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.course.code} - {self.code} - {self.name}"
    
    class Meta:
        db_table = 'subjects'
        unique_together = ['course', 'code']
        ordering = ['semester', 'name']


class Faculty(models.Model):
    """Model representing faculty members"""
    
    DESIGNATION_CHOICES = (
        ('professor', 'Professor'),
        ('associate_professor', 'Associate Professor'),
        ('assistant_professor', 'Assistant Professor'),
        ('lecturer', 'Lecturer'),
        ('instructor', 'Instructor'),
    )
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='faculty_profile')
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='faculty')
    designation = models.CharField(max_length=30, choices=DESIGNATION_CHOICES)
    qualification = models.CharField(max_length=200)
    specialization = models.CharField(max_length=200, blank=True, null=True)
    experience_years = models.PositiveIntegerField(default=0)
    joining_date = models.DateField()
    office_hours = models.CharField(max_length=100, blank=True, null=True)
    research_interests = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name()}"
    
    class Meta:
        db_table = 'faculty'
        ordering = ['designation', 'user__last_name']
