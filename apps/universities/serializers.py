# apps/universities/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import (
    University,
    Faculty,
    AcademicProgram,
    AcademicYear,
    Course,
    get_or_create_dentistry_faculty,
)
from apps.accounts.models import Role, User


# ============================================================
# University Serializers
# ============================================================

class UniversityListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing universities.
    """

    class Meta:
        model = University
        fields = (
            "id",
            "name",
            "short_name",
            "address",
            "email",
            "phone",
            "city",
            "country",
            "is_active",
        )


class UniversityDetailSerializer(serializers.ModelSerializer):
    """
    Full university representation with aggregated counts.
    """

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
        fields = (
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
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "faculties_count",
            "programs_count",
            "academic_years_count",
        )


class UniversityCreateSerializer(serializers.ModelSerializer):
    """
    Serializer used by IT Support to create universities.
    """

    class Meta:
        model = University
        fields = (
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
        )

    def validate_name(self, value):
        if University.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError(
                _("A university with this name already exists.")
            )
        return value.strip()

    def validate(self, attrs):
        short_name = attrs.get("short_name")
        if short_name is not None and short_name.strip() == "":
            raise serializers.ValidationError(
                {"short_name": _("Short name cannot be empty if provided.")}
            )
        return attrs


# ============================================================
# Faculty Serializers
# ============================================================

class FacultySerializer(serializers.ModelSerializer):
    """
    Faculty serializer scoped to a single university.
    """

    university_name = serializers.CharField(
        source="university.name",
        read_only=True,
    )

    class Meta:
        model = Faculty
        fields = (
            "id",
            "university",
            "university_name",
            "name",
            "description",
            "is_active",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "university_name",
        )

    def validate(self, attrs):
        university = attrs.get("university")
        name = attrs.get("name")

        if university:
            if not university.is_active:
                raise serializers.ValidationError(
                    _("Cannot add faculty to an inactive university.")
                )

            qs = Faculty.objects.filter(
                university=university,
                name__iexact=name,
            )

            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError(
                    {"name": _("Faculty name must be unique within the university.")}
                )

        return attrs


# ============================================================
# Academic Program Serializers
# ============================================================

class AcademicProgramSerializer(serializers.ModelSerializer):
    """
    Academic program serializer.
    """

    university_name = serializers.CharField(
        source="university.name",
        read_only=True,
    )
    faculty_name = serializers.CharField(
        source="faculty.name",
        read_only=True,
    )

    class Meta:
        model = AcademicProgram
        fields = (
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
        )
        read_only_fields = (
            "id",
            "created_at",
            "university_name",
            "faculty_name",
        )

    def validate(self, attrs):
        university = attrs.get("university")
        faculty = attrs.get("faculty")
        code = attrs.get("code")

        if faculty and university and faculty.university_id != university.id:
            raise serializers.ValidationError(
                {"faculty": _("Faculty must belong to the same university.")}
            )

        if university and code:
            qs = AcademicProgram.objects.filter(
                university=university,
                code__iexact=code,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError(
                    {"code": _("Program code must be unique within the university.")}
                )

        return attrs


# ============================================================
# Course Serializers
# ============================================================

class CourseSerializer(serializers.ModelSerializer):
    university_name = serializers.CharField(source="university.name", read_only=True)
    faculty_name = serializers.CharField(source="faculty.name", read_only=True)
    supervisor_email = serializers.EmailField(source="supervisor.email", read_only=True)
    students_emails = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "university",
            "university_name",
            "faculty",
            "faculty_name",
            "academic_year",
            "program",
            "supervisor",
            "supervisor_email",
            "students",
            "students_emails",
            "name",
            "code",
            "description",
            "credits",
            "is_active",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "university",
            "university_name",
            "faculty_name",
            "supervisor_email",
            "students_emails",
        )

    def get_students_emails(self, obj):
        return list(obj.students.values_list("email", flat=True))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        university = self.context.get("university")
        if university:
            # Scope selectable relations to this university for safer admin UX
            self.fields["faculty"].queryset = Faculty.objects.filter(university=university, is_active=True)
            self.fields["academic_year"].queryset = AcademicYear.objects.filter(university=university, is_active=True)
            self.fields["program"].queryset = AcademicProgram.objects.filter(university=university, is_active=True)
            self.fields["supervisor"].queryset = User.objects.filter(
                role__name=Role.SUPERVISOR,
                supervisorprofile_profile__university=university,
            )
            self.fields["students"].queryset = User.objects.filter(
                role__name=Role.STUDENT,
                studentprofile_profile__university=university,
            )

    def validate_supervisor(self, user):
        if not user:
            return user
        if getattr(user.role, "name", None) != Role.SUPERVISOR:
            raise serializers.ValidationError(_("Supervisor must have SUPERVISOR role."))
        return user

    def validate_students(self, students):
        for student in students:
            if getattr(student.role, "name", None) != Role.STUDENT:
                raise serializers.ValidationError(_("All enrolled users must have STUDENT role."))
        return students

    def validate(self, attrs):
        university = self.context.get("university")
        academic_year = attrs.get("academic_year")
        program = attrs.get("program")
        supervisor = attrs.get("supervisor")
        students = attrs.get("students", [])
        faculty = attrs.get("faculty")
        code = attrs.get("code")

        if academic_year and academic_year.university_id != university.id:
            raise serializers.ValidationError(_("Academic year must belong to this university."))
        if program and program.university_id != university.id:
            raise serializers.ValidationError(_("Program must belong to this university."))

        if supervisor:
            sup_univ = getattr(getattr(supervisor, "supervisorprofile_profile", None), "university_id", None)
            if sup_univ and sup_univ != university.id:
                raise serializers.ValidationError(_("Supervisor must belong to this university."))
            if sup_univ is None:
                raise serializers.ValidationError(_("Supervisor must have a university profile."))

        for student in students:
            stu_univ = getattr(getattr(student, "studentprofile_profile", None), "university_id", None)
            if stu_univ and stu_univ != university.id:
                raise serializers.ValidationError(_("Student must belong to this university."))
            if stu_univ is None:
                raise serializers.ValidationError(_("Student must have a university profile."))

        # Ensure code uniqueness per university (update-safe)
        if university and code:
            qs = Course.objects.filter(university=university, code__iexact=code)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"code": _("Course code must be unique within the university.")})

        # Auto-assign default faculty if none provided
        if not faculty:
            attrs["faculty"] = get_or_create_dentistry_faculty(university)

        return attrs

    def create(self, validated_data):
        university = self.context["university"]
        students = validated_data.pop("students", [])
        # Auto-assign default dentistry faculty
        if not validated_data.get("faculty"):
            validated_data["faculty"] = get_or_create_dentistry_faculty(university)
        course = Course.objects.create(university=university, **validated_data)
        if students:
            course.students.set(students)
        return course

    def update(self, instance, validated_data):
        students = validated_data.pop("students", None)
        result = super().update(instance, validated_data)
        if students is not None:
            result.students.set(students)
        return result


# ============================================================
# Academic Year Serializers
# ============================================================

class AcademicYearSerializer(serializers.ModelSerializer):
    """
    Academic year serializer.
    """

    university_name = serializers.CharField(
        source="university.name",
        read_only=True,
    )

    class Meta:
        model = AcademicYear
        fields = (
            "id",
            "university",
            "university_name",
            "name",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "university_name",
        )

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        university = attrs.get("university")
        is_active = attrs.get("is_active")

        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError(
                _("End date must be after start date.")
            )

        if is_active and university:
            qs = AcademicYear.objects.filter(
                university=university,
                is_active=True,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError(
                    _("Only one active academic year is allowed per university.")
                )

        return attrs
