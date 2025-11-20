from rest_framework import serializers
from django.contrib.auth import get_user_model  # authenticate
from django.contrib.auth.password_validation import validate_password
from .models import (
    PatientProfile, StudentProfile, SupervisorProfile,
    UniversityAdminProfile, TechSupportProfile
)

User = get_user_model()

"""
# Authentication Serializers (disabled temporarily)
class LoginSerializer(serializers.Serializer):
    \"\"\"Serializer to handle user login via email and password.\"\"\"

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError(
                {\"detail\": \"البريد الإلكتروني وكلمة المرور مطلوبان.\"}
            )

        user = authenticate(request=self.context.get('request'), email=email, password=password)

        if user is None:
            raise serializers.ValidationError({\"detail\": \"بيانات الدخول غير صحيحة.\"})

        if not user.is_active:
            raise serializers.ValidationError({\"detail\": \"الحساب غير مفعل. برجاء التواصل مع الدعم.\"})

        attrs['user'] = user
        return attrs

class LogoutSerializer(serializers.Serializer):
    \"\"\"Serializer to handle logout by blacklisting refresh token.\"\"\"

    refresh = serializers.CharField()

    def validate(self, attrs):
        refresh_token = attrs.get('refresh')

        if not refresh_token:
            raise serializers.ValidationError({\"detail\": \"Token غير موجود.\"})

        attrs['refresh_token'] = refresh_token
        return attrs
"""

# Create Serializers
class PatientCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a patient."""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm', 
            'first_name', 'last_name'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords don't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        # Create user
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(password)
        user.role = 'patient'
        user.save()
        
        # Create profile
        PatientProfile.objects.create(user=user)
        return user

class StudentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a student."""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    university_id = serializers.UUIDField(required=False, allow_null=True)
    student_id = serializers.CharField(required=False, allow_blank=True)
    year_of_study = serializers.IntegerField(required=False, allow_null=True)
    specialization = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm', 
            'first_name', 'last_name', 'university_id', 'student_id', 
            'year_of_study', 'specialization'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords don't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        # Extract profile data
        profile_data = {
            'university_id': validated_data.pop('university_id', None),
            'student_id': validated_data.pop('student_id', None),
            'year_of_study': validated_data.pop('year_of_study', None),
            'specialization': validated_data.pop('specialization', None)
        }
        
        # Remove None values
        profile_data = {k: v for k, v in profile_data.items() if v is not None}
        
        # Create user
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(password)
        user.role = 'student'
        user.save()
        
        # Create profile
        StudentProfile.objects.create(user=user, **profile_data)
        return user

class SupervisorCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a supervisor."""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    university_id = serializers.UUIDField(required=False, allow_null=True)
    department = serializers.CharField(required=False, allow_blank=True)
    position = serializers.CharField(required=False, allow_blank=True)
    license_number = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'university_id', 'department',
            'position', 'license_number', 'phone_number', 'address',
            'date_of_birth', 'gender'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords don't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        # Extract profile data
        profile_data = {
            'university_id': validated_data.pop('university_id', None),
            'department': validated_data.pop('department', None),
            'position': validated_data.pop('position', None),
            'license_number': validated_data.pop('license_number', None),
            'phone_number': validated_data.pop('phone_number', None),
            'address': validated_data.pop('address', None),
            'date_of_birth': validated_data.pop('date_of_birth', None),
            'gender': validated_data.pop('gender', None),
        }
        
        # Remove None values
        profile_data = {k: v for k, v in profile_data.items() if v is not None}
        
        # Create user
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(password)
        user.role = 'supervisor'
        user.save()
        
        # Create profile
        SupervisorProfile.objects.create(user=user, **profile_data)
        return user


class UniversityAdminCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a university admin."""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    university_id = serializers.UUIDField(required=False, allow_null=True)
    department = serializers.CharField(required=False, allow_blank=True)
    position = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm', 
            'first_name', 'last_name', 'university_id', 'department', 'position',
            
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords don't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        # Extract profile data
        profile_data = {
            'university_id': validated_data.pop('university_id', None),
            'department': validated_data.pop('department', None),
            'position': validated_data.pop('position', None)
        }
        
        # Remove None values
        profile_data = {k: v for k, v in profile_data.items() if v is not None}
        
        # Create user
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(password)
        user.role = 'university_admin'
        user.save()
        
        # Create profile
        UniversityAdminProfile.objects.create(user=user, **profile_data)
        return user

class TechSupportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a tech support."""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    department = serializers.CharField(required=False, allow_blank=True)
    position = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm', 
            'first_name', 'last_name', 'department', 'position'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords don't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        # Extract profile data
        profile_data = {
            'department': validated_data.pop('department', None),
            'position': validated_data.pop('position', None)
        }
        
        # Remove None values
        profile_data = {k: v for k, v in profile_data.items() if v is not None}
        
        # Create user
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(password)
        user.role = 'tech_support'
        user.save()
        
        # Create profile
        TechSupportProfile.objects.create(user=user, **profile_data)
        return user

# List Serializers
class PatientListSerializer(serializers.ModelSerializer):
    """Serializer for patient list data."""
    user_id = serializers.UUIDField(source='user.id')
    username = serializers.CharField(source='user.username')
    email = serializers.CharField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    
    class Meta:
        model = PatientProfile
        fields = [
            'user_id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'address', 'date_of_birth', 'gender'
        ]

class StudentListSerializer(serializers.ModelSerializer):
    """Serializer for student list data."""
    user_id = serializers.UUIDField(source='user.id')
    username = serializers.CharField(source='user.username')
    email = serializers.CharField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    university_name = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentProfile
        fields = [
            'user_id', 'username', 'email', 'first_name', 'last_name',
            'university_name', 'student_id', 'year_of_study', 'specialization'
        ]
    
    def get_university_name(self, obj):
        return obj.university.name if obj.university else None

class SupervisorListSerializer(serializers.ModelSerializer):
    """Serializer for supervisor list data."""
    user_id = serializers.UUIDField(source='user.id')
    username = serializers.CharField(source='user.username')
    email = serializers.CharField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    university_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SupervisorProfile
        fields = [
            'user_id', 'username', 'email', 'first_name', 'last_name',
            'university_name', 'department', 'position', 'license_number'
        ]
    
    def get_university_name(self, obj):
        return obj.university.name if obj.university else None

class UniversityAdminListSerializer(serializers.ModelSerializer):
    """Serializer for university admin list data."""
    user_id = serializers.UUIDField(source='user.id')
    username = serializers.CharField(source='user.username')
    email = serializers.CharField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    university_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UniversityAdminProfile
        fields = [
            'user_id', 'username', 'email', 'first_name', 'last_name',
            'university_name', 'department', 'position'
        ]
    
    def get_university_name(self, obj):
        return obj.university.name if obj.university else None

class TechSupportListSerializer(serializers.ModelSerializer):
    """Serializer for tech support list data."""
    user_id = serializers.UUIDField(source='user.id')
    username = serializers.CharField(source='user.username')
    email = serializers.CharField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    
    class Meta:
        model = TechSupportProfile
        fields = [
            'user_id', 'username', 'email', 'first_name', 'last_name',
            'department', 'position'
        ]

# Detail Serializers - مع التعديلات المطلوبة
class PatientDetailSerializer(serializers.ModelSerializer):
    """Serializer for patient detail data."""
    user_id = serializers.UUIDField(source='user.id')
    username = serializers.CharField(source='user.username')
    email = serializers.CharField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    role = serializers.CharField(source='user.role')
    is_active = serializers.BooleanField(source='user.is_active')
    date_joined = serializers.DateTimeField(source='user.date_joined')
    last_login = serializers.DateTimeField(source='user.last_login')
    
    class Meta:
        model = PatientProfile
        fields = '__all__'
        read_only_fields = ['user_id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined', 'last_login']

class StudentDetailSerializer(serializers.ModelSerializer):
    """Serializer for student detail data."""
    user_id = serializers.UUIDField(source='user.id')
    username = serializers.CharField(source='user.username')
    email = serializers.CharField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    role = serializers.CharField(source='user.role')
    is_active = serializers.BooleanField(source='user.is_active')
    date_joined = serializers.DateTimeField(source='user.date_joined')
    last_login = serializers.DateTimeField(source='user.last_login')
    university_name = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentProfile
        fields = '__all__'
        read_only_fields = ['user_id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined', 'last_login']
    
    def get_university_name(self, obj):
        return obj.university.name if obj.university else None

class SupervisorDetailSerializer(serializers.ModelSerializer):
    """Serializer for supervisor detail data."""
    user_id = serializers.UUIDField(source='user.id')
    username = serializers.CharField(source='user.username')
    email = serializers.CharField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    role = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(source='user.is_active')
    date_joined = serializers.DateTimeField(source='user.date_joined')
    last_login = serializers.DateTimeField(source='user.last_login')
    university_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SupervisorProfile
        fields = '__all__'
        read_only_fields = ['user_id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined', 'last_login']
    
    def get_university_name(self, obj):
        return obj.university.name if obj.university else None

class UniversityAdminDetailSerializer(serializers.ModelSerializer):
    """Serializer for university admin detail data."""
    user_id = serializers.UUIDField(source='user.id')
    username = serializers.CharField(source='user.username')
    email = serializers.CharField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    role = serializers.CharField(source='user.role')
    is_active = serializers.BooleanField(source='user.is_active')
    date_joined = serializers.DateTimeField(source='user.date_joined')
    last_login = serializers.DateTimeField(source='user.last_login')
    university_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UniversityAdminProfile
        fields = '__all__'
        read_only_fields = ['user_id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined', 'last_login']
    
    def get_university_name(self, obj):
        return obj.university.name if obj.university else None

class TechSupportDetailSerializer(serializers.ModelSerializer):
    """Serializer for tech support detail data."""
    user_id = serializers.UUIDField(source='user.id')
    username = serializers.CharField(source='user.username')
    email = serializers.CharField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    role = serializers.CharField(source='user.role')
    is_active = serializers.BooleanField(source='user.is_active')
    date_joined = serializers.DateTimeField(source='user.date_joined')
    last_login = serializers.DateTimeField(source='user.last_login')
    
    class Meta:
        model = TechSupportProfile
        fields = '__all__'
        read_only_fields = ['user_id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined', 'last_login']

# Update Serializers
class PatientUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a patient profile."""
    
    class Meta:
        model = PatientProfile
        fields = [
            'phone_number', 'address', 'date_of_birth', 'gender', 'profile_picture',
            'medical_history', 'allergies', 'medications',
            'emergency_contact_name', 'emergency_contact_phone'
        ]

class StudentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a student profile."""
    
    class Meta:
        model = StudentProfile
        fields = [
            'phone_number', 'address', 'date_of_birth', 'gender', 'profile_picture',
            'university', 'student_id', 'year_of_study', 'specialization'
        ]

class SupervisorUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a supervisor profile."""
    
    class Meta:
        model = SupervisorProfile
        fields = [
            'phone_number', 'address', 'date_of_birth', 'gender', 'profile_picture',
            'university', 'department', 'position', 'license_number'
        ]

class UniversityAdminUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a university admin profile."""
    
    class Meta:
        model = UniversityAdminProfile
        fields = [
            'phone_number', 'address', 'date_of_birth', 'gender', 'profile_picture',
            'university', 'department', 'position'
        ]

class TechSupportUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a tech support profile."""
    
    class Meta:
        model = TechSupportProfile
        fields = [
            'phone_number', 'address', 'date_of_birth', 'gender', 'profile_picture',
            'department', 'position'
        ]

# User Serializer for general use
class UserSerializer(serializers.ModelSerializer):
    """Serializer for general user data."""
    profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'is_active', 'date_joined', 'last_login', 'profile'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
    
    def get_profile(self, obj):
        """Get profile data based on user role."""
        profile_models = {
            'patient': PatientProfile,
            'student': StudentProfile,
            'supervisor': SupervisorProfile,
            'university_admin': UniversityAdminProfile,
            'tech_support': TechSupportProfile,
        }
        
        profile_model = profile_models.get(obj.role)
        if profile_model:
            try:
                profile = profile_model.objects.get(user=obj)
                profile_serializers = {
                    'patient': PatientDetailSerializer,
                    'student': StudentDetailSerializer,
                    'supervisor': SupervisorDetailSerializer,
                    'university_admin': UniversityAdminDetailSerializer,
                    'tech_support': TechSupportDetailSerializer,
                }
                
                serializer_class = profile_serializers.get(obj.role)
                if serializer_class:
                    return serializer_class(profile).data
            except profile_model.DoesNotExist:
                pass
        return None