from rest_framework import serializers
from django.core.validators import FileExtensionValidator
from django.core.files.uploadedfile import UploadedFile
from .models import Student, StudentDocument, AcademicRecord, ScholarshipApplication, DocumentVerification
from institutes.models import Institute
from departments.models import Department


class InstituteBasicSerializer(serializers.ModelSerializer):
    """Basic institute information for nested serialization"""
    class Meta:
        model = Institute
        fields = ('id', 'name', 'code', 'city', 'state')


class DepartmentBasicSerializer(serializers.ModelSerializer):
    """Basic department information for nested serialization"""
    class Meta:
        model = Department
        fields = ('id', 'name', 'code')


class StudentRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for student registration/creation"""
    
    class Meta:
        model = Student
        fields = (
            'institute', 'department', 'course_level', 'course_name',
            'academic_year', 'enrollment_date', 'roll_number',
            'admission_type', 'category', 'father_name', 'mother_name',
            'guardian_name', 'family_income', 'permanent_address',
            'current_address', 'emergency_contact'
        )
    
    def validate_family_income(self, value):
        """Validate family income is reasonable"""
        if value and value < 0:
            raise serializers.ValidationError("Family income cannot be negative")
        if value and value > 10000000:  # 1 crore
            raise serializers.ValidationError("Family income seems unreasonably high")
        return value
    
    def create(self, validated_data):
        """Create student profile for authenticated user"""
        user = self.context['request'].user
        if hasattr(user, 'student_profile'):
            raise serializers.ValidationError("Student profile already exists")
        
        validated_data['user'] = user
        return super().create(validated_data)


class StudentSerializer(serializers.ModelSerializer):
    """Comprehensive student serializer with nested data"""
    
    user_details = serializers.SerializerMethodField()
    institute_details = InstituteBasicSerializer(source='institute', read_only=True)
    department_details = DepartmentBasicSerializer(source='department', read_only=True)
    current_semester = serializers.ReadOnlyField()
    verification_status = serializers.SerializerMethodField()
    document_completion_percentage = serializers.SerializerMethodField()
    
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


class DocumentVerificationSerializer(serializers.ModelSerializer):
    """Serializer for document verification process"""
    
    verifier_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    
    class Meta:
        model = DocumentVerification
        fields = '__all__'
        read_only_fields = ('document', 'verified_by', 'verification_date', 'created_at', 'updated_at')


class StudentDocumentSerializer(serializers.ModelSerializer):
    """Enhanced serializer for student documents with validation"""
    
    verification = DocumentVerificationSerializer(read_only=True)
    file_size_mb = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    verifier_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    
    class Meta:
        model = StudentDocument
        fields = '__all__'
        read_only_fields = (
            'student', 'file_size', 'file_format', 'is_verified',
            'verified_by', 'verification_date', 'uploaded_at', 'updated_at'
        )
        
    def validate_document_file(self, value):
        """Validate uploaded file"""
        if not isinstance(value, UploadedFile):
            return value
            
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size must be less than {max_size // (1024*1024)}MB"
            )
        
        # Check file extension
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']
        file_extension = value.name.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        return value
    
    def create(self, validated_data):
        """Create document for current student"""
        student = self.context['request'].user.student_profile
        validated_data['student'] = student
        return super().create(validated_data)


class StudentDocumentUploadSerializer(serializers.ModelSerializer):
    """Simplified serializer for document upload"""
    
    class Meta:
        model = StudentDocument
        fields = ('document_type', 'document_name', 'document_file', 'description', 'document_number', 'issue_date', 'expiry_date', 'issuing_authority')
    
    def validate_document_file(self, value):
        """Validate uploaded file"""
        return StudentDocumentSerializer().validate_document_file(value)


class AcademicRecordSerializer(serializers.ModelSerializer):
    """Serializer for academic records"""
    
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    
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


class ScholarshipApplicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating scholarship applications"""
    
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
            raise serializers.ValidationError("Amount seems unreasonably high")
        return value
    
    def create(self, validated_data):
        """Create application for current student"""
        student = self.context['request'].user.student_profile
        validated_data['student'] = student
        return super().create(validated_data)


class ScholarshipApplicationSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for scholarship applications"""
    
    student_details = serializers.SerializerMethodField()
    processing_time = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_scholarship_type_display', read_only=True)
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
            'course': obj.student.course_name,
            'academic_year': obj.student.academic_year,
            'institute': obj.student.institute.name,
            'department': obj.student.department.name,
        }


class ScholarshipApplicationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating applications (draft only)"""
    
    class Meta:
        model = ScholarshipApplication
        fields = (
            'scholarship_type', 'scholarship_name', 'amount_requested',
            'reason', 'additional_information', 'family_details',
            'academic_details'
        )
    
    def validate(self, attrs):
        """Only allow updates for draft applications"""
        if self.instance and self.instance.status != 'draft':
            raise serializers.ValidationError("Cannot edit submitted application")
        return attrs


class ScholarshipApplicationSubmitSerializer(serializers.Serializer):
    """Serializer for application submission"""
    
    confirm_submission = serializers.BooleanField(required=True)
    declaration = serializers.BooleanField(required=True)
    
    def validate_confirm_submission(self, value):
        if not value:
            raise serializers.ValidationError("Submission confirmation is required")
        return value
    
    def validate_declaration(self, value):
        if not value:
            raise serializers.ValidationError("Declaration acceptance is required")
        return value


class ScholarshipApplicationReviewSerializer(serializers.ModelSerializer):
    """Serializer for application review by admins"""
    
    class Meta:
        model = ScholarshipApplication
        fields = (
            'status', 'review_comments', 'internal_notes',
            'rejection_reason', 'amount_approved', 'priority'
        )
    
    def validate_status(self, value):
        """Validate status transitions"""
        valid_transitions = {
            'submitted': ['under_review', 'rejected'],
            'under_review': ['document_verification', 'eligibility_check', 'approved', 'rejected', 'on_hold'],
            'document_verification': ['eligibility_check', 'under_review', 'rejected'],
            'eligibility_check': ['approved', 'partially_approved', 'rejected', 'under_review'],
            'on_hold': ['under_review', 'rejected'],
        }
        
        if self.instance:
            current_status = self.instance.status
            if current_status in valid_transitions:
                if value not in valid_transitions[current_status]:
                    raise serializers.ValidationError(
                        f"Cannot change status from {current_status} to {value}"
                    )
        
        return value
