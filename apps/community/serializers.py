from rest_framework import serializers
from .models import Content, ContentLike, ContentComment
from apps.accounts.serializers import UserSerializer
from apps.universities.serializers import UniversitySerializer
from medismile.utils.auth import resolve_request_user


class ContentCommentSerializer(serializers.ModelSerializer):
    """Serializer for content comment data."""
    
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ContentComment
        fields = [
            'id', 'user', 'text', 'is_approved', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ContentLikeSerializer(serializers.ModelSerializer):
    """Serializer for content like data."""
    
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ContentLike
        fields = [
            'id', 'user', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ContentSerializer(serializers.ModelSerializer):
    """Serializer for content data."""
    
    author = UserSerializer(read_only=True)
    university = UniversitySerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Content
        fields = [
            'id', 'title', 'description', 'content_type', 'category',
            'file', 'url', 'author', 'university', 'tags', 
            'is_public', 'is_featured', 'view_count', 'created_at', 
            'updated_at', 'likes_count', 'comments_count', 'is_liked'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'view_count']
    
    def get_likes_count(self, obj):
        """Get the count of likes for the content."""
        return obj.likes.count()
    
    def get_comments_count(self, obj):
        """Get the count of comments for the content."""
        return obj.comments.count()
    
    def get_is_liked(self, obj):
        """Check if the current user has liked the content."""
        request = self.context.get('request')
        user = resolve_request_user(request) if request else None
        if user:
            return obj.likes.filter(user=user).exists()
        return False


class ContentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating content."""
    
    class Meta:
        model = Content
        fields = [
            'title', 'description', 'content_type', 'category',
            'file', 'url', 'university', 'tags', 'is_public'
        ]
    
    def validate(self, data):
        """Validate content data."""
        # Check if either file or url is provided
        if not data.get('file') and not data.get('url'):
            raise serializers.ValidationError(("Either file or URL must be provided"))
        
        return data
    
    def create(self, validated_data):
        """Create a new content."""
        request = self.context.get('request')
        user = resolve_request_user(request) if request else None
        if not user:
            raise serializers.ValidationError({'user_id': 'User identification is required'})
        validated_data['author'] = user
        return super().create(validated_data)


class ContentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating content."""
    
    class Meta:
        model = Content
        fields = [
            'title', 'description', 'content_type', 'category',
            'file', 'url', 'university', 'tags', 'is_public', 'is_featured'
        ]
    
    def validate(self, data):
        """Validate content data."""
        # Check if either file or url is provided
        if not data.get('file') and not data.get('url'):
            raise serializers.ValidationError(("Either file or URL must be provided"))
        
        return data


class ContentCommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a content comment."""
    
    class Meta:
        model = ContentComment
        fields = [
            'content', 'text', 'parent'
        ]
    
    def create(self, validated_data):
        """Create a new content comment."""
        request = self.context.get('request')
        user = resolve_request_user(request) if request else None
        if not user:
            raise serializers.ValidationError({'user_id': 'User identification is required'})
        validated_data['user'] = user
        return super().create(validated_data)