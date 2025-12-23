# apps/accounts/serializers.py
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from rest_framework import serializers

from .models import (
    Role,
    PatientProfile,
    StudentProfile,
    SupervisorProfile,
    UniversityAdminProfile,
    TechSupportProfile,
)

User = get_user_model()

# ============================================================
# AUTH SERIALIZERS
# ============================================================
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password,
        )

        if not user:
            raise serializers.ValidationError({"detail": "بيانات الدخول غير صحيحة."})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "الحساب غير مفعل."})

        attrs["user"] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


# ============================================================
# BASE USER CREATE SERIALIZER
# ============================================================
class BaseUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    role_name: str = None  # must be defined in child

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password", "password_confirm")

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        role = Role.objects.get(name=self.role_name)

        user = User(**validated_data)
        user.role = role
        user.set_password(password)
        user.save()

        return user


# ============================================================
# CREATE SERIALIZERS
# ============================================================
class PatientCreateSerializer(BaseUserCreateSerializer):
    role_name = Role.PATIENT


class StudentCreateSerializer(BaseUserCreateSerializer):
    role_name = Role.STUDENT


class SupervisorCreateSerializer(BaseUserCreateSerializer):
    role_name = Role.SUPERVISOR


class UniversityAdminCreateSerializer(BaseUserCreateSerializer):
    role_name = Role.UNIVERSITY_ADMIN


class TechSupportCreateSerializer(BaseUserCreateSerializer):
    """
    🔐 Internal API – Only System Admin can use this
    """
    role_name = Role.TECH_SUPPORT


# ============================================================
# LIST SERIALIZERS
# ============================================================
class BaseProfileListSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    role = serializers.CharField(source="user.role.name", read_only=True)


class PatientListSerializer(BaseProfileListSerializer):
    class Meta:
        model = PatientProfile
        fields = "__all__"


class StudentListSerializer(BaseProfileListSerializer):
    university_name = serializers.CharField(source="university.name", read_only=True)

    class Meta:
        model = StudentProfile
        fields = "__all__"


class SupervisorListSerializer(BaseProfileListSerializer):
    university_name = serializers.CharField(source="university.name", read_only=True)

    class Meta:
        model = SupervisorProfile
        fields = "__all__"


class UniversityAdminListSerializer(BaseProfileListSerializer):
    university_name = serializers.CharField(source="university.name", read_only=True)

    class Meta:
        model = UniversityAdminProfile
        fields = "__all__"


class TechSupportListSerializer(BaseProfileListSerializer):
    class Meta:
        model = TechSupportProfile
        fields = "__all__"


# ============================================================
# DETAIL SERIALIZERS
# ============================================================
class BaseProfileDetailSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    role = serializers.CharField(source="user.role.name", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    date_joined = serializers.DateTimeField(source="user.date_joined", read_only=True)
    last_login = serializers.DateTimeField(source="user.last_login", read_only=True)


class PatientDetailSerializer(BaseProfileDetailSerializer):
    class Meta:
        model = PatientProfile
        fields = "__all__"


class StudentDetailSerializer(BaseProfileDetailSerializer):
    university_name = serializers.CharField(source="university.name", read_only=True)

    class Meta:
        model = StudentProfile
        fields = "__all__"


class SupervisorDetailSerializer(BaseProfileDetailSerializer):
    university_name = serializers.CharField(source="university.name", read_only=True)

    class Meta:
        model = SupervisorProfile
        fields = "__all__"


class UniversityAdminDetailSerializer(BaseProfileDetailSerializer):
    university_name = serializers.CharField(source="university.name", read_only=True)

    class Meta:
        model = UniversityAdminProfile
        fields = "__all__"


class TechSupportDetailSerializer(BaseProfileDetailSerializer):
    class Meta:
        model = TechSupportProfile
        fields = "__all__"


# ============================================================
# UPDATE SERIALIZERS
# ============================================================
class PatientUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        exclude = ("user",)


class StudentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        exclude = ("user",)


class SupervisorUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupervisorProfile
        exclude = ("user",)


class UniversityAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UniversityAdminProfile
        exclude = ("user",)


class TechSupportUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechSupportProfile
        exclude = ("user",)


# ============================================================
# USER SERIALIZER (GENERIC)
# ============================================================
class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "date_joined",
            "last_login",
        )
