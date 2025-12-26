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
# LOGIN SERIALIZERS
# ============================================================

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password,
        )

        if not user:
            raise serializers.ValidationError(
                {"detail": "بيانات الدخول غير صحيحة."}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "الحساب غير مفعل."}
            )

        attrs["user"] = user
        return attrs


class RoleBasedLoginSerializer(LoginSerializer):
    """
    Login serializer enforcing role-based access.
    """
    allowed_role: str | None = None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        user = attrs["user"]

        if not self.allowed_role:
            raise serializers.ValidationError(
                "Internal role configuration error."
            )

        if user.role.name != self.allowed_role:
            raise serializers.ValidationError(
                {"detail": "لا يمكنك تسجيل الدخول من هذه البوابة."}
            )

        return attrs


# ============================================================
# BASE USER CREATION
# ============================================================

class BaseUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )
    password_confirm = serializers.CharField(write_only=True)

    role_name: str | None = None  # MUST be defined in subclass

    class Meta:
        model = User
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password": "كلمتا المرور غير متطابقتين."}
            )

        attrs["email"] = attrs["email"].strip().lower()
        return attrs

    def _get_role(self) -> Role:
        try:
            return Role.objects.get(name=self.role_name)
        except Role.DoesNotExist:
            raise serializers.ValidationError(
                {"role": "الدور غير موجود في النظام."}
            )

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.role = self._get_role()
        user.set_password(password)

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            user.created_by = request.user

        user.full_clean()
        user.save()
        return user


# ============================================================
# CREATE SERIALIZERS (BY ROLE)
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
    role_name = Role.TECH_SUPPORT


# ============================================================
# PROFILE SERIALIZERS
# ============================================================

class BaseProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(source="user.role.name", read_only=True)

    class Meta:
        abstract = True


class PatientProfileSerializer(BaseProfileSerializer):
    class Meta:
        model = PatientProfile
        exclude = ("user",)


class StudentProfileSerializer(BaseProfileSerializer):
    university_name = serializers.CharField(
        source="university.name",
        read_only=True,
    )

    class Meta:
        model = StudentProfile
        exclude = ("user",)


class SupervisorProfileSerializer(BaseProfileSerializer):
    university_name = serializers.CharField(
        source="university.name",
        read_only=True,
    )

    class Meta:
        model = SupervisorProfile
        exclude = ("user",)


class UniversityAdminProfileSerializer(BaseProfileSerializer):
    university_name = serializers.CharField(
        source="university.name",
        read_only=True,
    )

    class Meta:
        model = UniversityAdminProfile
        exclude = ("user",)


class TechSupportProfileSerializer(BaseProfileSerializer):
    class Meta:
        model = TechSupportProfile
        exclude = ("user",)
