# apps/accounts/admin.py
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from medismile.admin_mixins import BaseOptimizedAdmin

from .models import (
    Role,
    User,
    PatientProfile,
    StudentProfile,
    SupervisorProfile,
    UniversityAdminProfile,
    TechSupportProfile,
)
from apps.universities.models import University


# ============================================================
# USER ADMIN FORMS (ADD + CHANGE)
# ============================================================
class _BaseUniversityScopedForm(forms.ModelForm):
    university = forms.ModelChoiceField(
        queryset=University.objects.all(),
        required=False,
        label=_("University"),
        help_text=_("Required for Student, Supervisor, and University Admin roles."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if getattr(self, "instance", None) and getattr(self.instance, "pk", None):
            role_name = getattr(getattr(self.instance, "role", None), "name", None)
            profile = self._get_profile_for_role(role_name)
            if profile and getattr(profile, "university_id", None):
                self.fields["university"].initial = profile.university_id

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        university = cleaned_data.get("university")
        role_name = getattr(role, "name", None)

        if role_name in {Role.STUDENT, Role.SUPERVISOR, Role.UNIVERSITY_ADMIN} and not university:
            raise forms.ValidationError(_("University is required for this role."))

        return cleaned_data

    def _get_profile_for_role(self, instance_role_name):
        profile_attr = {
            Role.STUDENT: "studentprofile_profile",
            Role.SUPERVISOR: "supervisorprofile_profile",
            Role.UNIVERSITY_ADMIN: "universityadminprofile_profile",
        }.get(instance_role_name)
        if not profile_attr:
            return None
        try:
            return getattr(self.instance, profile_attr)
        except Exception:
            return None


class UserAdminChangeForm(_BaseUniversityScopedForm, UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


class UserAdminCreationForm(_BaseUniversityScopedForm, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "role",
        )


# ============================================================
# ROLE ADMIN
# ============================================================
@admin.register(Role)
class RoleAdmin(BaseOptimizedAdmin):
    list_display = ("name", "description", "created_at")
    search_fields = ("name",)
    ordering = ("name",)
    readonly_fields = ("created_at",)


# ============================================================
# PROFILE INLINES
# ============================================================
class BaseProfileInline(admin.StackedInline):
    extra = 0
    can_delete = False
    verbose_name_plural = _("Profile")


class PatientProfileInline(BaseProfileInline):
    model = PatientProfile


class StudentProfileInline(BaseProfileInline):
    model = StudentProfile


class SupervisorProfileInline(BaseProfileInline):
    model = SupervisorProfile


class UniversityAdminProfileInline(BaseProfileInline):
    model = UniversityAdminProfile


class TechSupportProfileInline(BaseProfileInline):
    model = TechSupportProfile


# ============================================================
# USER ADMIN
# ============================================================
@admin.register(User)
class UserAdmin(BaseOptimizedAdmin, DjangoUserAdmin):
    """
    Central User admin.
    Roles and profiles are managed here in a controlled way.
    """

    form = UserAdminChangeForm
    add_form = UserAdminCreationForm

    list_display = (
        "email",
        "username",
        "role",
        "display_university",
        "is_active",
        "is_staff",
        "created_by",
        "date_joined",
    )
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("-date_joined",)
    list_select_related = ("role", "created_by")
    autocomplete_fields = ("created_by",)

    readonly_fields = (
        "last_login",
        "date_joined",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal Info"), {"fields": ("username", "first_name", "last_name")}),
        (
            _("Role & Ownership"),
            {
                "fields": (
                    "role",
                    "university",
                    "created_by",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
        (
            _("Important Dates"),
            {
                "fields": (
                    "last_login",
                    "date_joined",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "first_name",
                    "last_name",
                    "role",
                    "university",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    inlines = [
        PatientProfileInline,
        StudentProfileInline,
        SupervisorProfileInline,
        UniversityAdminProfileInline,
        TechSupportProfileInline,
    ]

    def save_model(self, request, obj, form, change):
        university = form.cleaned_data.get("university")
        role_name = getattr(obj.role, "name", None)

        if university and role_name in {
            Role.STUDENT,
            Role.SUPERVISOR,
            Role.UNIVERSITY_ADMIN,
        }:
            # pass context to signals during creation
            obj._desired_university_id = university.id

        if not obj.created_by_id and request.user.is_authenticated:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)

        # Ensure profile is synced with chosen university after save
        if university and role_name in {
            Role.STUDENT,
            Role.SUPERVISOR,
            Role.UNIVERSITY_ADMIN,
        }:
            profile = self._get_profile_instance(obj, role_name)
            if profile and getattr(profile, "university_id", None) != university.id:
                profile.university = university
                profile.full_clean()
                profile.save(update_fields=["university", "updated_at"])

    @staticmethod
    def _get_profile_instance(user, role_name):
        profile_attr = {
            Role.STUDENT: "studentprofile_profile",
            Role.SUPERVISOR: "supervisorprofile_profile",
            Role.UNIVERSITY_ADMIN: "universityadminprofile_profile",
        }.get(role_name)
        if not profile_attr:
            return None
        try:
            return getattr(user, profile_attr)
        except Exception:
            return None

    @admin.display(description=_("University"))
    def display_university(self, obj):
        profile = self._get_profile_instance(obj, getattr(obj.role, "name", None))
        return getattr(getattr(profile, "university", None), "name", None)
