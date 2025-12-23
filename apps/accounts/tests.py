# apps/accounts/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model

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
# USER MODEL TESTS
# ============================================================
class UserModelTest(TestCase):
    """Tests for the custom User model with RBAC."""

    @classmethod
    def setUpTestData(cls):
        cls.patient_role = Role.objects.get(name=Role.PATIENT)
        cls.student_role = Role.objects.get(name=Role.STUDENT)

    def test_create_user_default_role(self):
        """User should be created with default PATIENT role."""
        user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            password="TestPass123!",
            role=self.patient_role,
        )

        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("TestPass123!"))
        self.assertIsNotNone(user.role)
        self.assertEqual(user.role.name, Role.PATIENT)

    def test_create_user_with_specific_role(self):
        """User can be created with a specific role."""
        user = User.objects.create_user(
            email="student@example.com",
            username="student",
            first_name="Student",
            last_name="User",
            password="TestPass123!",
            role=self.student_role,
        )

        self.assertEqual(user.role.name, Role.STUDENT)

    def test_create_superuser(self):
        """Superuser should have staff and superuser flags."""
        admin_user = User.objects.create_superuser(
            email="admin@example.com",
            username="admin",
            first_name="Admin",
            last_name="User",
            password="AdminPass123!",
        )

        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)


# ============================================================
# PROFILE + SIGNALS TESTS
# ============================================================
class ProfileSignalTest(TestCase):
    """Ensure profiles are auto-created via signals."""

    @classmethod
    def setUpTestData(cls):
        cls.roles = {
            Role.PATIENT: Role.objects.get(name=Role.PATIENT),
            Role.STUDENT: Role.objects.get(name=Role.STUDENT),
            Role.SUPERVISOR: Role.objects.get(name=Role.SUPERVISOR),
            Role.UNIVERSITY_ADMIN: Role.objects.get(name=Role.UNIVERSITY_ADMIN),
            Role.TECH_SUPPORT: Role.objects.get(name=Role.TECH_SUPPORT),
        }

    def _create_user(self, role_name, email):
        return User.objects.create_user(
            email=email,
            username=role_name,
            first_name=role_name.capitalize(),
            last_name="User",
            password="TestPass123!",
            role=self.roles[role_name],
        )

    def test_patient_profile_created(self):
        user = self._create_user(Role.PATIENT, "patient@test.com")
        self.assertTrue(PatientProfile.objects.filter(user=user).exists())

    def test_student_profile_created(self):
        user = self._create_user(Role.STUDENT, "student@test.com")
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())

    def test_supervisor_profile_created(self):
        user = self._create_user(Role.SUPERVISOR, "supervisor@test.com")
        self.assertTrue(SupervisorProfile.objects.filter(user=user).exists())

    def test_university_admin_profile_created(self):
        user = self._create_user(Role.UNIVERSITY_ADMIN, "admin@test.com")
        self.assertTrue(UniversityAdminProfile.objects.filter(user=user).exists())

    def test_tech_support_profile_created(self):
        user = self._create_user(Role.TECH_SUPPORT, "tech@test.com")
        self.assertTrue(TechSupportProfile.objects.filter(user=user).exists())

    def test_only_one_profile_created(self):
        """Ensure OneToOne integrity (no duplicate profiles)."""
        user = self._create_user(Role.PATIENT, "single@test.com")
        PatientProfile.objects.get(user=user)

        self.assertEqual(PatientProfile.objects.filter(user=user).count(), 1)


# ============================================================
# ROLE CHANGE SAFETY TEST
# ============================================================
class RoleChangeTest(TestCase):
    """Ensure role change does not break profiles."""

    def test_role_change_creates_new_profile(self):
        patient_role = Role.objects.get(name=Role.PATIENT)
        student_role = Role.objects.get(name=Role.STUDENT)

        user = User.objects.create_user(
            email="change@test.com",
            username="changer",
            first_name="Change",
            last_name="User",
            password="TestPass123!",
            role=patient_role,
        )

        # initial profile
        self.assertTrue(PatientProfile.objects.filter(user=user).exists())

        # change role
        user.role = student_role
        user.save()

        # new profile exists, old is preserved
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())
        self.assertTrue(PatientProfile.objects.filter(user=user).exists())
