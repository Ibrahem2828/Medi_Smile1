import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


# ============================================================
# University
# ============================================================
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

    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    website = models.URLField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)

    logo = models.ImageField(
        upload_to="universities/logos/",
        blank=True,
        null=True,
        verbose_name=_("Logo"),
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "universities"
        verbose_name = _("University")
        verbose_name_plural = _("Universities")
        ordering = ["name"]

    def clean(self):
        super().clean()

        if self.short_name and len(self.short_name) < 2:
            raise ValidationError(
                {"short_name": _("Short name must be at least 2 characters.")}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

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

    description = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "faculties"
        verbose_name = _("Faculty")
        verbose_name_plural = _("Faculties")
        unique_together = ("university", "name")
        ordering = ["name"]

    def clean(self):
        super().clean()

        if not self.university.is_active:
            raise ValidationError(
                _("Cannot add faculty to an inactive university.")
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.university.name}"


# ============================================================
# Academic Program
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

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)

    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default="bachelor",
    )

    duration_years = models.PositiveIntegerField(default=4)

    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "academic_programs"
        verbose_name = _("Academic Program")
        verbose_name_plural = _("Academic Programs")
        unique_together = ("university", "code")
        ordering = ["name"]

    def clean(self):
        super().clean()

        if self.faculty and self.faculty.university != self.university:
            raise ValidationError(
                _("Faculty must belong to the same university as the program.")
            )

        if self.duration_years <= 0:
            raise ValidationError(
                _("Program duration must be greater than zero.")
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"


# ============================================================
# Academic Year
# ============================================================
class AcademicYear(models.Model):
    """
    Academic year scope (e.g. 2024 / 2025).
    Only ONE active academic year per university.
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

    def clean(self):
        super().clean()

        if self.start_date >= self.end_date:
            raise ValidationError(
                _("Academic year start date must be before end date.")
            )

        if self.is_active:
            qs = AcademicYear.objects.filter(
                university=self.university,
                is_active=True,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError(
                    _("Only one active academic year is allowed per university.")
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.university.name}"
