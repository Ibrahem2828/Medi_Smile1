# medismile/testing.py
"""
Shared fixtures for cross-tenant (multi-university) security tests.

Builds two universities (A and B), each with a student, supervisor and
University Admin, plus a patient, a tech-support user, and helpers.
"""
from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.universities.models import University


class TwoUniversitiesTestCase(APITestCase):
    @classmethod
    def _make_user(cls, *, username, role, university=None, **extra):
        user = User(email=f"{username}@test.com", username=username, role=role, **extra)
        if university is not None:
            user._desired_university_id = university.id
        user.set_password("Passw0rd!")
        user.save()
        return user

    @classmethod
    def setUpTestData(cls):
        cls.roles = {
            name: Role.objects.get_or_create(name=name)[0]
            for name in (
                Role.PATIENT,
                Role.STUDENT,
                Role.SUPERVISOR,
                Role.UNIVERSITY_ADMIN,
                Role.TECH_SUPPORT,
            )
        }
        cls.uni_a = University.objects.create(name="University A", city="A", country="X")
        cls.uni_b = University.objects.create(name="University B", city="B", country="X")

        cls.patient = cls._make_user(username="patient", role=cls.roles[Role.PATIENT])
        cls.other_patient = cls._make_user(username="patient2", role=cls.roles[Role.PATIENT])
        cls.tech = cls._make_user(username="tech", role=cls.roles[Role.TECH_SUPPORT], is_staff=True)

        cls.student_a = cls._make_user(username="student_a", role=cls.roles[Role.STUDENT], university=cls.uni_a)
        cls.student_b = cls._make_user(username="student_b", role=cls.roles[Role.STUDENT], university=cls.uni_b)
        cls.supervisor_a = cls._make_user(
            username="supervisor_a", role=cls.roles[Role.SUPERVISOR], university=cls.uni_a
        )
        cls.supervisor_b = cls._make_user(
            username="supervisor_b", role=cls.roles[Role.SUPERVISOR], university=cls.uni_b
        )
        cls.admin_a = cls._make_user(
            username="admin_a", role=cls.roles[Role.UNIVERSITY_ADMIN], university=cls.uni_a
        )
        cls.admin_b = cls._make_user(
            username="admin_b", role=cls.roles[Role.UNIVERSITY_ADMIN], university=cls.uni_b
        )
        for admin, uni in ((cls.admin_a, cls.uni_a), (cls.admin_b, cls.uni_b)):
            profile = admin.universityadminprofile_profile
            profile.university = uni
            profile.save()
        # An admin whose profile has no university at all.
        cls.admin_unscoped = cls._make_user(username="admin_x", role=cls.roles[Role.UNIVERSITY_ADMIN])

    def setUp(self):
        super().setUp()
        # Throttle counters live in the cache; isolate tests from each other.
        cache.clear()

    def login(self, user):
        self.client.force_authenticate(user=user)
