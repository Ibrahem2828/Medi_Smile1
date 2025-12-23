# apps/universities/views.py

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from rest_framework import generics, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import University, Faculty, AcademicProgram, AcademicYear
from .serializers import (
    UniversityListSerializer,
    UniversityDetailSerializer,
    UniversityCreateSerializer,
    FacultySerializer,
    AcademicProgramSerializer,
    AcademicYearSerializer,
)

from apps.accounts.permissions import IsUniversityAdmin


# ============================================================
# Standard API Response
# ============================================================

class APIResponse:
    @staticmethod
    def success(message, data=None, status_code=status.HTTP_200_OK):
        return Response(
            {
                "status": "success",
                "message": message,
                "data": data,
            },
            status=status_code,
        )

    @staticmethod
    def error(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response(
            {
                "status": "error",
                "message": message,
                "errors": errors,
            },
            status=status_code,
        )


# ============================================================
# University Views
# ============================================================

class UniversityListView(generics.ListAPIView):
    queryset = University.objects.filter(is_active=True)
    serializer_class = UniversityListSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(self.get_queryset(), many=True)
            return APIResponse.success(_("Universities retrieved successfully."), serializer.data)
        except Exception as e:
            return APIResponse.error(_("Failed to retrieve universities."), str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class UniversityCreateView(generics.CreateAPIView):
    serializer_class = UniversityCreateSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            university = serializer.save()
            return APIResponse.success(
                _("University created successfully."),
                UniversityDetailSerializer(university).data,
                status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return APIResponse.error(_("Invalid university data."), e.detail)
        except Exception as e:
            return APIResponse.error(_("Failed to create university."), str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class UniversityDetailView(generics.RetrieveAPIView):
    queryset = University.objects.all()
    serializer_class = UniversityDetailSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        try:
            university = self.get_object()
            serializer = self.get_serializer(university)
            return APIResponse.success(_("University retrieved successfully."), serializer.data)
        except Exception as e:
            return APIResponse.error(_("University not found."), str(e), status.HTTP_404_NOT_FOUND)


class UniversityUpdateView(generics.UpdateAPIView):
    queryset = University.objects.all()
    serializer_class = UniversityDetailSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def update(self, request, *args, **kwargs):
        try:
            university = self.get_object()
            serializer = self.get_serializer(university, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return APIResponse.success(_("University updated successfully."), serializer.data)
        except ValidationError as e:
            return APIResponse.error(_("Invalid update data."), e.detail)
        except Exception as e:
            return APIResponse.error(_("Failed to update university."), str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class UniversityDeleteView(generics.DestroyAPIView):
    queryset = University.objects.all()
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def delete(self, request, *args, **kwargs):
        try:
            university = self.get_object()
            university.is_active = False
            university.save(update_fields=["is_active"])
            return APIResponse.success(_("University deactivated successfully."))
        except Exception as e:
            return APIResponse.error(_("Failed to deactivate university."), str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================
# Faculty Views
# ============================================================

class FacultyListCreateView(generics.ListCreateAPIView):
    serializer_class = FacultySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Faculty.objects.filter(university_id=self.kwargs["university_id"], is_active=True)

    def create(self, request, *args, **kwargs):
        if not IsUniversityAdmin().has_permission(request, self):
            return APIResponse.error(_("Not allowed."), status_code=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        data["university"] = self.kwargs["university_id"]

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return APIResponse.success(_("Faculty created successfully."), serializer.data, status.HTTP_201_CREATED)


# ============================================================
# Academic Program Views
# ============================================================

class AcademicProgramListCreateView(generics.ListCreateAPIView):
    serializer_class = AcademicProgramSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AcademicProgram.objects.filter(university_id=self.kwargs["university_id"], is_active=True)

    def create(self, request, *args, **kwargs):
        if not IsUniversityAdmin().has_permission(request, self):
            return APIResponse.error(_("Not allowed."), status_code=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        data["university"] = self.kwargs["university_id"]

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return APIResponse.success(_("Academic program created successfully."), serializer.data, status.HTTP_201_CREATED)


# ============================================================
# Academic Year Views
# ============================================================

class AcademicYearListCreateView(generics.ListCreateAPIView):
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AcademicYear.objects.filter(university_id=self.kwargs["university_id"])

    def create(self, request, *args, **kwargs):
        if not IsUniversityAdmin().has_permission(request, self):
            return APIResponse.error(_("Not allowed."), status_code=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        data["university"] = self.kwargs["university_id"]

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return APIResponse.success(_("Academic year created successfully."), serializer.data, status.HTTP_201_CREATED)
