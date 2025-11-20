from rest_framework import serializers
from .models import University, Course


class BaseSerializer(serializers.ModelSerializer):
    """Base serializer with common functionality."""
    
    def get_field_names(self, declared_fields, info):
        """Get field names for the serializer."""
        field_names = super().get_field_names(declared_fields, info)
        # Add created_at and updated_at if they exist in the model
        if hasattr(self.Meta.model, 'created_at'):
            field_names.append('created_at')
        if hasattr(self.Meta.model, 'updated_at'):
            field_names.append('updated_at')
        return field_names


class CourseListSerializer(BaseSerializer):
    """Serializer for course list data."""
    university_name = serializers.CharField(source='university.name', read_only=True)
    
    class Meta:
        model = Course
        fields = [
            'id', 'name', 'code', 'level', 'duration_years', 
            'is_active', 'university_name'
        ]


class CourseDetailSerializer(BaseSerializer):
    """Serializer for course detail data."""
    university_name = serializers.CharField(source='university.name', read_only=True)
    
    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CourseCreateSerializer(BaseSerializer):
    """Serializer for creating a course."""
    
    class Meta:
        model = Course
        fields = [
            'university', 'name', 'code', 'description', 
            'level', 'duration_years'
        ]
    
    def validate(self, attrs):
        """Validate that course code is unique for the university."""
        university = attrs.get('university')
        code = attrs.get('code')
        
        if university and code:
            if Course.objects.filter(university=university, code=code).exists():
                raise serializers.ValidationError(
                    {"code": "A course with this code already exists for this university."}
                )
        
        return attrs


class UniversityListSerializer(BaseSerializer):
    """Serializer for university list data."""
    
    class Meta:
        model = University
        fields = [
            'id', 'name', 'city', 'country', 'is_active',
            'email', 'phone', 'address'
        ]


class UniversityDetailSerializer(BaseSerializer):
    """Serializer for university detail data."""
    courses = CourseListSerializer(many=True, read_only=True)
    
    class Meta:
        model = University
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class UniversityCreateSerializer(BaseSerializer):
    """Serializer for creating a university."""
    
    class Meta:
        model = University
        fields = [
            'name', 'description', 'address', 'city', 'country',
            'website', 'email', 'phone', 'logo'
        ]


# For backward compatibility
UniversitySerializer = UniversityDetailSerializer