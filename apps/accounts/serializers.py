from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db import IntegrityError

from rest_framework import serializers

from apps.universities.models import University
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

        try:
            user = User(**validated_data)
            user.role = self._get_role()
            user.set_password(password)

            request = self.context.get("request")
            if request and request.user.is_authenticated:
                user.created_by = request.user

            user.full_clean()
            user.save()
            return user
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"detail": "User with same email or username already exists.", "error": str(exc)}
            )


# ============================================================
# CREATE SERIALIZERS (BY ROLE)
# ============================================================

class PatientCreateSerializer(BaseUserCreateSerializer):
    role_name = Role.PATIENT


class StudentCreateSerializer(BaseUserCreateSerializer):
    role_name = Role.STUDENT

    university = serializers.UUIDField(
        source="studentprofile_profile.university_id",
        read_only=True,
    )
    university_name = serializers.CharField(
        source="studentprofile_profile.university.name",
        read_only=True,
    )

    class Meta(BaseUserCreateSerializer.Meta):
        fields = BaseUserCreateSerializer.Meta.fields + (
            "university",
            "university_name",
        )

    def _get_admin_university_id(self):
        request = self.context.get("request")
        admin_profile = getattr(
            getattr(request, "user", None), "universityadminprofile_profile", None
        )
        university_id = getattr(admin_profile, "university_id", None)
        if not university_id:
            raise serializers.ValidationError(
                {"university": "University Admin must belong to a university."}
            )
        return university_id

    @transaction.atomic
    def create(self, validated_data):
        admin_university_id = self._get_admin_university_id()
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        try:
            user = User(**validated_data)
            user.role = self._get_role()
            # Pass university to signal/profile creation
            user._desired_university_id = admin_university_id
            user.set_password(password)

            request = self.context.get("request")
            if request and request.user.is_authenticated:
                user.created_by = request.user

            user.full_clean()
            user.save()

            profile = user.studentprofile_profile
            profile.university_id = admin_university_id
            profile.full_clean()
            profile.save(update_fields=["university"])
            return user
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"detail": "User with same email or username already exists.", "error": str(exc)}
            )
        except Exception as exc:
            raise serializers.ValidationError({"detail": "Failed to create student.", "error": str(exc)})


class SupervisorCreateSerializer(BaseUserCreateSerializer):
    role_name = Role.SUPERVISOR

    university = serializers.UUIDField(
        source="supervisorprofile_profile.university_id",
        read_only=True,
    )
    university_name = serializers.CharField(
        source="supervisorprofile_profile.university.name",
        read_only=True,
    )

    class Meta(BaseUserCreateSerializer.Meta):
        fields = BaseUserCreateSerializer.Meta.fields + (
            "university",
            "university_name",
        )

    def _get_admin_university_id(self):
        request = self.context.get("request")
        admin_profile = getattr(
            getattr(request, "user", None), "universityadminprofile_profile", None
        )
        university_id = getattr(admin_profile, "university_id", None)
        if not university_id:
            raise serializers.ValidationError(
                {"university": "University Admin must belong to a university."}
            )
        return university_id

    @transaction.atomic
    def create(self, validated_data):
        admin_university_id = self._get_admin_university_id()
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        try:
            user = User(**validated_data)
            user.role = self._get_role()
            user._desired_university_id = admin_university_id
            user.set_password(password)

            request = self.context.get("request")
            if request and request.user.is_authenticated:
                user.created_by = request.user

            user.full_clean()
            user.save()

            profile = user.supervisorprofile_profile
            profile.university_id = admin_university_id
            profile.full_clean()
            profile.save(update_fields=["university"])
            return user
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"detail": "User with same email or username already exists.", "error": str(exc)}
            )
        except Exception as exc:
            raise serializers.ValidationError({"detail": "Failed to create supervisor.", "error": str(exc)})


class UniversityAdminCreateSerializer(BaseUserCreateSerializer):
    role_name = Role.UNIVERSITY_ADMIN
    university_id = serializers.UUIDField(write_only=True)
    university = serializers.UUIDField(
        source="universityadminprofile_profile.university_id",
        read_only=True,
    )
    university_name = serializers.CharField(
        source="universityadminprofile_profile.university.name",
        read_only=True,
    )

    class Meta(BaseUserCreateSerializer.Meta):
        fields = BaseUserCreateSerializer.Meta.fields + (
            "university_id",
            "university",
            "university_name",
        )

    @transaction.atomic
    def create(self, validated_data):
        university_id = validated_data.pop("university_id")
        try:
            University.objects.get(id=university_id)
        except University.DoesNotExist:
            raise serializers.ValidationError({"university_id": "Invalid university id."})

        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        try:
            user = User(**validated_data)
            user.role = self._get_role()
            user._desired_university_id = university_id
            user.set_password(password)

            request = self.context.get("request")
            if request and request.user.is_authenticated:
                user.created_by = request.user

            user.full_clean()
            user.save()

            profile = user.universityadminprofile_profile
            profile.university_id = university_id
            profile.full_clean()
            profile.save(update_fields=["university"])
            return user
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"detail": "User with same email or username already exists.", "error": str(exc)}
            )
        except Exception as exc:
            raise serializers.ValidationError({"detail": "Failed to create university admin.", "error": str(exc)})


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
    id = serializers.UUIDField(source="pk", read_only=True)
    university_name = serializers.CharField(
        source="university.name",
        read_only=True,
    )

    class Meta:
        model = StudentProfile
        exclude = ("user",)
        read_only_fields = ("university",)


class SupervisorProfileSerializer(BaseProfileSerializer):
    id = serializers.UUIDField(source="pk", read_only=True)
    university_name = serializers.CharField(
        source="university.name",
        read_only=True,
    )

    class Meta:
        model = SupervisorProfile
        exclude = ("user",)
        read_only_fields = ("university",)


class UniversityAdminProfileSerializer(BaseProfileSerializer):
    university_name = serializers.CharField(
        source="university.name",
        read_only=True,
    )

    class Meta:
        model = UniversityAdminProfile
        exclude = ("user",)
        read_only_fields = ("university",)


class TechSupportProfileSerializer(BaseProfileSerializer):
    class Meta:
        model = TechSupportProfile
        exclude = ("user",)


# ============================================================
# FCM Token
# ============================================================
class FCMTokenSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(max_length=255)

    def validate_fcm_token(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("FCM token cannot be empty.")
        return value
