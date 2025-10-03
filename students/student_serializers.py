from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone
from django.db import transaction
from .models import Student, StudentDocument, ScholarshipApplication, AcademicRecord
from authentication.models import CustomUser
from institutes.models import Institute
from departments.models import Department


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration during student registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'password', 'confirm_password',
            'first_name', 'last_name', 'phone_number'
        )
    
    def validate_email(self, value):
        """Validate email is unique"""
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate_username(self, value):
        """Validate username is unique and format"""
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        return value
    
    def validate_phone_number(self, value):
        """Validate phone number format"""
        if value and len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits long.")
        if value and not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        return value
    
    def validate(self, attrs):
        """Validate passwords match"""
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    
    def create(self, validated_data):
        """Create user account"""
        validated_data.pop('confirm_password')
        validated_data['user_type'] = 'student'
        validated_data['is_active'] = True
        
        user = CustomUser.objects.create_user(**validated_data)
        return user


class StudentRegistrationSerializer(serializers.ModelSerializer):
    """Complete student registration serializer"""
    user_data = UserRegistrationSerializer(write_only=True)
    
    class Meta:
        model = Student
        fields = (
            'user_data', 'institute', 'department', 'course_level', 
            'course_name', 'academic_year', 'enrollment_date', 
            'roll_number', 'admission_type', 'category',
            'father_name', 'mother_name', 'guardian_name',
            'family_income', 'permanent_address', 'current_address',
            'emergency_contact'
        )
    
    def validate_family_income(self, value):
        """Validate family income"""
        if value and value < 0:
            raise serializers.ValidationError("Family income cannot be negative")
        if value and value > 10000000:  # 1 crore
            raise serializers.ValidationError("Family income seems unreasonably high")
        return value
    
    def validate_roll_number(self, value):
        """Validate roll number uniqueness within institute"""
        institute = self.initial_data.get('institute')
        if institute and Student.objects.filter(
            roll_number=value, 
            institute_id=institute
        ).exists():
            raise serializers.ValidationError(
                "A student with this roll number already exists in this institute"
            )
        return value
    
    def validate_enrollment_date(self, value):
        """Validate enrollment date"""
        if value > timezone.now().date():
            raise serializers.ValidationError("Enrollment date cannot be in the future")
        return value
    
    def create(self, validated_data):
        """Create student with user account"""
        user_data = validated_data.pop('user_data')
        
        with transaction.atomic():
            # Create user account
            user_serializer = UserRegistrationSerializer(data=user_data)
            if user_serializer.is_valid():
                user = user_serializer.save()
            else:
                raise serializers.ValidationError({'user_data': user_serializer.errors})
            
            # Generate student ID
            institute = validated_data['institute']
            year = validated_data['enrollment_date'].year
            count = Student.objects.filter(
                institute=institute,
                enrollment_date__year=year
            ).count() + 1
            
            student_id = f"{institute.code}{year}{count:04d}"
            
            # Create student profile
            validated_data['user'] = user
            validated_data['student_id'] = student_id
            
            student = Student.objects.create(**validated_data)
            return student


