# apps/cases/test_security.py
"""
Cross-tenant regression tests: universities IDOR, case takeover,
unscoped-case access.
"""
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from rest_framework import status

from apps.cases.models import Case, CaseAssignmentRequest, CaseSession
from apps.cases.services import assign_case
from medismile.testing import TwoUniversitiesTestCase


class UniversityDetailIDORTests(TwoUniversitiesTestCase):
    def url(self, uni):
        return reverse("university-detail", args=[uni.id])

    def test_any_authenticated_user_can_read(self):
        self.login(self.patient)
        response = self.client.get(self.url(self.uni_a))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "University A")

    def test_patient_cannot_modify_university(self):
        self.login(self.patient)
        response = self.client.patch(self.url(self.uni_a), {"name": "Hijacked"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.uni_a.refresh_from_db()
        self.assertEqual(self.uni_a.name, "University A")

    def test_student_and_supervisor_cannot_modify_university(self):
        for user in (self.student_a, self.supervisor_a):
            self.login(user)
            response = self.client.patch(self.url(self.uni_a), {"is_active": False}, format="json")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, user.username)
        self.uni_a.refresh_from_db()
        self.assertTrue(self.uni_a.is_active)

    def test_admin_cannot_modify_another_university(self):
        self.login(self.admin_b)
        response = self.client.patch(self.url(self.uni_a), {"name": "Hijacked"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_modify_own_university(self):
        self.login(self.admin_a)
        response = self.client.patch(self.url(self.uni_a), {"city": "New City"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.uni_a.refresh_from_db()
        self.assertEqual(self.uni_a.city, "New City")

    def test_tech_support_can_modify_any_university(self):
        self.login(self.tech)
        response = self.client.patch(self.url(self.uni_b), {"city": "Ops City"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_inactive_university_hidden_from_non_tech_users(self):
        self.uni_b.is_active = False
        self.uni_b.save(update_fields=["is_active"])
        self.login(self.patient)
        self.assertEqual(self.client.get(self.url(self.uni_b)).status_code, status.HTTP_404_NOT_FOUND)
        self.login(self.tech)
        self.assertEqual(self.client.get(self.url(self.uni_b)).status_code, status.HTTP_200_OK)


class CaseAssignmentTakeoverTests(TwoUniversitiesTestCase):
    def setUp(self):
        self.case = Case.objects.create(
            patient=self.patient,
            title="Tooth pain",
            description="Pain in lower molar",
            university=self.uni_a,
            status=Case.Status.NEEDS_ASSIGNMENT_APPROVAL,
            is_public=True,
        )
        self.request = CaseAssignmentRequest.objects.create(case=self.case, student=self.student_a)

    def decide(self, user, decision="accept"):
        self.login(user)
        return self.client.patch(
            reverse("case-assignment-request-decision", args=[self.request.id]),
            {"decision": decision},
            format="json",
        )

    def test_supervisor_of_other_university_cannot_accept(self):
        response = self.decide(self.supervisor_b)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.case.refresh_from_db()
        self.assertEqual(self.case.university_id, self.uni_a.id)
        self.assertIsNone(self.case.supervisor_id)
        self.assertEqual(self.case.status, Case.Status.NEEDS_ASSIGNMENT_APPROVAL)

    def test_non_supervisor_cannot_decide(self):
        for user in (self.patient, self.student_a, self.admin_a):
            self.assertEqual(self.decide(user).status_code, status.HTTP_404_NOT_FOUND, user.username)

    def test_supervisor_of_same_university_can_accept(self):
        response = self.decide(self.supervisor_a)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, Case.Status.ASSIGNED)
        self.assertEqual(self.case.supervisor_id, self.supervisor_a.id)
        self.assertEqual(self.case.university_id, self.uni_a.id)

    def test_assign_case_never_rehomes_a_case(self):
        with self.assertRaises(PermissionDenied):
            assign_case(supervisor=self.supervisor_b, case=self.case, student=self.student_b)
        self.case.refresh_from_db()
        self.assertEqual(self.case.university_id, self.uni_a.id)

    def test_other_university_supervisor_cannot_use_assignment_decision_endpoint(self):
        self.login(self.supervisor_b)
        response = self.client.post(
            reverse("supervisor-assignment-decision", args=[self.case.id]),
            {"decision": "approve"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_assignment_approval_sets_supervisor(self):
        self.login(self.supervisor_a)
        response = self.client.post(
            reverse("supervisor-assignment-decision", args=[self.case.id]),
            {"decision": "approve"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.case.refresh_from_db()
        self.assertEqual(self.case.student_id, self.student_a.id)
        self.assertEqual(self.case.supervisor_id, self.supervisor_a.id)


class UnscopedCaseAccessTests(TwoUniversitiesTestCase):
    """Cases with university=NULL must not be open to every admin/supervisor."""

    def setUp(self):
        self.case = Case.objects.create(patient=self.patient, title="AI case", description="From AI")

    def test_admin_without_university_cannot_manage_unscoped_case(self):
        self.login(self.admin_unscoped)
        response = self.client.patch(
            reverse("case-status-update", args=[self.case.id]), {"status": "accepted"}, format="json"
        )
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_admin_of_unrelated_university_cannot_manage_unscoped_case(self):
        self.login(self.admin_b)
        response = self.client.patch(
            reverse("case-status-update", args=[self.case.id]), {"status": "accepted"}, format="json"
        )
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_session_list_is_scoped_for_admins(self):
        scoped = Case.objects.create(
            patient=self.patient,
            title="Scoped",
            description="d",
            university=self.uni_a,
            student=self.student_a,
            supervisor=self.supervisor_a,
            status=Case.Status.IN_PROGRESS,
        )
        CaseSession.objects.create(
            case=scoped,
            student=self.student_a,
            supervisor=self.supervisor_a,
            notes="clinical notes",
        )
        url = reverse("case-session-list", args=[scoped.id])
        self.login(self.admin_b)
        self.assertEqual(len(self.client.get(url).data), 0)
        self.login(self.admin_a)
        self.assertEqual(len(self.client.get(url).data), 1)
