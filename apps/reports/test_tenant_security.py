from rest_framework.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status

from apps.cases.models import Case
from apps.reports.models import Report
from apps.reports.services import export_report
from medismile.testing import TwoUniversitiesTestCase


class ReportTenantIsolationTests(TwoUniversitiesTestCase):
    def setUp(self):
        super().setUp()
        self.case_b = Case.objects.create(
            patient=self.other_patient,
            university=self.uni_b,
            title="University B clinical case",
            description="private",
        )

    def test_create_rejects_nested_foreign_case_id(self):
        self.login(self.admin_a)
        response = self.client.post(
            reverse("reports:report-list"),
            {
                "report_type": "university_archive",
                "target_type": "university",
                "target_id": str(self.uni_a.id),
                "content": {"cases": [{"id": str(self.case_b.id)}]},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_export_rejects_a_legacy_foreign_case_reference(self):
        report = Report.objects.create(
            author=self.admin_a,
            author_role="university_admin",
            university=self.uni_a,
            report_type=Report.ReportType.UNIVERSITY_ARCHIVE,
            target_type=Report.TargetType.UNIVERSITY,
            target_id=self.uni_a.id,
            content={"cases": [{"id": str(self.case_b.id)}]},
        )
        with self.assertRaises(ValidationError):
            export_report(actor=self.admin_a, report=report, fmt="pdf")
