# apps/support/tests.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from apps.accounts.models import Role
from apps.universities.models import University  # يفترض موجود
from .models import SupportTicket, SupportTicketResponse

User = get_user_model()


class SupportAppTests(APITestCase):
    def setUp(self):
        # Roles (يفترض Role model موجود ومعبأ مسبقاً في مشروعك)
        # إذا كان Role عبارة عن TextChoices فقط، تجاهل هذا الجزء
        # هنا نتعامل مع Role كـ constants: Role.TECH_SUPPORT...
        self.uni1 = University.objects.create(name="Uni 1")
        self.uni2 = University.objects.create(name="Uni 2")

        self.tech = User.objects.create_user(
            username="tech",
            email="tech@example.com",
            password="Pass12345!",
        )
        self.tech.role = Role.objects.get(name=Role.TECH_SUPPORT) if hasattr(Role, "objects") else self.tech.role
        if hasattr(self.tech, "save"):
            self.tech.save()

        self.admin1 = User.objects.create_user(
            username="admin1",
            email="admin1@example.com",
            password="Pass12345!",
        )
        if hasattr(self.admin1, "role"):
            self.admin1.role = Role.objects.get(name=Role.UNIVERSITY_ADMIN) if hasattr(Role, "objects") else self.admin1.role
        if hasattr(self.admin1, "university_id"):
            self.admin1.university = self.uni1
        self.admin1.save()

        self.patient1 = User.objects.create_user(
            username="p1",
            email="p1@example.com",
            password="Pass12345!",
        )
        if hasattr(self.patient1, "role"):
            self.patient1.role = Role.objects.get(name=Role.PATIENT) if hasattr(Role, "objects") else self.patient1.role
        if hasattr(self.patient1, "university_id"):
            self.patient1.university = self.uni1
        self.patient1.save()

        self.patient2 = User.objects.create_user(
            username="p2",
            email="p2@example.com",
            password="Pass12345!",
        )
        if hasattr(self.patient2, "role"):
            self.patient2.role = Role.objects.get(name=Role.PATIENT) if hasattr(Role, "objects") else self.patient2.role
        if hasattr(self.patient2, "university_id"):
            self.patient2.university = self.uni2
        self.patient2.save()

    def _login(self, user):
        self.client.force_authenticate(user=user)

    def test_patient_can_create_ticket(self):
        self._login(self.patient1)
        url = reverse("support:ticket-list")
        payload = {
            "category": "technical",
            "subject": "Login issue",
            "description": "Cannot login",
            "priority": "medium",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SupportTicket.objects.count(), 1)

    def test_patient_sees_only_own_tickets(self):
        t1 = SupportTicket.objects.create(
            created_by=self.patient1,
            category="technical",
            subject="T1",
            description="D1",
            priority="medium",
        )
        SupportTicket.objects.create(
            created_by=self.patient2,
            category="technical",
            subject="T2",
            description="D2",
            priority="medium",
        )

        self._login(self.patient1)
        url = reverse("support:ticket-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # pagination response: {"results": {"status":"success","data":[...]}}
        data = res.data["results"]["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(t1.id))

    def test_university_admin_sees_university_tickets(self):
        t1 = SupportTicket.objects.create(
            created_by=self.patient1, category="technical", subject="U1", description="x", priority="medium"
        )
        SupportTicket.objects.create(
            created_by=self.patient2, category="technical", subject="U2", description="x", priority="medium"
        )

        self._login(self.admin1)
        url = reverse("support:ticket-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data["results"]["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(t1.id))

    def test_tech_support_sees_all(self):
        SupportTicket.objects.create(created_by=self.patient1, category="technical", subject="A", description="x", priority="medium")
        SupportTicket.objects.create(created_by=self.patient2, category="technical", subject="B", description="x", priority="medium")

        self._login(self.tech)
        url = reverse("support:ticket-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data["results"]["data"]
        self.assertEqual(len(data), 2)

    def test_internal_notes_hidden_from_non_tech(self):
        ticket = SupportTicket.objects.create(created_by=self.patient1, category="technical", subject="S", description="x", priority="medium")
        SupportTicketResponse.objects.create(ticket=ticket, author=self.tech, message="internal", is_internal=True)
        SupportTicketResponse.objects.create(ticket=ticket, author=self.tech, message="public", is_internal=False)

        self._login(self.patient1)
        url = reverse("support:ticket-response-list", kwargs={"ticket_id": ticket.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data["results"]["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["message"], "public")

    def test_tech_reply_moves_ticket_to_in_progress(self):
        ticket = SupportTicket.objects.create(created_by=self.patient1, category="technical", subject="S", description="x", priority="medium", status="open")

        self._login(self.tech)
        url = reverse("support:ticket-response-list", kwargs={"ticket_id": ticket.id})
        res = self.client.post(url, {"message": "We are working on it", "is_internal": False}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "in_progress")

    def test_only_tech_can_create_internal_note(self):
        ticket = SupportTicket.objects.create(created_by=self.patient1, category="technical", subject="S", description="x", priority="medium")

        self._login(self.patient1)
        url = reverse("support:ticket-response-list", kwargs={"ticket_id": ticket.id})
        res = self.client.post(url, {"message": "internal attempt", "is_internal": True}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
