# apps/ai/test_images_and_scoping.py
"""
Patient image upload + image-based AI diagnosis, failure handling,
SSRF guard on image_urls, and university scoping of AI diagnoses.
"""
import io
import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status

from apps.ai.integrations.engine import AIEngineError
from apps.ai.models import AIDiagnosis, AIImageUpload, DiagnosisStatus
from apps.cases.models import Case
from medismile.testing import TwoUniversitiesTestCase

_ENGINE_OK = {
    "diagnosis_label": "caries",
    "primary_diagnosis": "caries",
    "confidence_level": "high",
    "severity_level": "moderate",
    "urgency_level": "non_urgent",
    "metadata": {"fallback": {"mode": "full"}},
}
_SYMPTOMS = "ألم شديد في الضرس عند شرب الماء البارد"


def _image_bytes(fmt="JPEG", size=(64, 48), exif_gps=False):
    buf = io.BytesIO()
    img = Image.new("RGB", size, (200, 180, 160))
    kwargs = {}
    if exif_gps and fmt == "JPEG":
        exif = Image.Exif()
        exif[0x010F] = "PhoneMaker"  # Make
        kwargs["exif"] = exif.tobytes()
    img.save(buf, format=fmt, **kwargs)
    return buf.getvalue()


def _upload(name="photo.jpg", content=None, content_type="image/jpeg"):
    return SimpleUploadedFile(name, content if content is not None else _image_bytes(), content_type=content_type)


