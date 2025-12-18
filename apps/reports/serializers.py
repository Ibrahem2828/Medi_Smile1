from rest_framework import serializers
from .models import Report
from apps.accounts.serializers import UserSerializer
from apps.universities.serializers import UniversitySerializer


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for report data."""
    
    student = UserSerializer(read_only=True)
    university = UniversitySerializer(read_only=True)
    generated_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id', 'student', 'report_type', 'file_url', 'generated_at',
            'generated_by', 'university', 'title', 'description', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'generated_at', 'created_at', 'updated_at']


class ReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a report."""
    
    student_id = serializers.UUIDField(write_only=True)
    university_id = serializers.UUIDField(write_only=True)
    generated_by_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Report
        fields = [
            'student_id', 'university_id', 'report_type', 'file_url',
            'title', 'description', 'generated_by_id', 'is_active'
        ]
    
    def validate(self, data):
        """Validate report data."""
        from apps.accounts.models import User
        
        student_id = data.get('student_id')
        if student_id:
            try:
                student = User.objects.get(id=student_id, role='student')
            except User.DoesNotExist:
                raise serializers.ValidationError({'student_id': 'Student not found'})
        
        return data
    
    def create(self, validated_data):
        """Create a new report."""
        from apps.accounts.models import User
        from medismile.utils.auth import resolve_request_user
        
        student_id = validated_data.pop('student_id')
        university_id = validated_data.pop('university_id')
        generated_by_id = validated_data.pop('generated_by_id', None)
        
        # Get student
        student = User.objects.get(id=student_id, role='student')
        
        # Get university
        from apps.universities.models import University
        university = University.objects.get(id=university_id)
        
        # Get generated_by - try from request_user first, then from generated_by_id
        request = self.context.get('request')
        generated_by = None
        if request:
            request_user = resolve_request_user(request)
            if request_user:
                generated_by = request_user
            elif generated_by_id:
                generated_by = User.objects.get(id=generated_by_id)
        elif generated_by_id:
            generated_by = User.objects.get(id=generated_by_id)
        
        return Report.objects.create(
            student=student,
            university=university,
            generated_by=generated_by,
            **validated_data
        )


class ReportUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a report."""
    
    class Meta:
        model = Report
        fields = [
            'title', 'description', 'is_active', 'file_url'
        ]




















