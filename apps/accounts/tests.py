# apps/accounts/tests.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role, PatientProfile, StudentProfile
from apps.universities.models import University


class AccountsBaseTestCase(APITestCase):
    """
    Base setup for accounts tests.
    """

    @classmethod
    def setUpTestData(cls):
        cls.patient_role = Role.objects.create(name=Role.PATIENT)
        cls.student_role = Role.objects.create(name=Role.STUDENT)
        cls.supervisor_role = Role.objects.create(name=Role.SUPERVISOR)
        cls.university_admin_role = Role.objects.create(name=Role.UNIVERSITY_ADMIN)
        cls.tech_support_role = Role.objects.create(name=Role.TECH_SUPPORT)

        cls.patient_password = "Patient123!"
        cls.student_password = "Student123!"

        cls.patient_user = User.objects.create_user(
            email="patient@test.com",
            username="patient1",
            password=cls.patient_password,
            role=cls.patient_role,
        )

        cls.student_user = User.objects.create_user(
            email="student@test.com",
            username="student1",
            password=cls.student_password,
            role=cls.student_role,
        )


# ============================================================
# LOGIN TESTS
# ============================================================
class LoginTests(AccountsBaseTestCase):
    def test_patient_login_success(self):
        url = reverse("login-patient")
        response = self.client.post(
            url,
            {"email": "patient@test.com", "password": self.patient_password},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], Role.PATIENT)

    def test_patient_login_from_wrong_portal_fails(self):
        """
        Patient tries to login from student portal.
        """
        url = reverse("login-student")
        response = self.client.post(
            url,
            {"email": "patient@test.com", "password": self.patient_password},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_login_success(self):
        url = reverse("login-student")
        response = self.client.post(
            url,
            {"email": "student@test.com", "password": self.student_password},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], Role.STUDENT)


# ============================================================
# SIGNALS TESTS
# ============================================================
class ProfileSignalTests(AccountsBaseTestCase):
    def test_patient_profile_created_automatically(self):
        self.assertTrue(
            PatientProfile.objects.filter(user=self.patient_user).exists()
        )

    def test_student_profile_created_automatically(self):
        self.assertTrue(
            StudentProfile.objects.filter(user=self.student_user).exists()
        )


# ============================================================
# SELF PROFILE ACCESS TESTS
# ============================================================
class SelfProfileAccessTests(AccountsBaseTestCase):
    def test_patient_can_access_own_profile(self):
        self.client.login(
            email="patient@test.com", password=self.patient_password
        )

        url = reverse("me-patient")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "patient@test.com")

    def test_patient_cannot_access_student_profile_endpoint(self):
        self.client.login(
            email="patient@test.com", password=self.patient_password
        )

        url = reverse("me-student")
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )


# ============================================================
# REGISTRATION TESTS
# ============================================================
class PatientRegistrationTests(APITestCase):
    def setUp(self):
        Role.objects.get_or_create(name=Role.PATIENT)

    def test_patient_self_registration(self):
        url = reverse("register-patient")
        response = self.client.post(
            url,
            {
                "email": "newpatient@test.com",
                "username": "newpatient",
                "first_name": "New",
                "last_name": "Patient",
                "password": "NewPatient123!",
                "password_confirm": "NewPatient123!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            User.objects.filter(email="newpatient@test.com").exists()
        )


# ============================================================
# CREATION / SCOPING RULES
# ============================================================
class CreationAndMeScopeTests(APITestCase):
    def setUp(self):
        # Roles
        self.patient_role = Role.objects.create(name=Role.PATIENT)
        self.student_role = Role.objects.create(name=Role.STUDENT)
        self.university_admin_role = Role.objects.create(name=Role.UNIVERSITY_ADMIN)

        # University
        self.university = University.objects.create(
            name="Scope University",
            city="City",
            country="Country",
        )

        # Users
        self.university_admin = User.objects.create_user(
            email="admin@scope.test",
            username="admin_scope",
            password="Admin123!",
            role=self.university_admin_role,
        )
        # attach university to admin profile
        profile = self.university_admin.universityadminprofile_profile
        profile.university = self.university
        profile.save(update_fields=["university"])

        self.patient = User.objects.create_user(
            email="patient@scope.test",
            username="patient_scope",
            password="Patient123!",
            role=self.patient_role,
        )

    def test_student_creation_requires_university_admin(self):
        # patient cannot create student
        self.client.login(email="patient@scope.test", password="Patient123!")
        url = reverse("create-student")
        res = self.client.post(
            url,
            {
                "email": "student@scope.test",
                "username": "student_scope",
                "first_name": "Stu",
                "last_name": "Dent",
                "password": "Student123!",
                "password_confirm": "Student123!",
            },
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # admin can create student within their university
        self.client.logout()
        self.client.login(email="admin@scope.test", password="Admin123!")
        res = self.client.post(
            url,
            {
                "email": "student@scope.test",
                "username": "student_scope",
                "first_name": "Stu",
                "last_name": "Dent",
                "password": "Student123!",
                "password_confirm": "Student123!",
            },
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        student = User.objects.get(email="student@scope.test")
        self.assertEqual(student.role.name, Role.STUDENT)
        self.assertEqual(student.studentprofile_profile.university, self.university)

    def test_me_endpoints_cannot_change_role_or_university(self):
        # create a student via admin to ensure profile is set
        self.client.login(email="admin@scope.test", password="Admin123!")
        student_create_url = reverse("create-student")
        self.client.post(
            student_create_url,
            {
                "email": "student2@scope.test",
                "username": "student_scope2",
                "first_name": "Stu2",
                "last_name": "Dent2",
                "password": "Student123!",
                "password_confirm": "Student123!",
            },
        )
        self.client.logout()

        self.client.login(email="student2@scope.test", password="Student123!")
        me_url = reverse("me-student")

        # attempt to patch role/university should not be applied
        res = self.client.patch(
            me_url,
            {
                "role": "tech_support",
                "university": None,
            },
            format="json",
        )
        # either forbidden or ignored
        self.assertIn(res.status_code, (status.HTTP_200_OK, status.HTTP_403_FORBIDDEN))

        student = User.objects.get(email="student2@scope.test")
        self.assertEqual(student.role.name, Role.STUDENT)
        self.assertIsNotNone(student.studentprofile_profile.university)
