from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Institute, InstituteAdmin, Course, CourseSpecialization
from students.models import Student


User = get_user_model()


class CourseSpecializationSerializer(serializers.ModelSerializer):
    """Serializer for course specializations"""
    
    class Meta:
        model = CourseSpecialization
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class CourseSerializer(serializers.ModelSerializer):
    """Serializer for courses with specializations"""
    
    specializations = CourseSpecializationSerializer(many=True, read_only=True)
    institute_name = serializers.CharField(source='institute.name', read_only=True)
    student_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_student_count(self, obj):
        """Get number of students enrolled in this course"""
        return Student.objects.filter(course_name=obj.name, institute=obj.institute).count()


class CourseCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating courses"""
    
    class Meta:
        model = Course
        fields = (
            'name', 'code', 'description', 'level', 'duration_years',
            'duration_semesters', 'department', 'fees_per_semester',
            'total_seats', 'eligibility_criteria', 'is_active'
        )
    
    def validate_duration_years(self, value):
        """Validate course duration"""
        if value <= 0 or value > 10:
            raise serializers.ValidationError("Duration must be between 1 and 10 years")
        return value
    
    def validate_duration_semesters(self, value):
        """Validate semester count"""
        if value <= 0 or value > 20:
            raise serializers.ValidationError("Semesters must be between 1 and 20")
        return value


class InstituteAdminBasicSerializer(serializers.ModelSerializer):
    """Basic serializer for institute admin info"""
    
    user_details = serializers.SerializerMethodField()
    
    class Meta:
        model = InstituteAdmin
        fields = ('id', 'user_details', 'position', 'is_active')
    
    def get_user_details(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'email': obj.user.email,
            'full_name': obj.user.get_full_name(),
            'phone_number': obj.user.phone_number,
        }


class InstituteSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for institutes"""
    
    admins = InstituteAdminBasicSerializer(source='admins', many=True, read_only=True)
    courses = CourseSerializer(many=True, read_only=True)
    statistics = serializers.SerializerMethodField()
    contact_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Institute
        fields = '__all__'
        read_only_fields = ('code', 'created_at', 'updated_at', 'is_verified', 'verification_date')
    
    def get_statistics(self, obj):
        """Get institute statistics"""
        students_count = Student.objects.filter(institute=obj).count()
        courses_count = obj.courses.count()
        active_courses = obj.courses.filter(is_active=True).count()
        verified_students = Student.objects.filter(institute=obj, is_verified=True).count()
        
        return {
            'total_students': students_count,
            'verified_students': verified_students,
            'total_courses': courses_count,
            'active_courses': active_courses,
            'verification_rate': (verified_students / students_count * 100) if students_count > 0 else 0
        }
    
    def get_contact_info(self, obj):
        """Get formatted contact information"""
        return {
            'address': {
                'street': obj.address,
                'city': obj.city,
                'state': obj.state,
                'postal_code': obj.postal_code,
                'country': obj.country,
                'full_address': f"{obj.address}, {obj.city}, {obj.state} {obj.postal_code}, {obj.country}"
            },
            'contact': {
                'phone': obj.phone_number,
                'email': obj.email,
                'website': obj.website,
                'fax': obj.fax_number
            }
        }


class InstituteRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for institute registration"""
    
    admin_user_data = serializers.DictField(write_only=True, required=True)
    
    class Meta:
        model = Institute
        fields = (
            'name', 'address', 'city', 'state', 'postal_code', 'country',
            'phone_number', 'email', 'website', 'fax_number', 'established_year',
            'institute_type', 'affiliation', 'university_name', 'approval_body',
            'recognition_status', 'admin_user_data'
        )
    
    def validate_admin_user_data(self, value):
        """Validate admin user data"""
        required_fields = ['username', 'email', 'first_name', 'last_name', 'password', 'phone_number']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"{field} is required for admin user")
        
        # Check if username/email already exists
        if User.objects.filter(username=value['username']).exists():
            raise serializers.ValidationError("Username already exists")
        if User.objects.filter(email=value['email']).exists():
            raise serializers.ValidationError("Email already exists")
        
        return value
    
    def validate_established_year(self, value):
        """Validate establishment year"""
        from datetime import datetime
        current_year = datetime.now().year
        if value < 1800 or value > current_year:
            raise serializers.ValidationError(f"Established year must be between 1800 and {current_year}")
        return value
    
    def create(self, validated_data):
        """Create institute with admin user"""
        admin_data = validated_data.pop('admin_user_data')
        
        with transaction.atomic():
            # Create institute
            institute = super().create(validated_data)
            
            # Create admin user
            admin_user = User.objects.create_user(
                username=admin_data['username'],
                email=admin_data['email'],
                first_name=admin_data['first_name'],
                last_name=admin_data['last_name'],
                password=admin_data['password'],
                phone_number=admin_data['phone_number'],
                user_type='institute_admin',
                is_active=False  # Needs approval
            )
            
            # Create institute admin
            InstituteAdmin.objects.create(
                user=admin_user,
                institute=institute,
                position=admin_data.get('position', 'Administrator'),
                is_active=False  # Needs approval
            )
        
        return institute


class InstituteUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating institute information"""
    
    class Meta:
        model = Institute
        fields = (
            'name', 'address', 'city', 'state', 'postal_code', 'country',
            'phone_number', 'email', 'website', 'fax_number', 'established_year',
            'institute_type', 'affiliation', 'university_name', 'approval_body',
            'recognition_status'
        )


class InstituteAdminSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for institute admins"""
    
    user_details = serializers.SerializerMethodField()
    institute_details = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = InstituteAdmin
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_user_details(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'email': obj.user.email,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'full_name': obj.user.get_full_name(),
            'phone_number': obj.user.phone_number,
            'is_active': obj.user.is_active,
            'date_joined': obj.user.date_joined,
            'last_login': obj.user.last_login,
        }
    
    def get_institute_details(self, obj):
        return {
            'id': obj.institute.id,
            'name': obj.institute.name,
            'code': obj.institute.code,
            'city': obj.institute.city,
            'state': obj.institute.state,
            'institute_type': obj.institute.institute_type,
        }
    
    def get_permissions(self, obj):
        """Get admin permissions based on their role"""
        return {
            'can_verify_students': obj.is_active,
            'can_manage_courses': obj.is_active,
            'can_approve_applications': obj.is_active,
            'can_view_all_students': obj.is_active,
            'can_manage_departments': obj.is_active,
        }


class InstituteAdminCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating institute admins"""
    
    user_data = serializers.DictField(write_only=True, required=True)
    
    class Meta:
        model = InstituteAdmin
        fields = ('institute', 'position', 'is_active', 'user_data')
    
    def validate_user_data(self, value):
        """Validate user data for new admin"""
        required_fields = ['username', 'email', 'first_name', 'last_name', 'password', 'phone_number']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"{field} is required")
        
        # Check if username/email already exists
        if User.objects.filter(username=value['username']).exists():
            raise serializers.ValidationError("Username already exists")
        if User.objects.filter(email=value['email']).exists():
            raise serializers.ValidationError("Email already exists")
        
        return value
    
    def create(self, validated_data):
        """Create institute admin with user"""
        user_data = validated_data.pop('user_data')
        
        with transaction.atomic():
            # Create user
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                password=user_data['password'],
                phone_number=user_data['phone_number'],
                user_type='institute_admin'
            )
            
            # Create institute admin
            validated_data['user'] = user
            return super().create(validated_data)


class InstituteVerificationSerializer(serializers.Serializer):
    """Serializer for institute verification"""
    
    verification_status = serializers.BooleanField(required=True)
    verification_comments = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def validate_verification_status(self, value):
        """Ensure verification status is provided"""
        if value is None:
            raise serializers.ValidationError("Verification status must be specified")
        return value
