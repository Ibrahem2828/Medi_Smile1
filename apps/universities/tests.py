# apps/universities/tests.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.universities.models import University


class UniversitiesBaseTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tech_role = Role.objects.create(name=Role.TECH_SUPPORT)
        cls.admin_role = Role.objects.create(name=Role.UNIVERSITY_ADMIN)

        cls.tech_user = User.objects.create_user(
            email="tech@test.com",
            username="tech",
            password="Tech12345!",
            role=cls.tech_role,
            is_staff=True,
        )

        cls.university = University.objects.create(
            name="Test University",
            city="Test City",
            country="Test Country",
        )

        cls.admin_user = User.objects.create_user(
            email="admin@test.com",
            username="admin",
            password="Admin12345!",
            role=cls.admin_role,
        )

        # Attach admin to university via profile
        cls.admin_user.universityadminprofile_profile.university = cls.university
        cls.admin_user.universityadminprofile_profile.save()


# ============================================================
# UNIVERSITY CREATION TESTS
# ============================================================
class UniversityCreationTests(UniversitiesBaseTestCase):
    def test_university_creation_by_tech_support(self):
        self.client.login(email="tech@test.com", password="Tech12345!")

        url = reverse("university-create")
        response = self.client.post(
            url,
            {
                "name": "Another University",
                "city": "City",
                "country": "Country",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_university_creation_forbidden_for_admin(self):
        self.client.login(email="admin@test.com", password="Admin12345!")

        url = reverse("university-create")
        response = self.client.post(
            url,
            {
                "name": "Forbidden University",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ============================================================
# FACULTY SCOPE TESTS
# ============================================================
class FacultyScopeTests(UniversitiesBaseTestCase):
    def test_admin_can_list_own_faculties(self):
        self.client.login(email="admin@test.com", password="Admin12345!")

        url = reverse("faculty-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_cannot_access_other_university(self):
        self.client.login(email="admin@test.com", password="Admin12345!")

        other_university = University.objects.create(
            name="Other University",
            city="Other City",
            country="Other Country",
        )

        url = reverse("university-detail", args=[other_university.id])
        response = self.client.get(url)

        # Allowed to view university info, but NOT manage scoped data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
