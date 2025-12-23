# apps/universities/tests.py

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.universities.models import University, Faculty, AcademicProgram, AcademicYear


class UniversityAPITestCase(APITestCase):

    def setUp(self):
        # Roles
        self.admin_role = Role.objects.create(name=Role.UNIVERSITY_ADMIN)
        self.student_role = Role.objects.create(name=Role.STUDENT)

        # Users
        self.university_admin = User.objects.create_user(
            email="admin@test.com",
            username="admin",
            password="password123",
            role=self.admin_role,
        )

        self.student = User.objects.create_user(
            email="student@test.com",
            username="student",
            password="password123",
            role=self.student_role,
        )

        self.client.force_authenticate(user=self.university_admin)

    def test_university_admin_can_create_university(self):
        url = reverse("university-create")
        payload = {
            "name": "Test University",
            "short_name": "TU",
            "city": "Test City",
            "country": "Test Country",
            "email": "info@testuni.edu",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(University.objects.count(), 1)

    def test_student_cannot_create_university(self):
        self.client.force_authenticate(user=self.student)
        url = reverse("university-create")

        response = self.client.post(url, {"name": "Blocked University"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class FacultyAPITestCase(APITestCase):

    def setUp(self):
        self.role = Role.objects.create(name=Role.UNIVERSITY_ADMIN)

        self.admin = User.objects.create_user(
            email="admin2@test.com",
            username="admin2",
            password="password123",
            role=self.role,
        )

        self.university = University.objects.create(
            name="Faculty Test University"
        )

        self.client.force_authenticate(user=self.admin)

    def test_create_faculty(self):
        url = reverse(
            "faculty-list-create",
            kwargs={"university_id": self.university.id},
        )

        payload = {
            "name": "Faculty of Dentistry",
            "description": "Dental faculty",
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Faculty.objects.count(), 1)


class AcademicProgramAPITestCase(APITestCase):

    def setUp(self):
        self.role = Role.objects.create(name=Role.UNIVERSITY_ADMIN)

        self.admin = User.objects.create_user(
            email="admin3@test.com",
            username="admin3",
            password="password123",
            role=self.role,
        )

        self.university = University.objects.create(
            name="Program Test University"
        )

        self.faculty = Faculty.objects.create(
            university=self.university,
            name="Faculty of Dentistry",
        )

        self.client.force_authenticate(user=self.admin)

    def test_create_academic_program(self):
        url = reverse(
            "academic-program-list-create",
            kwargs={"university_id": self.university.id},
        )

        payload = {
            "faculty": str(self.faculty.id),
            "name": "Bachelor of Dental Surgery",
            "code": "BDS",
            "level": "bachelor",
            "duration_years": 5,
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AcademicProgram.objects.count(), 1)


class AcademicYearAPITestCase(APITestCase):

    def setUp(self):
        self.role = Role.objects.create(name=Role.UNIVERSITY_ADMIN)

        self.admin = User.objects.create_user(
            email="admin4@test.com",
            username="admin4",
            password="password123",
            role=self.role,
        )

        self.university = University.objects.create(
            name="Year Test University"
        )

        self.client.force_authenticate(user=self.admin)

    def test_create_academic_year(self):
        url = reverse(
            "academic-year-list-create",
            kwargs={"university_id": self.university.id},
        )

        payload = {
            "name": "2024/2025",
            "start_date": "2024-09-01",
            "end_date": "2025-06-30",
            "is_active": True,
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AcademicYear.objects.count(), 1)
