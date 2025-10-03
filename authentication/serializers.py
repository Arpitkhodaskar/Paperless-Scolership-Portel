from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from .models import CustomUser, UserProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Enhanced serializer for user registration with validation"""
    
    password = serializers.CharField(
        write_only=True, 
        min_length=8,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    phone_number = serializers.CharField(
        required=False,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be valid format"
        )]
    )
    
    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'first_name', 'last_name', 
            'password', 'password_confirm', 'user_type', 'phone_number'
        )
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
        
    def validate_email(self, value):
        """Validate email uniqueness"""
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value
    
    def validate_username(self, value):
        """Validate username format"""
        if not value.replace('_', '').replace('.', '').isalnum():
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, underscores and dots"
            )
        return value
        
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """Enhanced serializer for user login with detailed validation"""
    
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(
        max_length=128,
        write_only=True,
        style={'input_type': 'password'}
    )
    remember_me = serializers.BooleanField(default=False, required=False)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # Allow login with email or username
            user = None
            if '@' in username:
                try:
                    user_obj = CustomUser.objects.get(email=username)
                    user = authenticate(username=user_obj.username, password=password)
                except CustomUser.DoesNotExist:
                    pass
            else:
                user = authenticate(username=username, password=password)
                
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
                
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password')


class UserProfileSerializer(serializers.ModelSerializer):
    """Enhanced serializer for user profile with nested data"""
    
    full_name = serializers.SerializerMethodField()
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ('user',)
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()


class UserSerializer(serializers.ModelSerializer):
    """Enhanced serializer for user information with profile data"""
    
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    
    class Meta:
        model = CustomUser
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'user_type_display', 'phone_number', 'profile_picture', 
            'is_verified', 'created_at', 'profile'
        )
        read_only_fields = ('id', 'created_at', 'is_verified', 'user_type')
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class ChangePasswordSerializer(serializers.Serializer):
    """Enhanced serializer for changing password with validation"""
    
    old_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True, 
        min_length=8,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user information"""
    
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = CustomUser
        fields = (
            'first_name', 'last_name', 'phone_number', 
            'profile_picture', 'profile'
        )
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update profile fields
        if profile_data and hasattr(instance, 'profile'):
            profile_serializer = UserProfileSerializer(
                instance.profile, 
                data=profile_data, 
                partial=True
            )
            if profile_serializer.is_valid():
                profile_serializer.save()
        
        return instance


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        try:
            CustomUser.objects.get(email=value)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("No user found with this email address")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        min_length=8,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
