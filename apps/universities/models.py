# apps/universities/models.py

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class University(models.Model):
    """
    Core University model.
    Acts as the top-level organizational scope for all academic entities.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("University Name"),
    )

    short_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Short Name"),
        help_text=_("Abbreviated name (e.g. HU, DENT-UNI)"),
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Description"),
    )

    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Address"),
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("City"),
    )

    country = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Country"),
    )

    website = models.URLField(
        blank=True,
        null=True,
        verbose_name=_("Website"),
    )

    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name=_("Official Email"),
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name=_("Phone"),
    )

    logo = models.ImageField(
        upload_to="universities/logos/",
        blank=True,
        null=True,
        verbose_name=_("Logo"),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
    )

    class Meta:
        db_table = "universities"
        verbose_name = _("University")
        verbose_name_plural = _("Universities")
        ordering = ["name"]

    def __str__(self):
        return self.name


# ============================================================
# Faculty / Department
# ============================================================

class Faculty(models.Model):
    """
    Faculty or College within a university
    (e.g. Faculty of Dentistry).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    university = models.ForeignKey(
        University,
        on_delete=models.CASCADE,
        related_name="faculties",
        verbose_name=_("University"),
    )

    name = models.CharField(
        max_length=200,
        verbose_name=_("Faculty Name"),
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Description"),
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "faculties"
        verbose_name = _("Faculty")
        verbose_name_plural = _("Faculties")
        unique_together = ("university", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.university.name}"


# ============================================================
# Academic Program (replaces generic Course)
# ============================================================

class AcademicProgram(models.Model):
    """
    Academic program (e.g. Bachelor of Dental Surgery).
    """

    LEVEL_CHOICES = (
        ("bachelor", _("Bachelor")),
        ("master", _("Master")),
        ("doctorate", _("Doctorate")),
        ("diploma", _("Diploma")),
        ("certificate", _("Certificate")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    university = models.ForeignKey(
        University,
        on_delete=models.CASCADE,
        related_name="programs",
        verbose_name=_("University"),
    )

    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programs",
        verbose_name=_("Faculty"),
    )

    name = models.CharField(
        max_length=255,
        verbose_name=_("Program Name"),
    )

    code = models.CharField(
        max_length=50,
        verbose_name=_("Program Code"),
    )

    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default="bachelor",
        verbose_name=_("Level"),
    )

    duration_years = models.PositiveIntegerField(
        default=4,
        verbose_name=_("Duration (Years)"),
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Description"),
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "academic_programs"
        verbose_name = _("Academic Program")
        verbose_name_plural = _("Academic Programs")
        unique_together = ("university", "code")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


# ============================================================
# Academic Year / Term
# ============================================================

class AcademicYear(models.Model):
    """
    Academic year scope (e.g. 2024 / 2025).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    university = models.ForeignKey(
        University,
        on_delete=models.CASCADE,
        related_name="academic_years",
        verbose_name=_("University"),
    )

    name = models.CharField(
        max_length=50,
        verbose_name=_("Academic Year"),
        help_text=_("Example: 2024/2025"),
    )

    start_date = models.DateField()
    end_date = models.DateField()

    is_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "academic_years"
        verbose_name = _("Academic Year")
        verbose_name_plural = _("Academic Years")
        unique_together = ("university", "name")
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.name} - {self.university.name}"
