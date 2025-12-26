# apps/cases/tests.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.universities.models import University
from apps.cases.models import Case


class CasesBaseTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Roles
        cls.patient_role = Role.objects.create(name=Role.PATIENT)
        cls.student_role = Role.objects.create(name=Role.STUDENT)
        cls.supervisor_role = Role.objects.create(name=Role.SUPERVISOR)
        cls.admin_role = Role.objects.create(name=Role.UNIVERSITY_ADMIN)
        cls.tech_role = Role.objects.create(name=Role.TECH_SUPPORT)

        # University
        cls.university = University.objects.create(
            name="Dental University",
            city="City",
            country="Country",
        )

        # Users
        cls.patient = User.objects.create_user(
            email="patient@test.com",
            username="patient",
            password="Patient123!",
            role=cls.patient_role,
        )

        cls.student = User.objects.create_user(
            email="student@test.com",
            username="student",
            password="Student123!",
            role=cls.student_role,
        )

        cls.supervisor = User.objects.create_user(
            email="supervisor@test.com",
            username="supervisor",
            password="Supervisor123!",
            role=cls.supervisor_role,
        )

        cls.admin = User.objects.create_user(
            email="admin@test.com",
            username="admin",
            password="Admin123!",
            role=cls.admin_role,
        )
        cls.admin.universityadminprofile_profile.university = cls.university
        cls.admin.universityadminprofile_profile.save()

        cls.tech = User.objects.create_user(
            email="tech@test.com",
            username="tech",
            password="Tech123!",
            role=cls.tech_role,
            is_staff=True,
        )


# ============================================================
# Case Creation Tests
# ============================================================
class CaseCreationTests(CasesBaseTestCase):
    def test_patient_can_create_case_for_himself(self):
        self.client.login(email="patient@test.com", password="Patient123!")

        url = reverse("case-list-create")
        response = self.client.post(
            url,
            {
                "title": "Tooth Pain",
                "description": "Severe pain in molar",
                "priority": "high",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Case.objects.count(), 1)

    def test_patient_cannot_create_second_active_case(self):
        Case.objects.create(
            title="Case 1",
            description="Desc",
            patient=self.patient,
        )

        self.client.login(email="patient@test.com", password="Patient123!")
        url = reverse("case-list-create")
        response = self.client.post(
            url,
            {
                "title": "Case 2",
                "description": "Another problem",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================
# Case Visibility Tests
# ============================================================
class CaseVisibilityTests(CasesBaseTestCase):
    def setUp(self):
        self.case = Case.objects.create(
            title="Visible Case",
            description="Desc",
            patient=self.patient,
            university=self.university,
            student=self.student,
            supervisor=self.supervisor,
            status=Case.Status.ASSIGNED,
        )

    def test_patient_can_view_own_case(self):
        self.client.login(email="patient@test.com", password="Patient123!")

        url = reverse("case-detail", args=[self.case.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_patient_cannot_view_case(self):
        other_patient = User.objects.create_user(
            email="other@test.com",
            username="other",
            password="Other123!",
            role=self.patient_role,
        )

        self.client.login(email="other@test.com", password="Other123!")
        url = reverse("case-detail", args=[self.case.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ============================================================
# University Scope Tests
# ============================================================
class CaseUniversityScopeTests(CasesBaseTestCase):
    def test_university_admin_sees_only_own_university_cases(self):
        other_university = University.objects.create(
            name="Other University",
            city="X",
            country="Y",
        )

        Case.objects.create(
            title="Case A",
            description="Desc",
            patient=self.patient,
            university=self.university,
        )

        Case.objects.create(
            title="Case B",
            description="Desc",
            patient=self.patient,
            university=other_university,
        )

        self.client.login(email="admin@test.com", password="Admin123!")

        url = reverse("case-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


# ============================================================
# Tech Support Access
# ============================================================
class TechSupportAccessTests(CasesBaseTestCase):
    def test_tech_support_can_view_all_cases(self):
        Case.objects.create(
            title="Global Case",
            description="Desc",
            patient=self.patient,
            university=self.university,
        )

        self.client.login(email="tech@test.com", password="Tech123!")

        url = reverse("case-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
