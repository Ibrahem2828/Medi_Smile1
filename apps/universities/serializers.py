# apps/universities/serializers.py

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import (
    University,
    Faculty,
    AcademicProgram,
    AcademicYear,
)


# ============================================================
# University Serializers
# ============================================================

class UniversityListSerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = [
            "id",
            "name",
            "short_name",
            "city",
            "country",
            "is_active",
        ]


class UniversityDetailSerializer(serializers.ModelSerializer):
    faculties_count = serializers.IntegerField(
        source="faculties.count", read_only=True
    )
    programs_count = serializers.IntegerField(
        source="programs.count", read_only=True
    )
    academic_years_count = serializers.IntegerField(
        source="academic_years.count", read_only=True
    )

    class Meta:
        model = University
        fields = [
            "id",
            "name",
            "short_name",
            "description",
            "address",
            "city",
            "country",
            "website",
            "email",
            "phone",
            "logo",
            "is_active",
            "faculties_count",
            "programs_count",
            "academic_years_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class UniversityCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = [
            "name",
            "short_name",
            "description",
            "address",
            "city",
            "country",
            "website",
            "email",
            "phone",
            "logo",
        ]

    def validate_name(self, value):
        if University.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError(
                _("A university with this name already exists.")
            )
        return value


# ============================================================
# Faculty Serializers
# ============================================================

class FacultySerializer(serializers.ModelSerializer):
    university_name = serializers.CharField(
        source="university.name", read_only=True
    )

    class Meta:
        model = Faculty
        fields = [
            "id",
            "university",
            "university_name",
            "name",
            "description",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# ============================================================
# Academic Program Serializers
# ============================================================

class AcademicProgramSerializer(serializers.ModelSerializer):
    university_name = serializers.CharField(
        source="university.name", read_only=True
    )
    faculty_name = serializers.CharField(
        source="faculty.name", read_only=True
    )

    class Meta:
        model = AcademicProgram
        fields = [
            "id",
            "university",
            "university_name",
            "faculty",
            "faculty_name",
            "name",
            "code",
            "level",
            "duration_years",
            "description",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        university = attrs.get("university")
        code = attrs.get("code")

        if university and code:
            if AcademicProgram.objects.filter(
                university=university, code=code
            ).exists():
                raise serializers.ValidationError(
                    {"code": _("Program code must be unique within the university.")}
                )
        return attrs


# ============================================================
# Academic Year Serializers
# ============================================================

class AcademicYearSerializer(serializers.ModelSerializer):
    university_name = serializers.CharField(
        source="university.name", read_only=True
    )

    class Meta:
        model = AcademicYear
        fields = [
            "id",
            "university",
            "university_name",
            "name",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError(
                _("End date must be after start date.")
            )
        return attrs


# ============================================================
# Backward compatibility alias (if needed elsewhere)
# ============================================================

UniversitySerializer = UniversityDetailSerializer