class StudentLoginSerializer(serializers.Serializer):
    """Student login serializer"""
    username_or_email = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validate login credentials"""
        username_or_email = attrs.get('username_or_email')
        password = attrs.get('password')
        
        if username_or_email and password:
            # Try to find user by username or email
            user = None
            if '@' in username_or_email:
                try:
                    user_obj = CustomUser.objects.get(email=username_or_email)
                    user = authenticate(username=user_obj.username, password=password)
                except CustomUser.DoesNotExist:
                    pass
            else:
                user = authenticate(username=username_or_email, password=password)
            
            if not user:
                raise serializers.ValidationError("Invalid login credentials")
            
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled")
            
            if user.user_type != 'student':
                raise serializers.ValidationError("Invalid account type for student login")
            
            # Check if student profile exists
            if not hasattr(user, 'student_profile'):
                raise serializers.ValidationError("Student profile not found")
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError("Must include username/email and password")


class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating student profile"""
    
    class Meta:
        model = Student
        fields = (
            'course_level', 'course_name', 'academic_year',
            'father_name', 'mother_name', 'guardian_name',
            'family_income', 'permanent_address', 'current_address',
            'emergency_contact'
        )
    
    def validate_family_income(self, value):
        """Validate family income"""
        if value and value < 0:
            raise serializers.ValidationError("Family income cannot be negative")
        return value


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile information"""
    
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'phone_number')
    
    def validate_phone_number(self, value):
        """Validate phone number format"""
        if value and len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits long.")
        if value and not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        return value


class StudentDocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer for document upload with comprehensive validation"""
    
    class Meta:
        model = StudentDocument
        fields = (
            'document_type', 'document_name', 'document_file',
            'description', 'document_number', 'issue_date',
            'expiry_date', 'issuing_authority'
        )
    
    def validate_document_file(self, value):
        """Comprehensive file validation"""
        if not isinstance(value, UploadedFile):
            return value
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size must be less than {max_size // (1024*1024)}MB. Current size: {value.size // (1024*1024)}MB"
            )
        
        # Check minimum file size (1KB)
        min_size = 1024
        if value.size < min_size:
            raise serializers.ValidationError("File is too small. Minimum size is 1KB")
        
        # Check file extension
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']
        file_extension = value.name.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type '{file_extension}' not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Check for malicious content
        dangerous_extensions = ['exe', 'bat', 'cmd', 'scr', 'pif', 'jar']
        if file_extension in dangerous_extensions:
            raise serializers.ValidationError("This file type is not allowed for security reasons")
        
        # Check file name for suspicious characters
        import re
        if not re.match(r'^[a-zA-Z0-9._\-\s()]+$', value.name):
            raise serializers.ValidationError("File name contains invalid characters")
        
        return value
    
    def validate_document_number(self, value):
        """Validate document number format"""
        if value and len(value.strip()) < 3:
            raise serializers.ValidationError("Document number must be at least 3 characters long")
        return value
    
    def validate_issue_date(self, value):
        """Validate issue date"""
        if value and value > timezone.now().date():
            raise serializers.ValidationError("Issue date cannot be in the future")
        return value
    
    def validate_expiry_date(self, value):
        """Validate expiry date"""
        issue_date = self.initial_data.get('issue_date')
        if value and issue_date:
            if isinstance(issue_date, str):
                from datetime import datetime
                issue_date = datetime.strptime(issue_date, '%Y-%m-%d').date()
            if value <= issue_date:
                raise serializers.ValidationError("Expiry date must be after issue date")
        return value
    
    def create(self, validated_data):
        """Create document for current student"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'student_profile'):
            validated_data['student'] = request.user.student_profile
            
            # Set file format and size
            file = validated_data.get('document_file')
            if file:
                validated_data['file_format'] = file.name.split('.')[-1].lower()
                validated_data['file_size'] = file.size
        
        return super().create(validated_data)


class ScholarshipApplicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating scholarship applications with validation"""
    
    class Meta:
        model = ScholarshipApplication
        fields = (
            'scholarship_type', 'scholarship_name', 'amount_requested',
            'reason', 'additional_information', 'family_details',
            'academic_details', 'academic_year'
        )
    
    def validate_amount_requested(self, value):
        """Validate requested amount"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        if value > 1000000:  # 10 lakh
            raise serializers.ValidationError("Amount seems unreasonably high. Maximum allowed is ₹10,00,000")
        return value
    
    def validate_reason(self, value):
        """Validate reason field"""
        if len(value.strip()) < 50:
            raise serializers.ValidationError("Please provide a detailed reason (minimum 50 characters)")
        return value
    
    def validate_scholarship_name(self, value):
        """Validate scholarship name"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Scholarship name must be at least 5 characters long")
        return value
    
    def validate(self, attrs):
        """Additional validation"""
        # Check if student already has an application for the same scholarship type in current year
        request = self.context.get('request')
        if request and hasattr(request.user, 'student_profile'):
            student = request.user.student_profile
            existing_app = ScholarshipApplication.objects.filter(
                student=student,
                scholarship_type=attrs['scholarship_type'],
                academic_year=attrs['academic_year'],
                status__in=['draft', 'submitted', 'under_review', 'approved']
            ).exists()
            
            if existing_app:
                raise serializers.ValidationError(
                    "You already have an active application for this scholarship type in the current academic year"
                )
        
        return attrs
    
    def create(self, validated_data):
        """Create application for current student"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'student_profile'):
            student = request.user.student_profile
            validated_data['student'] = student
            
            # Generate application ID
            year = timezone.now().year
            count = ScholarshipApplication.objects.filter(
                student__institute=student.institute,
                created_at__year=year
            ).count() + 1
            
            application_id = f"APP{student.institute.code}{year}{count:05d}"
            validated_data['application_id'] = application_id
        
        return super().create(validated_data)


class ScholarshipApplicationSerializer(serializers.ModelSerializer):
    """Complete serializer for scholarship applications with all details"""
    
    student_details = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_scholarship_type_display', read_only=True)
    processing_time = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = ScholarshipApplication
        fields = '__all__'
        read_only_fields = (
            'student', 'application_id', 'created_at', 'updated_at',
            'submitted_at', 'review_started_at', 'review_completed_at',
            'approved_at', 'rejected_at', 'assigned_to', 'reviewed_by',
            'approved_by', 'eligibility_score', 'document_completeness_score'
        )
    
    def get_student_details(self, obj):
        return {
            'student_id': obj.student.student_id,
            'name': obj.student.user.get_full_name(),
            'email': obj.student.user.email,
            'phone': obj.student.user.phone_number,
            'course': obj.student.course_name,
            'academic_year': obj.student.academic_year,
            'institute': obj.student.institute.name,
            'department': obj.student.department.name,
            'family_income': obj.student.family_income,
            'category': obj.student.category
        }


class StudentDocumentSerializer(serializers.ModelSerializer):
    """Enhanced serializer for student documents with verification details"""
    
    verification = serializers.SerializerMethodField()
    file_size_mb = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    verifier_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    
    class Meta:
        model = StudentDocument
        fields = '__all__'
        read_only_fields = (
            'student', 'file_size', 'file_format', 'is_verified',
            'verified_by', 'verification_date', 'uploaded_at', 'updated_at'
        )
    
    def get_verification(self, obj):
        """Get verification details"""
        if hasattr(obj, 'verification') and obj.verification.exists():
            verification = obj.verification.first()
            return {
                'status': verification.verification_status,
                'comments': verification.comments,
                'verified_by': verification.verified_by.get_full_name(),
                'verification_date': verification.verification_date
            }
        return None


class StudentSerializer(serializers.ModelSerializer):
    """Comprehensive student serializer with all related information"""
    
    user_details = serializers.SerializerMethodField()
    institute_details = serializers.SerializerMethodField()
    department_details = serializers.SerializerMethodField()
    current_semester = serializers.ReadOnlyField()
    verification_status = serializers.SerializerMethodField()
    document_completion_percentage = serializers.SerializerMethodField()
    application_statistics = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = '__all__'
        read_only_fields = (
            'user', 'student_id', 'created_at', 'updated_at',
            'is_verified', 'verification_date', 'verified_by'
        )
    
    def get_user_details(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'email': obj.user.email,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'full_name': obj.user.get_full_name(),
            'phone_number': obj.user.phone_number,
            'last_login': obj.user.last_login,
            'date_joined': obj.user.date_joined,
            'is_active': obj.user.is_active
        }
    
    def get_institute_details(self, obj):
        return {
            'id': obj.institute.id,
            'name': obj.institute.name,
            'code': obj.institute.code,
            'city': obj.institute.city,
            'state': obj.institute.state,
            'institute_type': obj.institute.institute_type
        }
    
    def get_department_details(self, obj):
        return {
            'id': obj.department.id,
            'name': obj.department.name,
            'code': obj.department.code
        }
    
    def get_verification_status(self, obj):
        return {
            'is_verified': obj.is_verified,
            'verification_date': obj.verification_date,
            'verified_by': obj.verified_by.get_full_name() if obj.verified_by else None
        }
    
    def get_document_completion_percentage(self, obj):
        """Calculate document completion percentage"""
        total_docs = obj.documents.count()
        verified_docs = obj.documents.filter(is_verified=True).count()
        return (verified_docs / total_docs * 100) if total_docs > 0 else 0
    
    def get_application_statistics(self, obj):
        """Get application statistics"""
        applications = obj.scholarship_applications.all()
        return {
            'total': applications.count(),
            'draft': applications.filter(status='draft').count(),
            'submitted': applications.filter(status='submitted').count(),
            'under_review': applications.filter(status='under_review').count(),
            'approved': applications.filter(status='approved').count(),
            'rejected': applications.filter(status='rejected').count()
        }


class AcademicRecordSerializer(serializers.ModelSerializer):
    """Serializer for academic records"""
    
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    grade_display = serializers.CharField(source='get_grade_display', read_only=True)
    
    class Meta:
        model = AcademicRecord
        fields = '__all__'
        read_only_fields = ('student', 'created_at', 'updated_at')
    
    def validate_gpa(self, value):
        """Validate GPA is in valid range"""
        if value < 0 or value > 10:
            raise serializers.ValidationError("GPA must be between 0 and 10")
        return value
    
    def validate_attendance_percentage(self, value):
        """Validate attendance percentage"""
        if value and (value < 0 or value > 100):
            raise serializers.ValidationError("Attendance must be between 0 and 100")
        return value
    
    def validate(self, attrs):
        """Additional validation"""
        # Ensure academic year and semester combination is valid
        academic_year = attrs.get('academic_year')
        semester = attrs.get('semester')
        
        if academic_year and semester:
            year_num = int(academic_year.replace('st', '').replace('nd', '').replace('rd', '').replace('th', ''))
            if semester > year_num * 2:
                raise serializers.ValidationError(
                    f"Semester {semester} is not valid for {academic_year} year"
                )
        
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    def validate_old_password(self, value):
        """Validate old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value
    
    def validate(self, attrs):
        """Validate new passwords match"""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def save(self):
        """Change password"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