class _MediaTestCase(TwoUniversitiesTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media = tempfile.mkdtemp(prefix="medismile-test-media-")
        cls._override = override_settings(MEDIA_ROOT=cls._media)
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        shutil.rmtree(cls._media, ignore_errors=True)
        super().tearDownClass()


class AIImageUploadTests(_MediaTestCase):
    url = reverse("ai:ai-image-upload")

    def test_patient_uploads_valid_image(self):
        self.login(self.patient)
        response = self.client.post(self.url, {"image": _upload()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        upload = AIImageUpload.objects.get(id=response.data["id"])
        self.assertEqual(upload.patient_id, self.patient.id)
        self.assertEqual(upload.content_type, "image/jpeg")
        self.assertEqual((upload.width, upload.height), (64, 48))
        self.assertIn("/api/ai/images/", response.data["file_url"])

    def test_metadata_is_stripped(self):
        self.login(self.patient)
        response = self.client.post(
            self.url, {"image": _upload(content=_image_bytes(exif_gps=True))}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        upload = AIImageUpload.objects.get(id=response.data["id"])
        with upload.image.open("rb") as fh, Image.open(fh) as img:
            self.assertEqual(len(img.getexif()), 0)

    def test_rejects_non_image_even_with_image_content_type(self):
        self.login(self.patient)
        fake = _upload(name="x.jpg", content=b"<script>alert(1)</script>", content_type="image/jpeg")
        response = self.client.post(self.url, {"image": fake}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(AIImageUpload.objects.exists())

    def test_rejects_unsupported_format(self):
        self.login(self.patient)
        gif = _upload(name="x.gif", content=_image_bytes(fmt="GIF"), content_type="image/gif")
        response = self.client.post(self.url, {"image": gif}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(AI_IMAGE_MAX_BYTES=100)
    def test_rejects_oversized_file(self):
        self.login(self.patient)
        response = self.client.post(self.url, {"image": _upload()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(AI_IMAGE_MAX_PIXELS=1000)
    def test_rejects_excessive_resolution(self):
        self.login(self.patient)
        response = self.client.post(self.url, {"image": _upload()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(AI_IMAGE_MAX_SIDE=32)
    def test_large_images_are_downscaled(self):
        self.login(self.patient)
        response = self.client.post(self.url, {"image": _upload()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertLessEqual(max(response.data["width"], response.data["height"]), 32)

    def test_non_patient_cannot_upload(self):
        self.login(self.student_a)
        response = self.client.post(self.url, {"image": _upload()}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_file_download_is_owner_only(self):
        self.login(self.patient)
        upload_id = self.client.post(self.url, {"image": _upload()}, format="multipart").data["id"]
        file_url = reverse("ai:ai-image-file", args=[upload_id])

        response = self.client.get(file_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/jpeg")

        self.login(self.other_patient)
        self.assertEqual(self.client.get(file_url).status_code, status.HTTP_404_NOT_FOUND)


@patch("apps.ai.services._get_engine_config")
class AIDiagnoseWithImagesTests(_MediaTestCase):
    url = reverse("ai:ai-diagnose")

    def _upload_id(self, user=None):
        self.login(user or self.patient)
        response = self.client.post(reverse("ai:ai-image-upload"), {"image": _upload()}, format="multipart")
        return response.data["id"]

    @patch("apps.ai.services.analyze_case", return_value=_ENGINE_OK)
    def test_json_with_image_ids_sends_bytes_to_vision(self, analyze_mock, _cfg):
        image_id = self._upload_id()
        response = self.client.post(
            self.url, {"symptoms_text": _SYMPTOMS, "image_ids": [image_id]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        kwargs = analyze_mock.call_args.kwargs
        self.assertEqual(len(kwargs["images"]), 1)
        self.assertTrue(kwargs["images"][0].content.startswith(b"\xff\xd8"))  # JPEG magic
        self.assertEqual(kwargs["image_urls"], [])
        upload = AIImageUpload.objects.get(id=image_id)
        self.assertEqual(str(upload.diagnosis_id), response.data["diagnosis"]["id"])

    @patch("apps.ai.services.analyze_case", return_value=_ENGINE_OK)
    def test_multipart_with_file_in_one_call(self, analyze_mock, _cfg):
        self.login(self.patient)
        response = self.client.post(
            self.url, {"symptoms_text": _SYMPTOMS, "image": _upload()}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(len(analyze_mock.call_args.kwargs["images"]), 1)
        self.assertEqual(AIImageUpload.objects.filter(patient=self.patient).count(), 1)

    @patch("apps.ai.services.analyze_case", return_value=_ENGINE_OK)
    def test_cannot_use_another_patients_image(self, analyze_mock, _cfg):
        foreign_id = self._upload_id(user=self.other_patient)
        self.login(self.patient)
        response = self.client.post(
            self.url, {"symptoms_text": _SYMPTOMS, "image_ids": [foreign_id]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        analyze_mock.assert_not_called()

    @patch("apps.ai.services.analyze_case", return_value=_ENGINE_OK)
    def test_image_cannot_be_reused(self, analyze_mock, _cfg):
        image_id = self._upload_id()
        first = self.client.post(self.url, {"symptoms_text": _SYMPTOMS, "image_ids": [image_id]}, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        second = self.client.post(self.url, {"symptoms_text": _SYMPTOMS, "image_ids": [image_id]}, format="json")
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.ai.services.analyze_case", return_value=_ENGINE_OK)
    def test_image_urls_on_untrusted_host_rejected(self, analyze_mock, _cfg):
        self.login(self.patient)
        for url in ("http://169.254.169.254/latest/meta-data/", "https://evil.example/x.jpg"):
            response = self.client.post(
                self.url, {"symptoms_text": _SYMPTOMS, "image_urls": [url]}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, url)
        analyze_mock.assert_not_called()

    @override_settings(AI_IMAGE_URL_ALLOWED_HOSTS=["cdn.medismile.test"])
    @patch("apps.ai.services.analyze_case", return_value=_ENGINE_OK)
    def test_image_urls_on_allowed_host_accepted(self, analyze_mock, _cfg):
        self.login(self.patient)
        response = self.client.post(
            self.url,
            {"symptoms_text": _SYMPTOMS, "image_urls": ["https://cdn.medismile.test/a.jpg"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(analyze_mock.call_args.kwargs["image_urls"], ["https://cdn.medismile.test/a.jpg"])

    @patch("apps.ai.services.analyze_case", side_effect=AIEngineError("all engines down"))
    def test_engine_failure_returns_503_and_persists_failed_record(self, _analyze, _cfg):
        self.login(self.patient)
        response = self.client.post(self.url, {"symptoms_text": _SYMPTOMS}, format="json")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["diagnosis"]["status"], DiagnosisStatus.FAILED)
        diagnosis = AIDiagnosis.objects.get(id=response.data["diagnosis"]["id"])
        self.assertEqual(diagnosis.status, DiagnosisStatus.FAILED)
        self.assertEqual(diagnosis.ai_metadata.get("engine_error"), "all engines down")


class AIDiagnosisUniversityScopingTests(TwoUniversitiesTestCase):
    """Admins must never see diagnoses of unscoped (university=NULL) cases."""

    def setUp(self):
        unscoped_case = Case.objects.create(patient=self.patient, title="AI", description="d")
        scoped_case = Case.objects.create(
            patient=self.other_patient, title="Scoped", description="d", university=self.uni_a
        )
        self.unscoped = AIDiagnosis.objects.create(
            case=unscoped_case, patient=self.patient, requested_by=self.patient, raw_symptoms="x"
        )
        self.scoped = AIDiagnosis.objects.create(
            case=scoped_case, patient=self.other_patient, requested_by=self.other_patient, raw_symptoms="y"
        )
        self.list_url = reverse("ai:ai-diagnosis-list")

    def _ids(self, response):
        items = response.data["results"] if isinstance(response.data, dict) else response.data
        return {item["id"] for item in items}

    def test_admin_without_university_sees_nothing(self):
        self.login(self.admin_unscoped)
        self.assertEqual(self._ids(self.client.get(self.list_url)), set())
        detail = self.client.get(reverse("ai:ai-diagnosis-detail", args=[self.unscoped.id]))
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_sees_only_own_university(self):
        self.login(self.admin_a)
        self.assertEqual(self._ids(self.client.get(self.list_url)), {str(self.scoped.id)})
        self.login(self.admin_b)
        self.assertEqual(self._ids(self.client.get(self.list_url)), set())
